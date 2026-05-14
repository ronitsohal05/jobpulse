"""init schema

Revision ID: 0001_init_schema
Revises: 
Create Date: 2026-05-07

"""

from __future__ import annotations

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql


revision = "0001_init_schema"
down_revision = None
branch_labels = None
depends_on = None


def upgrade() -> None:
    # IMPORTANT: Postgres ENUM types must not be auto-created twice.
    # We explicitly create them (checkfirst=True) and then use create_type=False
    # when attaching to columns so table DDL doesn't attempt to recreate them.
    embedding_entity_type = postgresql.ENUM(
        "job", "resume", "skill", name="embedding_entity_type", create_type=False
    )
    crawl_status = postgresql.ENUM(
        "success", "error", "skipped", name="crawl_status", create_type=False
    )
    job_category = postgresql.ENUM(
        "software_engineering",
        "machine_learning",
        "data_science",
        "frontend",
        "backend",
        "devops",
        "quant",
        "research",
        "cybersecurity",
        "other",
        name="job_category",
        create_type=False,
    )

    embedding_entity_type.create(op.get_bind(), checkfirst=True)
    crawl_status.create(op.get_bind(), checkfirst=True)
    job_category.create(op.get_bind(), checkfirst=True)

    op.create_table(
        "users",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("email", sa.String(length=320), nullable=True, unique=True),
        sa.Column("display_name", sa.String(length=200), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
    )

    op.create_table(
        "resumes",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("user_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("users.id", ondelete="SET NULL"), nullable=True),
        sa.Column("filename", sa.String(length=512), nullable=False),
        sa.Column("content_type", sa.String(length=200), nullable=False),
        sa.Column("file_bytes", sa.LargeBinary(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
    )

    op.create_table(
        "parsed_resume_data",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("resume_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("resumes.id", ondelete="CASCADE"), nullable=False, unique=True),
        sa.Column("data", sa.JSON(), nullable=False),
        sa.Column("text_content", sa.Text(), nullable=False),
        sa.Column("experience_years", sa.Integer(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
    )

    op.create_table(
        "job_postings",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("source", sa.String(length=200), nullable=True),
        sa.Column("source_url", sa.Text(), nullable=False),
        sa.Column("normalized_url", sa.Text(), nullable=False),
        sa.Column("title", sa.String(length=400), nullable=False),
        sa.Column("company", sa.String(length=400), nullable=False),
        sa.Column("location", sa.String(length=400), nullable=True),
        sa.Column("employment_type", sa.String(length=200), nullable=True),
        sa.Column("experience_level", sa.String(length=200), nullable=True),
        sa.Column("salary", sa.String(length=200), nullable=True),
        sa.Column("description", sa.Text(), nullable=False),
        sa.Column("required_skills_raw", sa.JSON(), nullable=True),
        sa.Column("preferred_skills_raw", sa.JSON(), nullable=True),
        sa.Column("date_posted", sa.DateTime(timezone=True), nullable=True),
        sa.Column("crawled_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("job_hash", sa.String(length=64), nullable=False),
        sa.Column("raw_html", sa.Text(), nullable=True),
        sa.Column("category", job_category, nullable=False, server_default="other"),
        sa.Column("category_confidence", sa.Integer(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.CheckConstraint("category_confidence IS NULL OR category_confidence BETWEEN 0 AND 100"),
        sa.UniqueConstraint("normalized_url", name="uq_job_postings_normalized_url"),
    )
    op.create_index("ix_job_postings_company_title", "job_postings", ["company", "title"])
    op.create_index("ix_job_postings_job_hash", "job_postings", ["job_hash"])

    op.create_table(
        "skills",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("canonical", sa.String(length=200), nullable=False, unique=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
    )

    op.create_table(
        "job_skills",
        sa.Column("job_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("job_postings.id", ondelete="CASCADE"), primary_key=True),
        sa.Column("skill_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("skills.id", ondelete="CASCADE"), primary_key=True),
        sa.Column("kind", sa.String(length=50), nullable=False, server_default="required"),
    )
    op.create_index("ix_job_skills_skill_id", "job_skills", ["skill_id"])

    op.create_table(
        "resume_skills",
        sa.Column("resume_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("resumes.id", ondelete="CASCADE"), primary_key=True),
        sa.Column("skill_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("skills.id", ondelete="CASCADE"), primary_key=True),
        sa.Column("weight", sa.Integer(), nullable=False, server_default="1"),
    )
    op.create_index("ix_resume_skills_skill_id", "resume_skills", ["skill_id"])

    op.create_table(
        "embeddings",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("entity_type", embedding_entity_type, nullable=False),
        sa.Column("entity_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("model", sa.String(length=200), nullable=False),
        sa.Column("dims", sa.Integer(), nullable=False),
        sa.Column("faiss_id", sa.Integer(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.UniqueConstraint("entity_type", "entity_id", "model", name="uq_embeddings_entity_model"),
    )
    op.create_index("ix_embeddings_entity_id", "embeddings", ["entity_id"])
    op.create_index("ix_embeddings_faiss_id", "embeddings", ["faiss_id"])

    op.create_table(
        "topics",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("name", sa.String(length=200), nullable=False),
        sa.Column("keywords", sa.JSON(), nullable=False),
        sa.Column("method", sa.String(length=100), nullable=False, server_default="nmf"),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.UniqueConstraint("name", "method", name="uq_topics_name_method"),
    )

    op.create_table(
        "job_topics",
        sa.Column("job_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("job_postings.id", ondelete="CASCADE"), primary_key=True),
        sa.Column("topic_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("topics.id", ondelete="CASCADE"), primary_key=True),
        sa.Column("score", sa.Integer(), nullable=False, server_default="0"),
    )

    op.create_table(
        "topic_timeseries",
        sa.Column("topic_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("topics.id", ondelete="CASCADE"), primary_key=True),
        sa.Column("bucket", sa.String(length=20), primary_key=True),
        sa.Column("bucket_start", sa.DateTime(timezone=True), primary_key=True),
        sa.Column("count", sa.Integer(), nullable=False),
    )
    op.create_index(
        "ix_topic_timeseries_bucket_start",
        "topic_timeseries",
        ["bucket", "bucket_start"],
    )

    op.create_table(
        "events",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("entity_type", sa.String(length=30), nullable=False),
        sa.Column("entity_value", sa.String(length=200), nullable=False),
        sa.Column("bucket", sa.String(length=20), nullable=False, server_default="week"),
        sa.Column("bucket_start", sa.DateTime(timezone=True), nullable=False),
        sa.Column("current_value", sa.Integer(), nullable=False),
        sa.Column("mean", sa.Float(), nullable=False, server_default="0"),
        sa.Column("std", sa.Float(), nullable=False, server_default="0"),
        sa.Column("z_score", sa.Float(), nullable=False, server_default="0"),
        sa.Column("detected_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("message", sa.Text(), nullable=False),
    )
    op.create_index("ix_events_detected_at", "events", ["detected_at"])

    op.create_table(
        "analytics_snapshots",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("name", sa.String(length=200), nullable=False),
        sa.Column("generated_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("payload", sa.JSON(), nullable=False),
    )

    op.create_table(
        "crawler_sources",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("name", sa.String(length=200), nullable=False, unique=True),
        sa.Column("base_url", sa.Text(), nullable=False),
        sa.Column("allowed_domain", sa.String(length=200), nullable=False),
        sa.Column("job_link_pattern", sa.String(length=400), nullable=True),
        sa.Column("crawl_frequency", sa.String(length=50), nullable=False, server_default="daily"),
        sa.Column("max_pages", sa.Integer(), nullable=False, server_default="100"),
        sa.Column("enabled", sa.Boolean(), nullable=False, server_default=sa.text("true")),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
    )

    op.create_table(
        "crawl_logs",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("source_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("crawler_sources.id", ondelete="SET NULL"), nullable=True),
        sa.Column("url", sa.Text(), nullable=False),
        sa.Column("status", crawl_status, nullable=False),
        sa.Column("http_status", sa.Integer(), nullable=True),
        sa.Column("message", sa.Text(), nullable=True),
        sa.Column("jobs_extracted", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("duplicates_skipped", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("pages_fetched", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
    )
    op.create_index(
        "ix_crawl_logs_source_id_created_at",
        "crawl_logs",
        ["source_id", "created_at"],
    )


def downgrade() -> None:
    op.drop_index("ix_crawl_logs_source_id_created_at", table_name="crawl_logs")
    op.drop_table("crawl_logs")
    op.drop_table("crawler_sources")
    op.drop_table("analytics_snapshots")
    op.drop_index("ix_events_detected_at", table_name="events")
    op.drop_table("events")
    op.drop_index("ix_topic_timeseries_bucket_start", table_name="topic_timeseries")
    op.drop_table("topic_timeseries")
    op.drop_table("job_topics")
    op.drop_table("topics")
    op.drop_index("ix_embeddings_faiss_id", table_name="embeddings")
    op.drop_index("ix_embeddings_entity_id", table_name="embeddings")
    op.drop_table("embeddings")
    op.drop_index("ix_resume_skills_skill_id", table_name="resume_skills")
    op.drop_table("resume_skills")
    op.drop_index("ix_job_skills_skill_id", table_name="job_skills")
    op.drop_table("job_skills")
    op.drop_table("skills")
    op.drop_index("ix_job_postings_job_hash", table_name="job_postings")
    op.drop_index("ix_job_postings_company_title", table_name="job_postings")
    op.drop_table("job_postings")
    op.drop_table("parsed_resume_data")
    op.drop_table("resumes")
    op.drop_table("users")

    op.execute("DROP TYPE IF EXISTS embedding_entity_type")
    op.execute("DROP TYPE IF EXISTS crawl_status")
    op.execute("DROP TYPE IF EXISTS job_category")

