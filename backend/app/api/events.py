from __future__ import annotations

from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.db.models import Event
from app.db.session import get_db
from app.schemas.events import EventOut
from app.services.events.pipeline import recompute_events


router = APIRouter(prefix="/api/events", tags=["events"])


@router.post("/recompute")
def recompute(db: Session = Depends(get_db)) -> dict:
    result = recompute_events(db=db)
    db.commit()
    return result


@router.get("", response_model=list[EventOut])
def list_events(db: Session = Depends(get_db), limit: int = 50) -> list[EventOut]:
    rows = db.query(Event).order_by(Event.z_score.desc()).limit(min(limit, 200)).all()
    return [
        EventOut(
            id=r.id,
            entity_type=r.entity_type,
            entity_value=r.entity_value,
            bucket=r.bucket,
            bucket_start=r.bucket_start,
            current_value=r.current_value,
            mean=r.mean,
            std=r.std,
            z_score=r.z_score,
            detected_at=r.detected_at,
            message=r.message,
        )
        for r in rows
    ]

