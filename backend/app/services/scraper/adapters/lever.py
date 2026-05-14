from __future__ import annotations

import json
import re
from urllib.parse import urlparse

from app.schemas.jobs import JobIn
from app.services.crawler.extract import extract_job_fields

from ..base import BaseJobAdapter
from ..http import PoliteHttpClient
from ..mapping import job_in_from_extracted
from ..normalizer import normalize_date_posted
from ..types import JobSourceType


class LeverAdapter(BaseJobAdapter):
    source: JobSourceType = "lever"

    def __init__(self, http: PoliteHttpClient) -> None:
        self.http = http

    def can_handle(self, url: str) -> bool:
        try:
            h = urlparse(url).netloc.lower()
            return "lever.co" in h
        except Exception:
            return False

    def _site_and_posting(self, url: str) -> tuple[str | None, str | None]:
        p = urlparse(url)
        parts = [x for x in p.path.strip("/").split("/") if x]
        if not parts:
            return None, None
        if len(parts) == 1:
            return parts[0], None
        return parts[0], parts[1]

    def discover_job_urls(self, url: str) -> list[str]:
        site, pid = self._site_and_posting(url)
        if not site:
            return []
        if pid:
            return [url]
        api = f"https://api.lever.co/v0/postings/{site}?mode=json"
        status, body, err = self.http.get(api)
        if err or not body or status != 200:
            return []
        try:
            data = json.loads(body)
        except json.JSONDecodeError:
            return []
        if not isinstance(data, list):
            return []
        out: list[str] = []
        for item in data:
            if not isinstance(item, dict):
                continue
            u = item.get("hostedUrl") or item.get("applyUrl")
            if isinstance(u, str) and u.startswith("http"):
                out.append(u)
        return out

    def _posting_json_to_job_in(self, item: dict, source_url: str) -> JobIn:
        title = str(item.get("text") or item.get("title") or "").strip()
        loc = ""
        if isinstance(item.get("categories"), dict):
            loc = str(item["categories"].get("location") or "").strip()
        desc = item.get("description") or ""
        desc_text = re.sub(r"<[^>]+>", " ", str(desc))
        desc_text = " ".join(desc_text.split()).strip() or title
        company = str(item.get("hiringOrganization") or item.get("company") or "").strip()
        if not company:
            site, _ = self._site_and_posting(source_url)
            if site:
                company = site.replace("-", " ").title()
        created = item.get("createdAt") or item.get("updatedAt")
        wt = item.get("workplaceType")
        if isinstance(wt, dict):
            et_raw = str(wt.get("label") or "")
        else:
            et_raw = str(wt or "")
        et = (et_raw[:200] or None) if et_raw.strip() else None
        return JobIn(
            title=title or "Untitled",
            company=company or "Unknown",
            location=loc or None,
            description=desc_text,
            source_url=source_url,
            source="lever",
            date_posted=normalize_date_posted(str(created)) if created else None,
            required_skills=None,
            preferred_skills=None,
            employment_type=et,
            experience_level=None,
            salary=None,
        )

    def extract_job(self, url: str) -> JobIn:
        site, pid = self._site_and_posting(url)
        if site and pid:
            api = f"https://api.lever.co/v0/postings/{pid}"
            status, body, err = self.http.get(api)
            if not err and body and status == 200:
                try:
                    item = json.loads(body)
                    if isinstance(item, dict):
                        return self._posting_json_to_job_in(item, url)
                except json.JSONDecodeError:
                    pass

        sc, html, err = self.http.get(url)
        if err or not html:
            raise RuntimeError(err or "empty_response")
        ex, _ = extract_job_fields(html, page_url=url)
        if not ex:
            raise RuntimeError("extract_failed")
        return job_in_from_extracted(ex, url, "lever")
