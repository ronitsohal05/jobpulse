from __future__ import annotations

from datetime import datetime
from uuid import UUID

from pydantic import BaseModel


class EventOut(BaseModel):
    id: UUID
    entity_type: str
    entity_value: str
    bucket: str
    bucket_start: datetime
    current_value: int
    mean: float
    std: float
    z_score: float
    detected_at: datetime
    message: str

