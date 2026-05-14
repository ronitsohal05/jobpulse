from __future__ import annotations

import json
from urllib.parse import urlparse

from app.schemas.jobs import JobIn

from ..base import BaseJobAdapter
from ..http import PoliteHttpClient
from ..mapping import job_in_from_extracted
from ..types import JobSourceType


class SmartRecruitersAdapter(BaseJobAdapter):
    source: JobSourceType = "smartrecruiters"

    def __init__(self, http: PoliteHttpClient) -> None:
        self.http = http

    def can_handle(self, url: str) -> bool:
        try:
            h = urlparse(url).netloc.lower()
            return "smartrecruiters.com" in h
        except Exception:
            return False

    def _company_slug(self, url: str) -> str | None:
        p = urlparse(url)
        parts = [x for x in p.path.strip("/").split("/") if x]
        return parts[0] if parts else None

    def discover_job_urls(self, url: str) -> list[str]:
        slug = self._company_slug(url)
        if not slug:
            return [url]
        api = f"https://api.smartrecruiters.com/v1/companies/{slug}/postings"
        status, body, err = self.http.get(api)
        if err or not body or status != 200:
            return [url]
        try:
            data = json.loads(body)
        except json.JSONDecodeError:
            return [url]
        out: list[str] = []
        for item in data.get("content") or []:
            if not isinstance(item, dict):
                continue
            u = item.get("jobAdUrl") or item.get("referralUrl")
            if isinstance(u, str) and u.startswith("http"):
                out.append(u)
        return out or [url]

    def extract_job(self, url: str) -> JobIn:
        from app.services.crawler.extract import extract_job_fields

        sc, html, err = self.http.get(url)
        if err or not html:
            raise RuntimeError(err or "empty_response")
        ex, _ = extract_job_fields(html, page_url=url)
        if not ex:
            raise RuntimeError("extract_failed")
        return job_in_from_extracted(ex, url, "smartrecruiters")
