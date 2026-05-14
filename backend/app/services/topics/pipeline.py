from __future__ import annotations

from collections import defaultdict
from datetime import datetime, timezone
from uuid import UUID

from sqlalchemy.orm import Session

from app.db.models import JobPosting, JobTopic, Topic, TopicTimeseries


def _week_bucket_start(dt: datetime) -> datetime:
    if dt.tzinfo is None:
        dt = dt.replace(tzinfo=timezone.utc)
    # Monday 00:00 UTC
    monday = dt.date().toordinal() - dt.weekday()
    d = datetime.fromordinal(monday).replace(tzinfo=timezone.utc)
    return d


def _job_skills_document(job: JobPosting) -> str:
    """Space-separated skill strings for TF-IDF (same fields as events pipeline)."""
    parts: list[str] = []
    for raw in (job.required_skills_raw or []) + (job.preferred_skills_raw or []):
        if not raw:
            continue
        s = str(raw).strip().lower()
        if s:
            parts.append(s)
    return " ".join(parts)


def recompute_topics(db: Session, *, n_topics: int = 8, method: str = "nmf") -> dict:
    jobs = db.query(JobPosting).order_by(JobPosting.crawled_at.desc()).limit(5000).all()
    if not jobs:
        return {"topics": 0, "jobs_labeled": 0}

    jobs_fit: list[JobPosting] = []
    docs: list[str] = []
    for j in jobs:
        doc = _job_skills_document(j)
        if doc.strip():
            jobs_fit.append(j)
            docs.append(doc)
    if len(docs) < 2:
        return {"topics": 0, "jobs_labeled": 0}

    from sklearn.decomposition import NMF
    from sklearn.feature_extraction.text import TfidfVectorizer

    vectorizer = TfidfVectorizer(
        max_features=20000,
        stop_words=None,
        ngram_range=(1, 2),
        min_df=2,
        token_pattern=r"(?u)\b\w\w+\b",
    )
    X = vectorizer.fit_transform(docs)
    n_topics = min(n_topics, max(2, X.shape[0] // 10))
    model = NMF(n_components=n_topics, random_state=42, init="nndsvda", max_iter=300)
    W = model.fit_transform(X)
    H = model.components_

    feature_names = vectorizer.get_feature_names_out()

    # Delete previous nmf topics (simple MVP behavior)
    old_topics = db.query(Topic).filter(Topic.method == method).all()
    old_topic_ids = [t.id for t in old_topics]
    if old_topic_ids:
        db.query(JobTopic).filter(JobTopic.topic_id.in_(old_topic_ids)).delete(synchronize_session=False)
        db.query(TopicTimeseries).filter(TopicTimeseries.topic_id.in_(old_topic_ids)).delete(
            synchronize_session=False
        )
        db.query(Topic).filter(Topic.method == method).delete(synchronize_session=False)
        db.flush()

    topics: list[Topic] = []
    for i in range(n_topics):
        top_idx = H[i].argsort()[::-1][:10]
        keywords = [str(feature_names[j]) for j in top_idx]
        t = Topic(name=f"Topic {i+1}", keywords=keywords, method=method)
        db.add(t)
        topics.append(t)
    db.flush()

    # Assign best topic per job (only jobs that contributed skill text)
    jobs_labeled = 0
    for job, w in zip(jobs_fit, W, strict=False):
        best = int(w.argmax())
        score = float(w[best])
        db.add(JobTopic(job_id=job.id, topic_id=topics[best].id, score=int(score * 1000)))
        jobs_labeled += 1

    # Timeseries counts per week
    counts: dict[tuple[UUID, datetime], int] = defaultdict(int)
    for job, w in zip(jobs_fit, W, strict=False):
        best = int(w.argmax())
        bucket_start = _week_bucket_start(job.crawled_at)
        counts[(topics[best].id, bucket_start)] += 1

    for (topic_id, bucket_start), count in counts.items():
        db.add(
            TopicTimeseries(
                topic_id=topic_id,
                bucket="week",
                bucket_start=bucket_start,
                count=count,
            )
        )

    return {"topics": len(topics), "jobs_labeled": jobs_labeled}

