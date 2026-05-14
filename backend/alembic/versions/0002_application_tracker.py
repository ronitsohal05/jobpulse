"""job applications tracker

Revision ID: 0002_application_tracker
Revises: 0001_init_schema
Create Date: 2026-05-13

"""

from __future__ import annotations

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql


revision = "0002_application_tracker"
down_revision = "0001_init_schema"
branch_labels = None
depends_on = None


def upgrade() -> None:
    application_status = postgresql.ENUM(
        "interested",
        "applied",
        "screening",
        "interview",
        "offer",
        "rejected",
        "withdrawn",
        name="application_status",
        create_type=False,
    )
    application_status.create(op.get_bind(), checkfirst=True)

    op.create_table(
        "job_applications",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("job_posting_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("resume_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("title", sa.String(length=400), nullable=False),
        sa.Column("company", sa.String(length=400), nullable=False),
        sa.Column("location", sa.String(length=400), nullable=True),
        sa.Column("source_url", sa.Text(), nullable=False),
        sa.Column("normalized_url", sa.Text(), nullable=False),
        sa.Column(
            "status",
            postgresql.ENUM(
                "interested",
                "applied",
                "screening",
                "interview",
                "offer",
                "rejected",
                "withdrawn",
                name="application_status",
                create_type=False,
            ),
            nullable=False,
        ),
        sa.Column("applied_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("next_follow_up_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("notes", sa.Text(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.ForeignKeyConstraint(["job_posting_id"], ["job_postings.id"], ondelete="SET NULL"),
        sa.ForeignKeyConstraint(["resume_id"], ["resumes.id"], ondelete="SET NULL"),
        sa.UniqueConstraint("resume_id", "normalized_url", name="uq_job_applications_resume_normalized_url"),
    )
    op.create_index("ix_job_applications_job_posting_id", "job_applications", ["job_posting_id"], unique=False)
    op.create_index("ix_job_applications_resume_id", "job_applications", ["resume_id"], unique=False)
    op.create_index(
        "ix_job_applications_status_updated",
        "job_applications",
        ["status", "updated_at"],
        unique=False,
    )


def downgrade() -> None:
    op.drop_index("ix_job_applications_status_updated", table_name="job_applications")
    op.drop_index("ix_job_applications_resume_id", table_name="job_applications")
    op.drop_index("ix_job_applications_job_posting_id", table_name="job_applications")
    op.drop_table("job_applications")
    op.execute(sa.text("DROP TYPE IF EXISTS application_status"))
