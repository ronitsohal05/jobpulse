from __future__ import annotations

import re
from urllib.parse import urljoin, urlparse

from app.schemas.jobs import JobIn

from ..base import BaseJobAdapter
from ..http import PoliteHttpClient
from ..mapping import job_in_from_extracted
from ..types import JobSourceType


class WorkdayAdapter(BaseJobAdapter):
    source: JobSourceType = "workday"

    def __init__(self, http: PoliteHttpClient) -> None:
        self.http = http

    def can_handle(self, url: str) -> bool:
        try:
            h = urlparse(url).netloc.lower()
            return "myworkdayjobs.com" in h or "workday.com" in h
        except Exception:
            return False

    def discover_job_urls(self, url: str) -> list[str]:
        status, html, err = self.http.get(url)
        if err or not html:
            return [url]
        found: set[str] = set()
        for m in re.finditer(r'href=["\']([^"\']+)["\']', html, re.I):
            href = m.group(1)
            if "/job/" not in href.lower():
                continue
            absu = urljoin(url, href)
            if urlparse(absu).netloc == urlparse(url).netloc:
                found.add(absu.split("#")[0])
        return sorted(found) or [url]

    def extract_job(self, url: str) -> JobIn:
        from app.services.crawler.extract import extract_job_fields

        sc, html, err = self.http.get(url)
        if err or not html:
            raise RuntimeError(err or "empty_response")
        ex, _ = extract_job_fields(html, page_url=url)
        if not ex:
            raise RuntimeError("extract_failed")
        return job_in_from_extracted(ex, url, "workday")
