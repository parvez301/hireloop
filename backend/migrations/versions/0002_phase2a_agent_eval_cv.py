"""phase2a_agent_eval_cv

Revision ID: 0002_phase2a
Revises: 0001_phase1
Create Date: 2026-04-10

Adds jobs, evaluations, evaluation_cache, cv_outputs, conversations,
messages, and usage_events tables with their indexes.
"""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision: str = "0002_phase2a"
down_revision: Union[str, None] = "0001_phase1"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "jobs",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("content_hash", sa.String(64), nullable=False),
        sa.Column("url", sa.String(2048), nullable=True),
        sa.Column("title", sa.String(512), nullable=False),
        sa.Column("company", sa.String(255), nullable=True),
        sa.Column("location", sa.String(255), nullable=True),
        sa.Column("salary_min", sa.Integer(), nullable=True),
        sa.Column("salary_max", sa.Integer(), nullable=True),
        sa.Column("employment_type", sa.String(64), nullable=True),
        sa.Column("seniority", sa.String(64), nullable=True),
        sa.Column("description_md", sa.Text(), nullable=False),
        sa.Column("requirements_json", postgresql.JSONB(astext_type=sa.Text()), nullable=True),
        sa.Column("source", sa.String(32), nullable=False),
        sa.Column("board_company", sa.String(255), nullable=True),
        sa.Column(
            "discovered_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.Column("expires_at", sa.DateTime(timezone=True), nullable=True),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("content_hash", name="uq_jobs_content_hash"),
    )
    op.create_index("idx_jobs_content_hash", "jobs", ["content_hash"])
    op.create_index("idx_jobs_company", "jobs", ["company"])
    op.create_index("idx_jobs_source", "jobs", ["source"])
    op.create_index("idx_jobs_discovered_at", "jobs", [sa.text("discovered_at DESC")])

    op.create_table(
        "evaluations",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("user_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("job_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("overall_grade", sa.String(4), nullable=False),
        sa.Column("dimension_scores", postgresql.JSONB(astext_type=sa.Text()), nullable=False),
        sa.Column("reasoning", sa.Text(), nullable=False),
        sa.Column("red_flags", postgresql.JSONB(astext_type=sa.Text()), nullable=True),
        sa.Column("personalization", sa.Text(), nullable=True),
        sa.Column("match_score", sa.Float(), nullable=False),
        sa.Column("recommendation", sa.String(32), nullable=False),
        sa.Column("model_used", sa.String(64), nullable=False),
        sa.Column("tokens_used", sa.Integer(), nullable=True),
        sa.Column("cached", sa.Boolean(), nullable=False, server_default=sa.text("false")),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["job_id"], ["jobs.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("user_id", "job_id", name="uq_evaluations_user_job"),
    )
    op.create_index("idx_evaluations_user_id", "evaluations", ["user_id"])
    op.create_index("idx_evaluations_job_id", "evaluations", ["job_id"])
    op.create_index(
        "idx_evaluations_user_created",
        "evaluations",
        ["user_id", sa.text("created_at DESC")],
    )
    op.create_index(
        "idx_evaluations_user_grade",
        "evaluations",
        ["user_id", "overall_grade"],
    )

    op.create_table(
        "evaluation_cache",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("content_hash", sa.String(64), nullable=False),
        sa.Column("base_evaluation", postgresql.JSONB(astext_type=sa.Text()), nullable=False),
        sa.Column("requirements_json", postgresql.JSONB(astext_type=sa.Text()), nullable=False),
        sa.Column("model_used", sa.String(64), nullable=False),
        sa.Column("hit_count", sa.Integer(), nullable=False, server_default=sa.text("0")),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("content_hash", name="uq_evaluation_cache_content_hash"),
    )
    op.create_index("idx_eval_cache_content_hash", "evaluation_cache", ["content_hash"])
    op.create_index("idx_eval_cache_created", "evaluation_cache", ["created_at"])

    op.create_table(
        "cv_outputs",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("user_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("job_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("tailored_md", sa.Text(), nullable=False),
        sa.Column("pdf_s3_key", sa.String(512), nullable=False),
        sa.Column("changes_summary", sa.Text(), nullable=True),
        sa.Column("model_used", sa.String(64), nullable=False),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["job_id"], ["jobs.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("idx_cv_outputs_user_id", "cv_outputs", ["user_id"])
    op.create_index(
        "idx_cv_outputs_user_created",
        "cv_outputs",
        ["user_id", sa.text("created_at DESC")],
    )

    op.create_table(
        "conversations",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("user_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("title", sa.String(255), nullable=True),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("idx_conversations_user_id", "conversations", ["user_id"])
    op.create_index(
        "idx_conversations_user_updated",
        "conversations",
        ["user_id", sa.text("updated_at DESC")],
    )

    op.create_table(
        "messages",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("conversation_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("role", sa.String(16), nullable=False),
        sa.Column("content", sa.Text(), nullable=False, server_default=sa.text("''")),
        sa.Column("tool_calls", postgresql.JSONB(astext_type=sa.Text()), nullable=True),
        sa.Column("cards", postgresql.JSONB(astext_type=sa.Text()), nullable=True),
        sa.Column("metadata", postgresql.JSONB(astext_type=sa.Text()), nullable=True),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.ForeignKeyConstraint(
            ["conversation_id"], ["conversations.id"], ondelete="CASCADE"
        ),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("idx_messages_conv_created", "messages", ["conversation_id", "created_at"])

    op.create_table(
        "usage_events",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("user_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("event_type", sa.String(32), nullable=False),
        sa.Column("module", sa.String(32), nullable=True),
        sa.Column("model", sa.String(64), nullable=True),
        sa.Column("tokens_used", sa.Integer(), nullable=True),
        sa.Column("cost_cents", sa.Integer(), nullable=True),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("idx_usage_user_created", "usage_events", ["user_id", sa.text("created_at DESC")])
    op.create_index(
        "idx_usage_user_type_created",
        "usage_events",
        ["user_id", "event_type", sa.text("created_at DESC")],
    )


def downgrade() -> None:
    op.drop_index("idx_usage_user_type_created", table_name="usage_events")
    op.drop_index("idx_usage_user_created", table_name="usage_events")
    op.drop_table("usage_events")

    op.drop_index("idx_messages_conv_created", table_name="messages")
    op.drop_table("messages")

    op.drop_index("idx_conversations_user_updated", table_name="conversations")
    op.drop_index("idx_conversations_user_id", table_name="conversations")
    op.drop_table("conversations")

    op.drop_index("idx_cv_outputs_user_created", table_name="cv_outputs")
    op.drop_index("idx_cv_outputs_user_id", table_name="cv_outputs")
    op.drop_table("cv_outputs")

    op.drop_index("idx_eval_cache_created", table_name="evaluation_cache")
    op.drop_index("idx_eval_cache_content_hash", table_name="evaluation_cache")
    op.drop_table("evaluation_cache")

    op.drop_index("idx_evaluations_user_grade", table_name="evaluations")
    op.drop_index("idx_evaluations_user_created", table_name="evaluations")
    op.drop_index("idx_evaluations_job_id", table_name="evaluations")
    op.drop_index("idx_evaluations_user_id", table_name="evaluations")
    op.drop_table("evaluations")

    op.drop_index("idx_jobs_discovered_at", table_name="jobs")
    op.drop_index("idx_jobs_source", table_name="jobs")
    op.drop_index("idx_jobs_company", table_name="jobs")
    op.drop_index("idx_jobs_content_hash", table_name="jobs")
    op.drop_table("jobs")
