from __future__ import annotations

from collections import defaultdict
from datetime import datetime, timedelta, timezone

from sqlalchemy.orm import Session

from app.db.models import Event, JobPosting


def _week_bucket_start(dt: datetime) -> datetime:
    if dt.tzinfo is None:
        dt = dt.replace(tzinfo=timezone.utc)
    monday = dt.date().toordinal() - dt.weekday()
    return datetime.fromordinal(monday).replace(tzinfo=timezone.utc)


def recompute_events(
    db: Session,
    *,
    lookback_weeks: int = 12,
    z_threshold: float = 2.0,
    max_events: int = 50,
) -> dict:
    jobs = db.query(JobPosting).order_by(JobPosting.crawled_at.desc()).limit(5000).all()
    if not jobs:
        return {"events": 0}

    # Count skill mentions per week using required_skills_raw/preferred_skills_raw.
    counts: dict[tuple[str, datetime], int] = defaultdict(int)
    for j in jobs:
        week = _week_bucket_start(j.crawled_at)
        for s in (j.required_skills_raw or []) + (j.preferred_skills_raw or []):
            if not s:
                continue
            counts[(str(s), week)] += 1

    if not counts:
        return {"events": 0}

    # Determine most recent week as "current"
    current_week = max(w for _, w in counts.keys())
    cutoff_week = current_week - timedelta(weeks=lookback_weeks)

    series_by_skill: dict[str, list[tuple[datetime, int]]] = defaultdict(list)
    for (skill, week), c in counts.items():
        if week < cutoff_week:
            continue
        series_by_skill[skill].append((week, c))

    # Clear existing events (MVP behavior)
    db.query(Event).delete(synchronize_session=False)
    db.flush()

    detected: list[Event] = []
    now = datetime.now(timezone.utc)
    for skill, series in series_by_skill.items():
        series.sort(key=lambda x: x[0])
        current = next((c for w, c in series if w == current_week), 0)
        history = [c for w, c in series if w != current_week]
        if len(history) < 4:
            continue
        mean = sum(history) / float(len(history))
        var = sum((c - mean) ** 2 for c in history) / float(len(history))
        std = max(var**0.5, 1e-6)
        z = (current - mean) / std
        if z >= z_threshold and current >= 5:
            msg = (
                f'NEW EVENT DETECTED: \"{skill}\" appeared in {current} postings this week '
                f"after averaging {mean:.1f} (z={z:.2f})."
            )
            detected.append(
                Event(
                    entity_type="skill",
                    entity_value=skill,
                    bucket="week",
                    bucket_start=current_week,
                    current_value=current,
                    mean=float(mean),
                    std=float(std),
                    z_score=float(z),
                    detected_at=now,
                    message=msg,
                )
            )

    detected.sort(key=lambda e: e.z_score, reverse=True)
    detected = detected[:max_events]
    for e in detected:
        db.add(e)

    return {"events": len(detected)}

