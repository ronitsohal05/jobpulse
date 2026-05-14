from __future__ import annotations

from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import func
from sqlalchemy.orm import Session

from app.db.models import CrawlLog, CrawlerSource
from app.db.session import get_db
from app.schemas.crawler import (
    CrawlLogOut,
    CrawlRunResponse,
    CrawlSeedResponse,
    CrawlStatsOut,
    CrawlerSourceIn,
    CrawlerSourceOut,
    CrawlerSourcePatch,
)
from app.services.crawler.pipeline import crawl_and_ingest_source
from app.services.crawler.seed import seed_sources_from_json
from app.workers.enqueue import try_enqueue_crawl


router = APIRouter(prefix="/api/crawl", tags=["crawler"])


def _to_source_out(s: CrawlerSource) -> CrawlerSourceOut:
    return CrawlerSourceOut(
        id=s.id,
        name=s.name,
        base_url=s.base_url,
        allowed_domain=s.allowed_domain,
        job_link_pattern=s.job_link_pattern,
        crawl_frequency=s.crawl_frequency,
        max_pages=s.max_pages,
        enabled=s.enabled,
        created_at=s.created_at,
        updated_at=s.updated_at,
    )


@router.get("/sources", response_model=list[CrawlerSourceOut])
def list_sources(db: Session = Depends(get_db)) -> list[CrawlerSourceOut]:
    rows = db.query(CrawlerSource).order_by(CrawlerSource.created_at.desc()).all()
    return [_to_source_out(r) for r in rows]


@router.post("/seed", response_model=CrawlSeedResponse)
def seed_crawler_sources(db: Session = Depends(get_db)) -> CrawlSeedResponse:
    """Load `infra/crawler_sources.json` (or bundled `/app/seed/crawler_sources.json`) into the DB."""
    result = seed_sources_from_json(db=db)
    if result.get("error"):
        return CrawlSeedResponse(
            created=0, updated=0, seed_file=None, error=str(result["error"])
        )
    return CrawlSeedResponse(
        created=int(result.get("created") or 0),
        updated=int(result.get("updated") or 0),
        seed_file=result.get("seed_file") if isinstance(result.get("seed_file"), str) else None,
    )


@router.patch("/source/{source_id}", response_model=CrawlerSourceOut)
def patch_source(
    source_id: UUID, payload: CrawlerSourcePatch, db: Session = Depends(get_db)
) -> CrawlerSourceOut:
    src = db.query(CrawlerSource).filter(CrawlerSource.id == source_id).one_or_none()
    if not src:
        raise HTTPException(status_code=404, detail="Source not found")
    was_enabled = src.enabled
    if payload.enabled is not None:
        src.enabled = payload.enabled
    db.commit()
    db.refresh(src)
    if payload.enabled is True and not was_enabled:
        try_enqueue_crawl(src.id)
    return _to_source_out(src)


@router.post("/source", response_model=CrawlerSourceOut)
def create_source(payload: CrawlerSourceIn, db: Session = Depends(get_db)) -> CrawlerSourceOut:
    existing = db.query(CrawlerSource).filter(CrawlerSource.name == payload.name).one_or_none()
    if existing:
        raise HTTPException(status_code=409, detail="Source name already exists")
    s = CrawlerSource(**payload.model_dump())
    db.add(s)
    db.commit()
    db.refresh(s)
    if s.enabled:
        try_enqueue_crawl(s.id)
    return _to_source_out(s)


@router.post("/run/{source_id}", response_model=CrawlRunResponse)
def run_source(source_id: UUID, db: Session = Depends(get_db)) -> CrawlRunResponse:
    src = db.query(CrawlerSource).filter(CrawlerSource.id == source_id).one_or_none()
    if not src:
        raise HTTPException(status_code=404, detail="Source not found")
    result = crawl_and_ingest_source(db=db, source_id=source_id)
    db.commit()
    return CrawlRunResponse(**result)


@router.get("/stats", response_model=CrawlStatsOut)
def crawl_stats(db: Session = Depends(get_db)) -> CrawlStatsOut:
    total = int(db.query(func.count(CrawlerSource.id)).scalar() or 0)
    active = int(
        db.query(func.count(CrawlerSource.id)).filter(CrawlerSource.enabled.is_(True)).scalar() or 0
    )
    return CrawlStatsOut(active_sources=active, total_sources=total)


@router.get("/logs", response_model=list[CrawlLogOut])
def list_logs(db: Session = Depends(get_db), limit: int = 50, offset: int = 0) -> list[CrawlLogOut]:
    rows = (
        db.query(CrawlLog)
        .order_by(CrawlLog.created_at.desc())
        .limit(min(limit, 200))
        .offset(max(offset, 0))
        .all()
    )
    return [
        CrawlLogOut(
            id=r.id,
            source_id=r.source_id,
            url=r.url,
            status=r.status.value,
            http_status=r.http_status,
            message=r.message,
            jobs_extracted=r.jobs_extracted,
            duplicates_skipped=r.duplicates_skipped,
            pages_fetched=r.pages_fetched,
            created_at=r.created_at,
        )
        for r in rows
    ]

