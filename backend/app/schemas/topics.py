from __future__ import annotations

from datetime import datetime
from uuid import UUID

from pydantic import BaseModel


class TopicOut(BaseModel):
    id: UUID
    name: str
    keywords: list[str]
    method: str


class TopicTrendPoint(BaseModel):
    bucket_start: datetime
    count: int


class TopicWithTrend(BaseModel):
    topic: TopicOut
    trend: list[TopicTrendPoint]

