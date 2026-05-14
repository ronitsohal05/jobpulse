from __future__ import annotations

import re
from collections import deque
from urllib.parse import urljoin, urlparse

from bs4 import BeautifulSoup

from app.schemas.jobs import JobIn
from app.services.crawler.extract import extract_job_fields, extract_links
from app.services.crawler.fetch import allowed_by_any_domain
from app.settings import settings

from ..base import BaseJobAdapter
from ..http import PoliteHttpClient
from ..mapping import job_in_from_extracted
from ..normalizer import (
    normalize_employment_type,
    normalize_experience_level,
    normalize_salary,
    normalize_source_url,
)
from ..types import JobSourceType


def _visible_text(html: str) -> str:
    soup = BeautifulSoup(html, "lxml")
    for s in soup(["script", "style", "noscript"]):
        s.decompose()
    text = soup.get_text("\n")
    lines = [l.strip() for l in text.splitlines() if l.strip()]
    return "\n".join(lines)


def _first_text(soup: BeautifulSoup, selector: str) -> str | None:
    el = soup.select_one(selector)
    if not el:
        return None
    t = el.get_text(" ", strip=True)
    return t[:2000] if t else None


def _guess_salary(text: str) -> str | None:
    for line in text.splitlines():
        low = line.lower()
        if "$" in line and any(k in low for k in ("salary", "compensation", "pay", "range")):
            return line.strip()[:200]
    if m := re.search(r"\$\s?\d[\d,]*(?:\s?-\s?\$?\s?\d[\d,]*)?(?:\s?/yr)?", text):
        return m.group(0).strip()[:200]
    return None


def _guess_employment(text: str) -> str | None:
    low = text.lower()
    for token, label in (
        ("full-time", "full-time"),
        ("full time", "full-time"),
        ("part-time", "part-time"),
        ("part time", "part-time"),
        ("contract", "contract"),
        ("temporary", "temporary"),
        ("internship", "internship"),
        ("intern ", "internship"),
    ):
        if token in low:
            return label
    return None


def _guess_experience(text: str) -> str | None:
    low = text.lower()
    for token in (
        "principal",
        "staff",
        "senior",
        "junior",
        "entry level",
        "new grad",
        "intern",
    ):
        if token in low:
            return normalize_experience_level(token)
    return None


def _enrich_from_selectors(job: JobIn, html: str) -> JobIn:
    text = _visible_text(html)
    soup = BeautifulSoup(html, "lxml")

    title_guess = (
        _first_text(soup, "h1")
        or _first_text(soup, "h2")
        or _first_text(soup, "[class*='title' i]")
        or _first_text(soup, "[class*='job-title' i]")
        or _first_text(soup, "[data-testid*='title' i]")
    )
    if title_guess and (len(job.title) < 3 or job.title.lower() == "untitled"):
        job = job.model_copy(update={"title": title_guess[:400]})

    loc_guess = _first_text(soup, "[class*='location' i]") or _first_text(
        soup, "[data-testid*='location' i]"
    )
    if loc_guess and not job.location:
        job = job.model_copy(update={"location": loc_guess[:400]})

    desc_guess = (
        _first_text(soup, "[class*='description' i]")
        or _first_text(soup, "[class*='content' i]")
        or _first_text(soup, "main")
        or _first_text(soup, "article")
    )
    if desc_guess and len(job.description) < 120:
        job = job.model_copy(update={"description": desc_guess})

    salary = job.salary or _guess_salary(text)
    et = job.employment_type or _guess_employment(text)
    el = job.experience_level or _guess_experience(text + "\n" + (job.title or ""))

    return job.model_copy(
        update={
            "salary": normalize_salary(salary),
            "employment_type": normalize_employment_type(et),
            "experience_level": el,
        }
    )


def extract_generic_job(http: PoliteHttpClient, url: str, *, source_label: str = "generic") -> JobIn:
    sc, html, err = http.get(url)
    if err or not html:
        raise RuntimeError(err or "empty_response")

    ex, _note = extract_job_fields(html, page_url=url)
    if not ex:
        raise RuntimeError("extract_failed")

    job = job_in_from_extracted(ex, url, source_label)
    job = _enrich_from_selectors(job, html)

    weak = len(job.description) < 200 or job.title.lower() in ("untitled", "job posting")
    if weak and getattr(settings, "scraper_llm_enabled", False):
        from ..llm_extract import extract_job_with_llm_optional

        llm_job = extract_job_with_llm_optional(_visible_text(html)[:12000], url)
        if llm_job:
            job = llm_job

    return job


def _listing_host(page_url: str) -> str:
    try:
        return urlparse(page_url).netloc.lower().split("@")[-1]
    except Exception:
        return ""


def extract_pagination_hrefs(
    soup: BeautifulSoup,
    listing_url: str,
    *,
    seed_host: str,
    job_link_pattern: str | None,
) -> list[str]:
    """Likely follow-on search / listing pages (same host, not job-detail URLs)."""
    seen: set[str] = set()
    out: list[str] = []

    def maybe_add(href: str | None) -> None:
        if not href or href.startswith("#") or href.startswith("javascript:"):
            return
        u = urljoin(listing_url, href.strip())
        if _listing_host(u) != seed_host:
            return
        if job_link_pattern and job_link_pattern in u:
            return
        key = normalize_source_url(u)
        if key == normalize_source_url(listing_url):
            return
        if key in seen:
            return
        seen.add(key)
        out.append(u)

    for tag in soup.select('link[rel="next"]'):
        maybe_add(tag.get("href"))
    for tag in soup.select('a[rel="next"]'):
        maybe_add(tag.get("href"))

    for a in soup.find_all("a", href=True):
        href = a.get("href")
        if not href:
            continue
        rel = a.get("rel")
        if isinstance(rel, (list, tuple)) and any(str(x).lower() == "next" for x in rel):
            maybe_add(href)
            continue
        if isinstance(rel, str) and "next" in rel.lower():
            maybe_add(href)
            continue
        aria = (a.get("aria-label") or "").lower()
        title = (a.get("title") or "").lower()
        if any(
            p in aria or p in title
            for p in ("next page", "next jobs", "goto next", "load more results", "show next")
        ):
            maybe_add(href)
            continue
        raw_txt = (a.get_text() or "").strip().lower()
        txt = " ".join(raw_txt.split())
        if txt in ("next", "»", "›", "siguiente", "weiter", "suivant", "volgende"):
            maybe_add(href)

    return out[:24]


class GenericJobPageAdapter(BaseJobAdapter):
    source: JobSourceType = "generic"

    def __init__(
        self,
        http: PoliteHttpClient,
        *,
        job_link_pattern: str | None = None,
        allowed_domains_csv: str | None = None,
        max_discovered_links: int = 500,
        max_listing_pages: int = 25,
    ) -> None:
        self.http = http
        self.job_link_pattern = job_link_pattern
        self.allowed_domains_csv = allowed_domains_csv
        self.max_discovered_links = max_discovered_links
        self.max_listing_pages = max_listing_pages

    def can_handle(self, url: str) -> bool:
        return True

    def discover_job_urls(self, url: str) -> list[str]:
        """
        Walk the seed search URL plus linked listing pages (e.g. rel=next) and collect job URLs.
        """
        seed_host = _listing_host(url)
        if not seed_host:
            return []
        max_lp = max(1, min(40, self.max_listing_pages))

        queue: deque[str] = deque([url])
        queued_norm: set[str] = {normalize_source_url(url)}
        visited_norm: set[str] = set()
        job_out: list[str] = []
        job_norm: set[str] = set()

        while queue and len(visited_norm) < max_lp:
            page_url = queue.popleft()
            pn = normalize_source_url(page_url)
            if pn in visited_norm:
                continue
            visited_norm.add(pn)

            sc, html, err = self.http.get(page_url)
            if err or not html:
                continue
            soup = BeautifulSoup(html, "lxml")

            for ju in extract_links(html, base_url=page_url, pattern=self.job_link_pattern):
                if self.allowed_domains_csv and not allowed_by_any_domain(ju, self.allowed_domains_csv):
                    continue
                jk = normalize_source_url(ju)
                if jk in job_norm:
                    continue
                job_norm.add(jk)
                job_out.append(ju)
                if len(job_out) >= self.max_discovered_links:
                    return job_out

            for next_u in extract_pagination_hrefs(
                soup, page_url, seed_host=seed_host, job_link_pattern=self.job_link_pattern
            ):
                nn = normalize_source_url(next_u)
                if nn in visited_norm or nn in queued_norm:
                    continue
                queued_norm.add(nn)
                queue.append(next_u)

        return job_out

    def extract_job(self, url: str) -> JobIn:
        return extract_generic_job(self.http, url, source_label="generic")


class IcimsAdapter(GenericJobPageAdapter):
    source: JobSourceType = "icims"

    def can_handle(self, url: str) -> bool:
        try:
            return "icims.com" in urlparse(url).netloc.lower()
        except Exception:
            return False

    def extract_job(self, url: str) -> JobIn:
        return extract_generic_job(self.http, url, source_label="icims")


class BambooHrAdapter(GenericJobPageAdapter):
    source: JobSourceType = "bamboohr"

    def can_handle(self, url: str) -> bool:
        try:
            return "bamboohr.com" in urlparse(url).netloc.lower()
        except Exception:
            return False

    def extract_job(self, url: str) -> JobIn:
        return extract_generic_job(self.http, url, source_label="bamboohr")
