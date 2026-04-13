"""phase2d_interview_prep_negotiation_feedback

Revision ID: 0006_phase2d
Revises: 0005_phase2c
Create Date: 2026-04-11

Creates interview_preps, negotiations, feedback; adds FK from applications.negotiation_id.
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision: str = "0006_phase2d"
down_revision: str | None = "0005_phase2c"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "interview_preps",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("user_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("job_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("custom_role", sa.String(255), nullable=True),
        sa.Column("questions", postgresql.JSONB(astext_type=sa.Text()), nullable=False),
        sa.Column("red_flag_questions", postgresql.JSONB(astext_type=sa.Text()), nullable=True),
        sa.Column("model_used", sa.String(64), nullable=False),
        sa.Column("tokens_used", sa.Integer(), nullable=True),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.CheckConstraint(
            "(job_id IS NOT NULL AND custom_role IS NULL) "
            "OR (job_id IS NULL AND custom_role IS NOT NULL)",
            name="ck_interview_preps_job_xor_custom_role",
        ),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["job_id"], ["jobs.id"], ondelete="SET NULL"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("idx_interview_preps_user_id", "interview_preps", ["user_id"])
    op.create_index(
        "idx_interview_preps_user_created",
        "interview_preps",
        ["user_id", sa.text("created_at DESC")],
    )

    op.create_table(
        "negotiations",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("user_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("job_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("offer_details", postgresql.JSONB(astext_type=sa.Text()), nullable=False),
        sa.Column("market_research", postgresql.JSONB(astext_type=sa.Text()), nullable=False),
        sa.Column("counter_offer", postgresql.JSONB(astext_type=sa.Text()), nullable=False),
        sa.Column("scripts", postgresql.JSONB(astext_type=sa.Text()), nullable=False),
        sa.Column("model_used", sa.String(64), nullable=False),
        sa.Column("tokens_used", sa.Integer(), nullable=True),
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
    op.create_index("idx_negotiations_user_id", "negotiations", ["user_id"])
    op.create_index(
        "idx_negotiations_user_created",
        "negotiations",
        ["user_id", sa.text("created_at DESC")],
    )
    op.create_index("idx_negotiations_job_id", "negotiations", ["job_id"])

    op.create_table(
        "feedback",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("user_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("resource_type", sa.String(32), nullable=False),
        sa.Column("resource_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("rating", sa.Integer(), nullable=False),
        sa.Column("correction_notes", sa.Text(), nullable=True),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.CheckConstraint("rating >= 1 AND rating <= 5", name="ck_feedback_rating_1_5"),
        sa.CheckConstraint(
            "resource_type IN ('evaluation', 'cv_output', 'interview_prep', 'negotiation')",
            name="ck_feedback_resource_type",
        ),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint(
            "user_id",
            "resource_type",
            "resource_id",
            name="uq_feedback_user_resource",
        ),
    )
    op.create_index("idx_feedback_user_id", "feedback", ["user_id"])
    op.create_index(
        "idx_feedback_resource",
        "feedback",
        ["resource_type", "resource_id"],
    )
    op.create_index(
        "idx_feedback_created",
        "feedback",
        [sa.text("created_at DESC")],
    )

    op.create_foreign_key(
        "fk_applications_negotiation_id",
        "applications",
        "negotiations",
        ["negotiation_id"],
        ["id"],
        ondelete="SET NULL",
    )


def downgrade() -> None:
    op.drop_constraint("fk_applications_negotiation_id", "applications", type_="foreignkey")

    op.drop_index("idx_feedback_created", table_name="feedback")
    op.drop_index("idx_feedback_resource", table_name="feedback")
    op.drop_index("idx_feedback_user_id", table_name="feedback")
    op.drop_table("feedback")

    op.drop_index("idx_negotiations_job_id", table_name="negotiations")
    op.drop_index("idx_negotiations_user_created", table_name="negotiations")
    op.drop_index("idx_negotiations_user_id", table_name="negotiations")
    op.drop_table("negotiations")

    op.drop_index("idx_interview_preps_user_created", table_name="interview_preps")
    op.drop_index("idx_interview_preps_user_id", table_name="interview_preps")
    op.drop_table("interview_preps")
