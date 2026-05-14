from __future__ import annotations

import re
from urllib.parse import urlparse
from uuid import UUID

from sqlalchemy.orm import Session

from app.db.models import CrawlLog, CrawlStatus, CrawlerSource
from app.services.crawler.fetch import Fetcher
from app.services.importers.summer2027 import RAW_README_URL, import_summer2027_internships
from app.services.scraper.http import client_from_settings
from app.services.scraper.repository import JobRepository
from app.services.scraper.service import JobScraperService


def _github_blob_to_raw(url: str) -> str:
    """
    Convert GitHub blob URLs like:
      https://github.com/{owner}/{repo}/blob/{branch}/README.md
    to raw:
      https://raw.githubusercontent.com/{owner}/{repo}/{branch}/README.md
    If it's already raw, return as-is.
    """
    if "raw.githubusercontent.com" in url:
        return url
    m = re.match(r"^https?://github\\.com/([^/]+)/([^/]+)/blob/([^/]+)/(.+)$", url)
    if not m:
        return url
    owner, repo, branch, path = m.group(1), m.group(2), m.group(3), m.group(4)
    return f"https://raw.githubusercontent.com/{owner}/{repo}/{branch}/{path}"


def _is_github_readme_source(source: CrawlerSource) -> bool:
    """
    README-table import mode should ONLY be used for GitHub repos (or raw GitHub content).
    """
    u = (source.base_url or "").strip()
    if not u:
        return False
    try:
        host = urlparse(u).netloc.lower()
        path = urlparse(u).path.lower()
    except Exception:
        return False

    is_github_host = host in {"github.com", "raw.githubusercontent.com"} or host.endswith(
        ".github.com"
    )
    looks_like_readme = "readme" in path and (path.endswith(".md") or "/readme" in path)
    return bool(is_github_host and looks_like_readme)


def _is_summer2027_repo(source: CrawlerSource) -> bool:
    u = (source.base_url or "").lower()
    n = (source.name or "").lower()
    return ("vanshb03/summer2027-internships" in u) or ("summer2027-internships" in u) or (
        "summer2027-internships" in n
    )


def crawl_and_ingest_source(db: Session, source_id: UUID) -> dict:
    source = db.query(CrawlerSource).filter(CrawlerSource.id == source_id).one()
    if not source.enabled:
        db.add(
            CrawlLog(
                source_id=source.id,
                url=source.base_url,
                status=CrawlStatus.skipped,
                http_status=None,
                message="Source is disabled — enable it in Crawler sources, then run again.",
                pages_fetched=0,
                jobs_extracted=0,
                duplicates_skipped=0,
            )
        )
        return {"source_id": str(source_id), "pages_fetched": 0, "jobs_extracted": 0, "duplicates_skipped": 0, "status": "disabled"}

    fetcher = Fetcher(crawl_delay_s=1.0)
    pages_fetched = 0
    jobs_extracted = 0
    duplicates = 0

    # Special-case: GitHub README table importer (ONLY for GitHub sources)
    if _is_github_readme_source(source):
        # Currently we only support the Summer2027-Internships table format.
        # If you add more GitHub README sources later, we'll add additional parsers.
        if not _is_summer2027_repo(source):
            db.add(
                CrawlLog(
                    source_id=source.id,
                    url=source.base_url,
                    status=CrawlStatus.error,
                    http_status=None,
                    message="GitHub README import is only implemented for Summer2027-Internships right now.",
                    pages_fetched=0,
                    jobs_extracted=0,
                    duplicates_skipped=0,
                )
            )
            return {
                "source_id": str(source_id),
                "pages_fetched": 0,
                "jobs_extracted": 0,
                "duplicates_skipped": 0,
                "status": "error",
            }

        raw_url = _github_blob_to_raw(source.base_url) if source.base_url else RAW_README_URL
        status_code, md, err = fetcher.get(raw_url)
        pages_fetched += 1
        if err or not md:
            db.add(
                CrawlLog(
                    source_id=source.id,
                    url=raw_url,
                    status=CrawlStatus.error,
                    http_status=status_code,
                    message=err or "empty_response",
                    pages_fetched=pages_fetched,
                    jobs_extracted=0,
                    duplicates_skipped=0,
                )
            )
            return {
                "source_id": str(source_id),
                "pages_fetched": pages_fetched,
                "jobs_extracted": 0,
                "duplicates_skipped": 0,
                "status": "error",
            }

        # Importer does its own fetch; we already fetched MD above for crawl logging.
        # To avoid double-fetch, we pass through the raw_url and let it refetch (kept simple).
        result = import_summer2027_internships(
            db=db,
            raw_url=raw_url,
            embed=True,
            source_name=source.name,
        )
        jobs_extracted = int(result.get("created") or 0)
        duplicates = int(result.get("duplicates_skipped") or 0)

        db.add(
            CrawlLog(
                source_id=source.id,
                url=raw_url,
                status=CrawlStatus.success,
                http_status=status_code,
                message=f"imported {result.get('rows_parsed')} rows from README table",
                pages_fetched=pages_fetched,
                jobs_extracted=jobs_extracted,
                duplicates_skipped=duplicates,
            )
        )
        return {
            "source_id": str(source_id),
            "pages_fetched": pages_fetched,
            "jobs_extracted": jobs_extracted,
            "duplicates_skipped": duplicates,
            "status": "success",
        }

    http = client_from_settings()
    http.min_interval_per_host_s = fetcher.crawl_delay_s
    status_code, html, err = http.get(source.base_url)
    if err or not html:
        db.add(
            CrawlLog(
                source_id=source.id,
                url=source.base_url,
                status=CrawlStatus.error,
                http_status=status_code,
                message=err or "empty_response",
                pages_fetched=len(http.request_logs),
                jobs_extracted=0,
                duplicates_skipped=0,
            )
        )
        return {"source_id": str(source_id), "pages_fetched": len(http.request_logs), "jobs_extracted": 0, "duplicates_skipped": 0, "status": "error"}

    scraper = JobScraperService(http=http)
    jobs = scraper.scrape_seed_urls(
        [source.base_url],
        job_link_pattern=source.job_link_pattern,
        allowed_domains_csv=source.allowed_domain,
        max_pages=source.max_pages,
        max_listing_pages=max(3, min(40, source.max_pages)),
    )
    pages_fetched = len(http.request_logs)

    repo = JobRepository(db)
    jobs_extracted = 0
    duplicates = 0
    for job in jobs:
        _, created = repo.upsert_job(job.model_copy(update={"source": source.name}), embed=True)
        if created:
            jobs_extracted += 1
        else:
            duplicates += 1

    db.add(
        CrawlLog(
            source_id=source.id,
            url=source.base_url,
            status=CrawlStatus.success,
            http_status=status_code,
            message=f"scraper extracted {len(jobs)} unique postings ({jobs_extracted} new)",
            pages_fetched=pages_fetched,
            jobs_extracted=jobs_extracted,
            duplicates_skipped=duplicates,
        )
    )

    return {
        "source_id": str(source_id),
        "pages_fetched": pages_fetched,
        "jobs_extracted": jobs_extracted,
        "duplicates_skipped": duplicates,
        "status": "success",
    }

