"""
Periodic crawl scheduler: enqueues RQ jobs for every enabled crawler source.

Run as a dedicated process (see docker-compose `crawl-scheduler` service).
"""
from __future__ import annotations

import logging
import os
import time

from app.db.models import CrawlerSource
from app.db.session import SessionLocal
from app.settings import settings
from app.workers.queue import get_queue

logger = logging.getLogger(__name__)


def _interval_s() -> int:
    raw = os.environ.get("CRAWL_SCHEDULE_INTERVAL_S")
    if raw and raw.isdigit():
        return max(60, int(raw))
    return max(60, int(settings.crawl_schedule_interval_s))


def enqueue_all_enabled_sources() -> int:
    """Enqueue one crawl job per enabled source. Returns number of jobs enqueued."""
    db = SessionLocal()
    try:
        rows = db.query(CrawlerSource).filter(CrawlerSource.enabled.is_(True)).all()
        ids = [r.id for r in rows]
    finally:
        db.close()
    if not ids:
        logger.info("No enabled crawler sources; nothing enqueued.")
        return 0
    q = get_queue()
    for sid in ids:
        q.enqueue(
            "app.workers.tasks.crawl_source",
            str(sid),
            job_timeout=1800,
            result_ttl=3600,
        )
    logger.info("Enqueued %d crawl job(s) for enabled sources (redis=%s)", len(ids), settings.redis_url)
    return len(ids)


def main() -> None:
    logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(name)s: %(message)s")
    interval = _interval_s()
    logger.info("Crawl scheduler started: interval=%ss (%0.2fh)", interval, interval / 3600.0)
    while True:
        try:
            n = enqueue_all_enabled_sources()
            logger.info("Scheduled crawl cycle complete: %d job(s) enqueued", n)
        except Exception:
            logger.exception("Scheduled crawl enqueue failed")
        time.sleep(interval)


if __name__ == "__main__":
    main()
