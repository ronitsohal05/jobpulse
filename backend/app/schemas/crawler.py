from __future__ import annotations

from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, Field


class CrawlerSourceIn(BaseModel):
    name: str
    base_url: str
    allowed_domain: str = Field(
        ...,
        description="Single hostname (e.g. amazon.jobs) or comma-separated allowlist (e.g. github.com,boards.greenhouse.io).",
    )
    job_link_pattern: str | None = None
    crawl_frequency: str = "daily"
    max_pages: int = Field(default=100, ge=1, le=1000)
    enabled: bool = True


class CrawlerSourcePatch(BaseModel):
    enabled: bool | None = None


class CrawlerSourceOut(CrawlerSourceIn):
    id: UUID
    created_at: datetime
    updated_at: datetime


class CrawlRunResponse(BaseModel):
    source_id: UUID
    pages_fetched: int
    jobs_extracted: int
    duplicates_skipped: int
    status: str


class CrawlSeedResponse(BaseModel):
    created: int = 0
    updated: int = 0
    seed_file: str | None = None
    error: str | None = None


class CrawlLogOut(BaseModel):
    id: UUID
    source_id: UUID | None
    url: str
    status: str
    http_status: int | None
    message: str | None
    jobs_extracted: int
    duplicates_skipped: int
    pages_fetched: int
    created_at: datetime


class CrawlStatsOut(BaseModel):
    """Aggregate crawler state for admin dashboards."""

    active_sources: int = Field(..., description="Sources with enabled=true")
    total_sources: int = Field(..., description="All crawler_sources rows")

