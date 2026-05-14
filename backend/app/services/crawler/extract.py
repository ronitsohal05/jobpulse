from __future__ import annotations

import json
import re
from dataclasses import dataclass
from typing import Any
from urllib.parse import urlparse, urljoin

from bs4 import BeautifulSoup


@dataclass
class ExtractedJob:
    title: str
    company: str
    location: str | None
    description: str
    date_posted: str | None
    employment_type: str | None
    salary: str | None
    required_skills: list[str] | None
    preferred_skills: list[str] | None
    raw_html: str | None


def extract_links(html: str, base_url: str, pattern: str | None) -> list[str]:
    soup = BeautifulSoup(html, "lxml")
    urls: set[str] = set()
    for a in soup.find_all("a", href=True):
        href = a.get("href")
        if not href:
            continue
        u = urljoin(base_url, href)
        if pattern and pattern not in u:
            continue
        urls.add(u)
    return sorted(urls)


def _iter_jsonld_nodes(payload: Any) -> Any:
    if isinstance(payload, dict):
        if "@graph" in payload:
            for item in payload["@graph"]:
                yield from _iter_jsonld_nodes(item)
            return
        yield payload
    elif isinstance(payload, list):
        for item in payload:
            yield from _iter_jsonld_nodes(item)


def _is_job_posting(obj: dict[str, Any]) -> bool:
    t = obj.get("@type") or obj.get("type")
    if isinstance(t, list):
        return any("jobposting" in str(x).lower() for x in t)
    return "jobposting" in str(t or "").lower()


def _org_name(org: Any) -> str | None:
    if org is None:
        return None
    if isinstance(org, str):
        s = org.strip()
        if s.startswith("http"):
            return None
        return s or None
    if isinstance(org, dict):
        if "name" in org:
            n = org["name"]
            if isinstance(n, dict):
                return str(n.get("name") or n.get("@value") or "").strip() or None
            return str(n).strip() or None
    return None


def _jsonld_description_text(desc: Any) -> str:
    if desc is None:
        return ""
    if isinstance(desc, str):
        return desc
    if isinstance(desc, dict):
        return str(desc.get("value") or desc.get("text") or desc.get("@value") or desc.get("description") or "")
    return str(desc)


def _location_from_jobloc(job_loc: Any) -> str | None:
    if job_loc is None:
        return None
    if isinstance(job_loc, str):
        return job_loc.strip() or None
    if isinstance(job_loc, list):
        parts = [_location_from_jobloc(x) for x in job_loc]
        parts = [p for p in parts if p]
        return ", ".join(parts) if parts else None
    if not isinstance(job_loc, dict):
        return None
    if job_loc.get("name"):
        return str(job_loc["name"]).strip()
    addr = job_loc.get("address")
    if isinstance(addr, str):
        return addr.strip() or None
    if isinstance(addr, dict):
        bits = [
            addr.get("addressLocality"),
            addr.get("addressRegion"),
            addr.get("addressCountry"),
        ]
        bits = [str(b).strip() for b in bits if b]
        return ", ".join(bits) if bits else None
    return None


def _extract_jsonld_jobposting(html: str) -> dict[str, Any] | None:
    soup = BeautifulSoup(html, "lxml")
    for tag in soup.find_all("script", attrs={"type": "application/ld+json"}):
        raw = tag.get_text() or ""
        if not raw.strip():
            continue
        try:
            payload = json.loads(raw)
        except json.JSONDecodeError:
            continue
        for node in _iter_jsonld_nodes(payload):
            if isinstance(node, dict) and _is_job_posting(node):
                return node
    return None


def _strip_html_to_text(html: str) -> str:
    soup = BeautifulSoup(html, "lxml")
    for s in soup(["script", "style", "noscript"]):
        s.decompose()
    text = soup.get_text("\n")
    lines = [l.strip() for l in text.splitlines() if l.strip()]
    return "\n".join(lines)


def _meta_content(soup: BeautifulSoup, *, prop: str | None = None, name: str | None = None) -> str | None:
    if prop:
        tag = soup.find("meta", attrs={"property": prop})
        if tag and tag.get("content"):
            return str(tag["content"]).strip()
    if name:
        tag = soup.find("meta", attrs={"name": name})
        if tag and tag.get("content"):
            return str(tag["content"]).strip()
    return None


def _infer_company_from_url(url: str | None) -> str | None:
    if not url:
        return None
    try:
        host = urlparse(url).netloc.lower().split("@")[-1]
        host = host.split(":")[0]
    except Exception:
        return None

    # Known career domains → display name
    branding: list[tuple[str, str]] = [
        ("amazon.jobs", "Amazon"),
        ("jobs.apple.com", "Apple"),
        ("jobs.netflix.net", "Netflix"),
        ("explore.jobs.netflix.net", "Netflix"),
        ("netflix.com", "Netflix"),
        ("greenhouse.io", None),
        ("lever.co", None),
        ("myworkdayjobs.com", None),
        ("smartrecruiters.com", None),
        ("ashbyhq.com", None),
        ("linkedin.com", "LinkedIn"),
    ]
    for suffix, name in branding:
        if host == suffix or host.endswith("." + suffix):
            if name:
                return name
            break

    # boards.greenhouse.io/{company}/ → title-case slug
    parts = urlparse(url).path.strip("/").split("/")
    if "greenhouse.io" in host and len(parts) >= 1 and parts[0]:
        slug = parts[0].replace("-", " ").title()
        return slug if slug else None
    if "lever.co" in host and len(parts) >= 1 and parts[0] not in ("jobs", "u"):
        slug = parts[0].replace("-", " ").title()
        return slug if slug else None

    # amazon.jobs content often under /en/jobs/...
    if "amazon.jobs" in host:
        return "Amazon"
    if "apple.com" in host:
        return "Apple"

    return None


def _title_from_html_fallback(soup: BeautifulSoup, text: str, page_url: str | None) -> str:
    og_title = _meta_content(soup, prop="og:title") or _meta_content(soup, name="twitter:title")
    if og_title and len(og_title) > 2 and og_title.lower() not in ("job", "careers", "search"):
        return og_title.strip()[:400]

    h1 = soup.find("h1")
    if h1:
        t = h1.get_text().strip()
        if t and len(t) > 1:
            return t[:400]

    # First line: "Role | Company" or "Role - Careers"
    first_line = text.splitlines()[0].strip() if text else ""
    if first_line:
        m = re.match(r"^(.+?)\s*(?:[|\u2013\u2014\-])\s*(.+)$", first_line)
        if m:
            left, right = m.group(1).strip(), m.group(2).strip()
            if len(left) > 2 and right.lower() not in ("careers", "jobs", "home"):
                return left[:400]
        return first_line[:400]

    if page_url:
        inferred = _infer_company_from_url(page_url)
        if inferred:
            return f"Job posting ({inferred})"

    return "Untitled"


def _company_from_html_fallback(soup: BeautifulSoup, page_url: str | None) -> str:
    og_site = _meta_content(soup, prop="og:site_name")
    if og_site and og_site.lower() not in ("job", "careers"):
        return og_site.strip()[:400]

    app_name = _meta_content(soup, name="application-name")
    if app_name:
        return app_name.strip()[:400]

    from_url = _infer_company_from_url(page_url)
    if from_url:
        return from_url

    return "Unknown"


def _location_from_meta_and_text(soup: BeautifulSoup, text: str) -> str | None:
    loc = _meta_content(soup, name="jobLocation") or _meta_content(soup, prop="job:location")
    if loc:
        return loc[:400]
    # Common pattern: "Location\nCity, ST" in visible text — weak heuristic
    for line in text.splitlines()[:40]:
        if re.search(r"\b(remote|hybrid|onsite)\b", line, re.I):
            return line.strip()[:400]
        m = re.search(
            r"\b([A-Z][a-z]+(?:\s+[A-Z][a-z]+)?),\s*([A-Z]{2})\b",
            line,
        )
        if m and len(line) < 120:
            return line.strip()[:400]
    return None


def extract_job_fields(html: str, page_url: str | None = None) -> tuple[ExtractedJob | None, str | None]:
    soup = BeautifulSoup(html, "lxml")

    # Attempt 1: JSON-LD JobPosting
    jsonld = _extract_jsonld_jobposting(html)
    if jsonld:
        title = jsonld.get("title") or jsonld.get("name") or ""
        org = jsonld.get("hiringOrganization") or jsonld.get("organization")
        if isinstance(org, list) and org:
            org = org[0]
        company = _org_name(org)

        location = None
        jl = jsonld.get("jobLocation")
        location = _location_from_jobloc(jl)
        if not location and jsonld.get("applicantLocationRequirements"):
            location = str(jsonld.get("applicantLocationRequirements"))[:400]

        desc = _jsonld_description_text(jsonld.get("description"))
        date_posted = jsonld.get("datePosted")
        employment_type = jsonld.get("employmentType")
        salary = None
        base_salary = jsonld.get("baseSalary")
        if isinstance(base_salary, dict):
            value = base_salary.get("value")
            if isinstance(value, dict):
                salary = str(value.get("value") or value.get("minValue") or "")
            elif value is not None:
                salary = str(value)

        title_s = str(title).strip() or _title_from_html_fallback(soup, _strip_html_to_text(html), page_url)
        company_s = (company or "").strip() or _company_from_html_fallback(soup, page_url)
        desc_text = _strip_html_to_text(desc) if "<" in desc else desc
        if not desc_text.strip():
            desc_text = _strip_html_to_text(html)

        return (
            ExtractedJob(
                title=title_s[:400],
                company=company_s[:400],
                location=str(location).strip()[:400] if location else None,
                description=desc_text,
                date_posted=str(date_posted) if date_posted else None,
                employment_type=str(employment_type) if employment_type else None,
                salary=salary,
                required_skills=None,
                preferred_skills=None,
                raw_html=html,
            ),
            None,
        )

    # Attempt 2: meta + heuristics (+ URL inference)
    text = _strip_html_to_text(html)
    title = _title_from_html_fallback(soup, text, page_url)
    company = _company_from_html_fallback(soup, page_url)
    location = _location_from_meta_and_text(soup, text)

    return (
        ExtractedJob(
            title=title,
            company=company,
            location=location,
            description=text or title,
            date_posted=None,
            employment_type=None,
            salary=None,
            required_skills=None,
            preferred_skills=None,
            raw_html=html,
        ),
        "jsonld_not_found_used_html_fallback",
    )
