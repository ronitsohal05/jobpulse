from __future__ import annotations

import logging
from uuid import UUID

logger = logging.getLogger(__name__)


def try_enqueue_crawl(source_id: UUID) -> bool:
    """Queue a background crawl. Returns False if Redis/RQ is unavailable (API still succeeds)."""
    try:
        from app.workers.queue import get_queue

        q = get_queue()
        q.enqueue(
            "app.workers.tasks.crawl_source",
            str(source_id),
            job_timeout=1800,
            result_ttl=3600,
        )
        return True
    except Exception as exc:  # noqa: BLE001 — enqueue must never break callers
        logger.warning("Could not enqueue crawl for source %s: %s", source_id, exc)
        return False
