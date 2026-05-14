from __future__ import annotations

from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.db.models import Topic, TopicTimeseries
from app.db.session import get_db
from app.schemas.topics import TopicOut, TopicTrendPoint, TopicWithTrend
from app.services.topics.pipeline import recompute_topics


router = APIRouter(prefix="/api/topics", tags=["topics"])


@router.post("/recompute")
def recompute(db: Session = Depends(get_db)) -> dict:
    result = recompute_topics(db=db)
    db.commit()
    return result


@router.get("", response_model=list[TopicWithTrend])
def list_topics(db: Session = Depends(get_db)) -> list[TopicWithTrend]:
    topics = db.query(Topic).order_by(Topic.created_at.desc()).all()
    out: list[TopicWithTrend] = []
    for t in topics:
        points = (
            db.query(TopicTimeseries)
            .filter(TopicTimeseries.topic_id == t.id, TopicTimeseries.bucket == "week")
            .order_by(TopicTimeseries.bucket_start.asc())
            .limit(52)
            .all()
        )
        out.append(
            TopicWithTrend(
                topic=TopicOut(id=t.id, name=t.name, keywords=t.keywords, method=t.method),
                trend=[TopicTrendPoint(bucket_start=p.bucket_start, count=p.count) for p in points],
            )
        )
    return out

