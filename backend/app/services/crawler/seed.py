from __future__ import annotations

import json
import os
from pathlib import Path

from sqlalchemy.orm import Session

from app.db.models import CrawlerSource


def resolve_seed_file() -> Path | None:
    env = os.environ.get("CRAWLER_SOURCES_PATH", "").strip()
    candidates = []
    if env:
        candidates.append(Path(env))
    candidates.extend(
        [
            Path("/app/infra/crawler_sources.json"),
            Path("/app/seed/crawler_sources.json"),
        ]
    )
    for p in candidates:
        if p.is_file():
            return p
    return None


def seed_sources_from_json(db: Session, path: Path | None = None) -> dict[str, int | str]:
    p = path or resolve_seed_file()
    if not p or not p.is_file():
        return {
            "created": 0,
            "updated": 0,
            "error": "No seed file found. Set CRAWLER_SOURCES_PATH or mount infra/ at /app/infra.",
        }

    data = json.loads(p.read_text(encoding="utf-8"))
    sources = data.get("sources") or []
    created = 0
    updated = 0

    for raw in sources:
        name = raw.get("name")
        if not name:
            continue
        existing = db.query(CrawlerSource).filter(CrawlerSource.name == name).one_or_none()
        payload = {
            "base_url": raw["base_url"],
            "allowed_domain": raw["allowed_domain"],
            "job_link_pattern": raw.get("job_link_pattern"),
            "crawl_frequency": raw.get("crawl_frequency") or "daily",
            "max_pages": int(raw.get("max_pages") or 100),
            "enabled": bool(raw.get("enabled", True)),
        }
        if existing:
            for k, v in payload.items():
                setattr(existing, k, v)
            updated += 1
        else:
            db.add(CrawlerSource(name=name, **payload))
            created += 1

    db.commit()
    return {"created": created, "updated": updated, "seed_file": str(p)}
