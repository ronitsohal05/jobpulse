from __future__ import annotations

import enum
import hashlib
from datetime import datetime
from typing import Any
from uuid import UUID, uuid4

from sqlalchemy import (
    JSON,
    Boolean,
    CheckConstraint,
    DateTime,
    Enum,
    ForeignKey,
    Float,
    Index,
    Integer,
    LargeBinary,
    String,
    Text,
    UniqueConstraint,
)
from sqlalchemy.dialects.postgresql import UUID as PG_UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base, TimestampMixin


class EmbeddingEntityType(str, enum.Enum):
    job = "job"
    resume = "resume"
    skill = "skill"


class CrawlStatus(str, enum.Enum):
    success = "success"
    error = "error"
    skipped = "skipped"


class JobCategory(str, enum.Enum):
    software_engineering = "software_engineering"
    machine_learning = "machine_learning"
    data_science = "data_science"
    frontend = "frontend"
    backend = "backend"
    devops = "devops"
    quant = "quant"
    research = "research"
    cybersecurity = "cybersecurity"
    other = "other"


class ApplicationStatus(str, enum.Enum):
    interested = "interested"
    applied = "applied"
    screening = "screening"
    interview = "interview"
    offer = "offer"
    rejected = "rejected"
    withdrawn = "withdrawn"


class User(TimestampMixin, Base):
    __tablename__ = "users"

    id: Mapped[UUID] = mapped_column(PG_UUID(as_uuid=True), primary_key=True, default=uuid4)
    email: Mapped[str | None] = mapped_column(String(320), unique=True, nullable=True)
    display_name: Mapped[str | None] = mapped_column(String(200), nullable=True)


class Resume(TimestampMixin, Base):
    __tablename__ = "resumes"

    id: Mapped[UUID] = mapped_column(PG_UUID(as_uuid=True), primary_key=True, default=uuid4)
    user_id: Mapped[UUID | None] = mapped_column(
        PG_UUID(as_uuid=True), ForeignKey("users.id", ondelete="SET NULL"), nullable=True
    )
    filename: Mapped[str] = mapped_column(String(512), nullable=False)
    content_type: Mapped[str] = mapped_column(String(200), nullable=False)
    file_bytes: Mapped[bytes] = mapped_column(LargeBinary, nullable=False)

    parsed: Mapped["ParsedResumeData | None"] = relationship(
        back_populates="resume", cascade="all, delete-orphan", uselist=False
    )


class ParsedResumeData(TimestampMixin, Base):
    __tablename__ = "parsed_resume_data"

    id: Mapped[UUID] = mapped_column(PG_UUID(as_uuid=True), primary_key=True, default=uuid4)
    resume_id: Mapped[UUID] = mapped_column(
        PG_UUID(as_uuid=True),
        ForeignKey("resumes.id", ondelete="CASCADE"),
        nullable=False,
        unique=True,
    )
    data: Mapped[dict[str, Any]] = mapped_column(JSON, nullable=False)
    text_content: Mapped[str] = mapped_column(Text, nullable=False)
    experience_years: Mapped[int | None] = mapped_column(Integer, nullable=True)

    resume: Mapped["Resume"] = relationship(back_populates="parsed")


class JobPosting(TimestampMixin, Base):
    __tablename__ = "job_postings"

    id: Mapped[UUID] = mapped_column(PG_UUID(as_uuid=True), primary_key=True, default=uuid4)

    source: Mapped[str | None] = mapped_column(String(200), nullable=True)
    source_url: Mapped[str] = mapped_column(Text, nullable=False)
    normalized_url: Mapped[str] = mapped_column(Text, nullable=False)

    title: Mapped[str] = mapped_column(String(400), nullable=False)
    company: Mapped[str] = mapped_column(String(400), nullable=False)
    location: Mapped[str | None] = mapped_column(String(400), nullable=True)
    employment_type: Mapped[str | None] = mapped_column(String(200), nullable=True)
    experience_level: Mapped[str | None] = mapped_column(String(200), nullable=True)
    salary: Mapped[str | None] = mapped_column(String(200), nullable=True)

    description: Mapped[str] = mapped_column(Text, nullable=False)
    required_skills_raw: Mapped[list[str] | None] = mapped_column(JSON, nullable=True)
    preferred_skills_raw: Mapped[list[str] | None] = mapped_column(JSON, nullable=True)

    date_posted: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    crawled_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)

    job_hash: Mapped[str] = mapped_column(String(64), nullable=False, index=True)
    raw_html: Mapped[str | None] = mapped_column(Text, nullable=True)

    category: Mapped[JobCategory] = mapped_column(
        Enum(JobCategory, name="job_category"),
        nullable=False,
        default=JobCategory.other,
    )
    category_confidence: Mapped[int | None] = mapped_column(
        Integer,
        nullable=True,
        doc="0-100 confidence",
    )

    __table_args__ = (
        UniqueConstraint("normalized_url", name="uq_job_postings_normalized_url"),
        Index("ix_job_postings_company_title", "company", "title"),
        CheckConstraint("category_confidence IS NULL OR category_confidence BETWEEN 0 AND 100"),
    )

    @staticmethod
    def compute_job_hash(company: str, title: str, location: str | None, description: str) -> str:
        normalized_description = " ".join(description.split()).strip().lower()
        raw = f"{company.strip().lower()}|{title.strip().lower()}|{(location or '').strip().lower()}|{normalized_description}"
        return hashlib.sha256(raw.encode("utf-8")).hexdigest()


class Skill(TimestampMixin, Base):
    __tablename__ = "skills"

    id: Mapped[UUID] = mapped_column(PG_UUID(as_uuid=True), primary_key=True, default=uuid4)
    canonical: Mapped[str] = mapped_column(String(200), nullable=False, unique=True)


class JobSkill(Base):
    __tablename__ = "job_skills"

    job_id: Mapped[UUID] = mapped_column(
        PG_UUID(as_uuid=True),
        ForeignKey("job_postings.id", ondelete="CASCADE"),
        primary_key=True,
    )
    skill_id: Mapped[UUID] = mapped_column(
        PG_UUID(as_uuid=True), ForeignKey("skills.id", ondelete="CASCADE"), primary_key=True
    )
    kind: Mapped[str] = mapped_column(String(50), nullable=False, default="required")

    __table_args__ = (Index("ix_job_skills_skill_id", "skill_id"),)


class ResumeSkill(Base):
    __tablename__ = "resume_skills"

    resume_id: Mapped[UUID] = mapped_column(
        PG_UUID(as_uuid=True),
        ForeignKey("resumes.id", ondelete="CASCADE"),
        primary_key=True,
    )
    skill_id: Mapped[UUID] = mapped_column(
        PG_UUID(as_uuid=True), ForeignKey("skills.id", ondelete="CASCADE"), primary_key=True
    )
    weight: Mapped[int] = mapped_column(Integer, nullable=False, default=1)

    __table_args__ = (Index("ix_resume_skills_skill_id", "skill_id"),)


class Embedding(TimestampMixin, Base):
    __tablename__ = "embeddings"

    id: Mapped[UUID] = mapped_column(PG_UUID(as_uuid=True), primary_key=True, default=uuid4)
    entity_type: Mapped[EmbeddingEntityType] = mapped_column(
        Enum(EmbeddingEntityType, name="embedding_entity_type"), nullable=False
    )
    entity_id: Mapped[UUID] = mapped_column(PG_UUID(as_uuid=True), nullable=False, index=True)
    model: Mapped[str] = mapped_column(String(200), nullable=False)
    dims: Mapped[int] = mapped_column(Integer, nullable=False)
    faiss_id: Mapped[int] = mapped_column(Integer, nullable=False, index=True)

    __table_args__ = (
        UniqueConstraint(
            "entity_type", "entity_id", "model", name="uq_embeddings_entity_model"
        ),
    )


class Topic(TimestampMixin, Base):
    __tablename__ = "topics"

    id: Mapped[UUID] = mapped_column(PG_UUID(as_uuid=True), primary_key=True, default=uuid4)
    name: Mapped[str] = mapped_column(String(200), nullable=False)
    keywords: Mapped[list[str]] = mapped_column(JSON, nullable=False, default=list)
    method: Mapped[str] = mapped_column(String(100), nullable=False, default="nmf")

    __table_args__ = (UniqueConstraint("name", "method", name="uq_topics_name_method"),)


class JobTopic(Base):
    __tablename__ = "job_topics"

    job_id: Mapped[UUID] = mapped_column(
        PG_UUID(as_uuid=True),
        ForeignKey("job_postings.id", ondelete="CASCADE"),
        primary_key=True,
    )
    topic_id: Mapped[UUID] = mapped_column(
        PG_UUID(as_uuid=True), ForeignKey("topics.id", ondelete="CASCADE"), primary_key=True
    )
    score: Mapped[int] = mapped_column(Integer, nullable=False, default=0)


class TopicTimeseries(Base):
    __tablename__ = "topic_timeseries"

    topic_id: Mapped[UUID] = mapped_column(
        PG_UUID(as_uuid=True), ForeignKey("topics.id", ondelete="CASCADE"), primary_key=True
    )
    bucket: Mapped[str] = mapped_column(String(20), primary_key=True, default="week")
    bucket_start: Mapped[datetime] = mapped_column(DateTime(timezone=True), primary_key=True)
    count: Mapped[int] = mapped_column(Integer, nullable=False)

    __table_args__ = (Index("ix_topic_timeseries_bucket_start", "bucket", "bucket_start"),)


class Event(Base):
    __tablename__ = "events"

    id: Mapped[UUID] = mapped_column(PG_UUID(as_uuid=True), primary_key=True, default=uuid4)
    entity_type: Mapped[str] = mapped_column(String(30), nullable=False)  # skill/topic/keyword
    entity_value: Mapped[str] = mapped_column(String(200), nullable=False)
    bucket: Mapped[str] = mapped_column(String(20), nullable=False, default="week")
    bucket_start: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    current_value: Mapped[int] = mapped_column(Integer, nullable=False)
    mean: Mapped[float] = mapped_column(Float, nullable=False, default=0.0)
    std: Mapped[float] = mapped_column(Float, nullable=False, default=0.0)
    z_score: Mapped[float] = mapped_column(Float, nullable=False, default=0.0)
    detected_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    message: Mapped[str] = mapped_column(Text, nullable=False)

    __table_args__ = (Index("ix_events_detected_at", "detected_at"),)


class JobApplication(TimestampMixin, Base):
    """Tracks a user's progress on a job (from our index or external URL)."""

    __tablename__ = "job_applications"

    id: Mapped[UUID] = mapped_column(PG_UUID(as_uuid=True), primary_key=True, default=uuid4)
    job_posting_id: Mapped[UUID | None] = mapped_column(
        PG_UUID(as_uuid=True),
        ForeignKey("job_postings.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
    )
    resume_id: Mapped[UUID | None] = mapped_column(
        PG_UUID(as_uuid=True),
        ForeignKey("resumes.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
    )
    title: Mapped[str] = mapped_column(String(400), nullable=False)
    company: Mapped[str] = mapped_column(String(400), nullable=False)
    location: Mapped[str | None] = mapped_column(String(400), nullable=True)
    source_url: Mapped[str] = mapped_column(Text, nullable=False)
    normalized_url: Mapped[str] = mapped_column(Text, nullable=False)
    status: Mapped[ApplicationStatus] = mapped_column(
        Enum(ApplicationStatus, name="application_status"),
        nullable=False,
        default=ApplicationStatus.interested,
    )
    applied_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    next_follow_up_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    notes: Mapped[str | None] = mapped_column(Text, nullable=True)

    __table_args__ = (
        UniqueConstraint("resume_id", "normalized_url", name="uq_job_applications_resume_normalized_url"),
        Index("ix_job_applications_status_updated", "status", "updated_at"),
    )


class AnalyticsSnapshot(Base):
    __tablename__ = "analytics_snapshots"

    id: Mapped[UUID] = mapped_column(PG_UUID(as_uuid=True), primary_key=True, default=uuid4)
    name: Mapped[str] = mapped_column(String(200), nullable=False)
    generated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    payload: Mapped[dict[str, Any]] = mapped_column(JSON, nullable=False)


class CrawlerSource(TimestampMixin, Base):
    __tablename__ = "crawler_sources"

    id: Mapped[UUID] = mapped_column(PG_UUID(as_uuid=True), primary_key=True, default=uuid4)
    name: Mapped[str] = mapped_column(String(200), nullable=False, unique=True)
    base_url: Mapped[str] = mapped_column(Text, nullable=False)
    allowed_domain: Mapped[str] = mapped_column(String(200), nullable=False)
    job_link_pattern: Mapped[str | None] = mapped_column(String(400), nullable=True)
    crawl_frequency: Mapped[str] = mapped_column(String(50), nullable=False, default="daily")
    max_pages: Mapped[int] = mapped_column(Integer, nullable=False, default=100)
    enabled: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)


class CrawlLog(TimestampMixin, Base):
    __tablename__ = "crawl_logs"

    id: Mapped[UUID] = mapped_column(PG_UUID(as_uuid=True), primary_key=True, default=uuid4)
    source_id: Mapped[UUID | None] = mapped_column(
        PG_UUID(as_uuid=True), ForeignKey("crawler_sources.id", ondelete="SET NULL"), nullable=True
    )
    url: Mapped[str] = mapped_column(Text, nullable=False)
    status: Mapped[CrawlStatus] = mapped_column(
        Enum(CrawlStatus, name="crawl_status"), nullable=False
    )
    http_status: Mapped[int | None] = mapped_column(Integer, nullable=True)
    message: Mapped[str | None] = mapped_column(Text, nullable=True)
    jobs_extracted: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    duplicates_skipped: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    pages_fetched: Mapped[int] = mapped_column(Integer, nullable=False, default=0)

    __table_args__ = (Index("ix_crawl_logs_source_id_created_at", "source_id", "created_at"),)

