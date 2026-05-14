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


class GreenhouseAdapter(BaseJobAdapter):
    source: JobSourceType = "greenhouse"

    def __init__(self, http: PoliteHttpClient) -> None:
        self.http = http

    def can_handle(self, url: str) -> bool:
        try:
            return "greenhouse.io" in urlparse(url).netloc.lower()
        except Exception:
            return False

    def _board_and_job(self, url: str) -> tuple[str | None, str | None]:
        p = urlparse(url)
        parts = [x for x in p.path.strip("/").split("/") if x]
        if not parts:
            return None, None
        if "jobs" in parts:
            i = parts.index("jobs")
            board = parts[i - 1] if i > 0 else None
            jid = parts[i + 1] if len(parts) > i + 1 else None
            return board, jid
        return parts[0], None

    def discover_job_urls(self, url: str) -> list[str]:
        board, job_id = self._board_and_job(url)
        if not board:
            return []
        if job_id:
            return [url]
        api = f"https://boards-api.greenhouse.io/v1/boards/{board}/jobs"
        status, body, err = self.http.get(api)
        if err or not body or status != 200:
            return []
        try:
            data = json.loads(body)
        except json.JSONDecodeError:
            return []
        out: list[str] = []
        for j in data.get("jobs") or []:
            au = j.get("absolute_url")
            if isinstance(au, str) and au.startswith("http"):
                out.append(au)
        return out

    def _job_json_to_job_in(self, job: dict, source_url: str, board: str | None) -> JobIn:
        title = str(job.get("title") or "").strip()
        loc = job.get("location") or {}
        location = loc.get("name") if isinstance(loc, dict) else str(loc) if loc else None
        desc = str(job.get("content") or job.get("internal_content") or "")
        desc_text = re.sub(r"<[^>]+>", " ", desc)
        desc_text = " ".join(desc_text.split()).strip() or title
        company = None
        md = job.get("metadata")
        if isinstance(md, list):
            for item in md:
                if isinstance(item, dict) and str(item.get("name", "")).lower() in (
                    "company",
                    "company name",
                ):
                    company = str(item.get("value") or "").strip() or None
        if not company and isinstance(job.get("metadata"), dict):
            company = str(job.get("metadata", {}).get("company_name") or "").strip() or None
        if not company and board:
            company = board.replace("-", " ").title()
        posted_raw = job.get("first_published") or job.get("updated_at")
        return JobIn(
            title=title or "Untitled",
            company=company or "Unknown",
            location=location,
            description=desc_text,
            source_url=source_url,
            source="greenhouse",
            date_posted=normalize_date_posted(str(posted_raw)) if posted_raw else None,
            required_skills=None,
            preferred_skills=None,
            employment_type=None,
            experience_level=None,
            salary=None,
        )

    def extract_job(self, url: str) -> JobIn:
        board, job_id = self._board_and_job(url)
        if board and job_id:
            detail = f"https://boards-api.greenhouse.io/v1/boards/{board}/jobs/{job_id}"
            status, body, err = self.http.get(detail)
            if not err and body and status == 200:
                try:
                    job = json.loads(body)
                    return self._job_json_to_job_in(job, url, board)
                except json.JSONDecodeError:
                    pass

        sc, html, err = self.http.get(url)
        if err or not html:
            raise RuntimeError(err or "empty_response")
        ex, _note = extract_job_fields(html, page_url=url)
        if not ex:
            raise RuntimeError("extract_failed")
        return job_in_from_extracted(ex, url, "greenhouse")
