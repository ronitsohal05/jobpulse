from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timezone


@dataclass
class ScraperRequestLog:
    url: str
    method: str = "GET"
    status_code: int | None = None
    error: str | None = None
    duration_ms: float | None = None
    robots_allowed: bool | None = None
    timestamp: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
