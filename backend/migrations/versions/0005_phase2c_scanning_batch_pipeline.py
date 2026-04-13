"""phase2c_scanning_batch_pipeline

Revision ID: 0005_phase2c
Revises: 0004_phase2b1
Create Date: 2026-04-10

Adds scan_configs, scan_runs, scan_results, batch_runs, batch_items,
applications tables with their indexes.
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision: str = "0005_phase2c"
down_revision: str | None = "0004_phase2b1"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    # ---------- scan_configs ----------
    op.create_table(
        "scan_configs",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("user_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("name", sa.String(255), nullable=False),
        sa.Column("companies", postgresql.JSONB(astext_type=sa.Text()), nullable=False),
        sa.Column("keywords", postgresql.JSONB(astext_type=sa.Text()), nullable=True),
        sa.Column("exclude_keywords", postgresql.JSONB(astext_type=sa.Text()), nullable=True),
        sa.Column(
            "schedule",
            sa.String(32),
            nullable=False,
            server_default=sa.text("'manual'"),
        ),
        sa.Column(
            "is_active",
            sa.Boolean(),
            nullable=False,
            server_default=sa.text("true"),
        ),
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
    op.create_index("idx_scan_configs_user_id", "scan_configs", ["user_id"])

    # ---------- scan_runs ----------
    op.create_table(
        "scan_runs",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("user_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("scan_config_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("inngest_event_id", sa.String(255), nullable=True),
        sa.Column("status", sa.String(32), nullable=False),
        sa.Column("jobs_found", sa.Integer(), nullable=False, server_default=sa.text("0")),
        sa.Column("jobs_new", sa.Integer(), nullable=False, server_default=sa.text("0")),
        sa.Column("truncated", sa.Boolean(), nullable=False, server_default=sa.text("false")),
        sa.Column("error", sa.Text(), nullable=True),
        sa.Column(
            "started_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.Column("completed_at", sa.DateTime(timezone=True), nullable=True),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["scan_config_id"], ["scan_configs.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("idx_scan_runs_user_id", "scan_runs", ["user_id"])
    op.create_index("idx_scan_runs_status", "scan_runs", ["status"])
    op.create_index(
        "idx_scan_runs_user_started",
        "scan_runs",
        ["user_id", sa.text("started_at DESC")],
    )

    # ---------- scan_results ----------
    op.create_table(
        "scan_results",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("scan_run_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("job_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("relevance_score", sa.Float(), nullable=True),
        sa.Column("is_new", sa.Boolean(), nullable=False, server_default=sa.text("true")),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.ForeignKeyConstraint(["scan_run_id"], ["scan_runs.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["job_id"], ["jobs.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("scan_run_id", "job_id", name="uq_scan_results_run_job"),
    )
    op.create_index("idx_scan_results_run_id", "scan_results", ["scan_run_id"])
    op.create_index(
        "idx_scan_results_run_score",
        "scan_results",
        ["scan_run_id", sa.text("relevance_score DESC NULLS LAST")],
    )

    # ---------- batch_runs ----------
    op.create_table(
        "batch_runs",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("user_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("inngest_event_id", sa.String(255), nullable=True),
        sa.Column("status", sa.String(32), nullable=False),
        sa.Column("total_jobs", sa.Integer(), nullable=False),
        sa.Column("l0_passed", sa.Integer(), nullable=False, server_default=sa.text("0")),
        sa.Column("l1_passed", sa.Integer(), nullable=False, server_default=sa.text("0")),
        sa.Column("l2_evaluated", sa.Integer(), nullable=False, server_default=sa.text("0")),
        sa.Column("source_type", sa.String(32), nullable=False),
        sa.Column("source_ref", sa.String(255), nullable=True),
        sa.Column(
            "started_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.Column("completed_at", sa.DateTime(timezone=True), nullable=True),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("idx_batch_runs_user_id", "batch_runs", ["user_id"])
    op.create_index(
        "idx_batch_runs_user_started",
        "batch_runs",
        ["user_id", sa.text("started_at DESC")],
    )

    # ---------- batch_items ----------
    op.create_table(
        "batch_items",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("batch_run_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("job_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("evaluation_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("stage", sa.String(32), nullable=False),
        sa.Column("filter_reason", sa.String(64), nullable=True),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.ForeignKeyConstraint(["batch_run_id"], ["batch_runs.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["job_id"], ["jobs.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["evaluation_id"], ["evaluations.id"], ondelete="SET NULL"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("idx_batch_items_run_id", "batch_items", ["batch_run_id"])
    op.create_index(
        "idx_batch_items_run_stage",
        "batch_items",
        ["batch_run_id", "stage"],
    )

    # ---------- applications ----------
    op.create_table(
        "applications",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("user_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("job_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("status", sa.String(32), nullable=False),
        sa.Column("applied_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("notes", sa.Text(), nullable=True),
        sa.Column("evaluation_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("cv_output_id", postgresql.UUID(as_uuid=True), nullable=True),
        # Nullable FK-less column for Phase 2d — negotiations table doesn't exist yet.
        # The FK constraint is added in Phase 2d's migration alongside the negotiations table.
        sa.Column("negotiation_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["job_id"], ["jobs.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["evaluation_id"], ["evaluations.id"], ondelete="SET NULL"),
        sa.ForeignKeyConstraint(["cv_output_id"], ["cv_outputs.id"], ondelete="SET NULL"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("user_id", "job_id", name="uq_applications_user_job"),
    )
    op.create_index("idx_applications_user_id", "applications", ["user_id"])
    op.create_index(
        "idx_applications_user_status",
        "applications",
        ["user_id", "status"],
    )
    op.create_index(
        "idx_applications_updated",
        "applications",
        [sa.text("updated_at DESC")],
    )


def downgrade() -> None:
    op.drop_index("idx_applications_updated", table_name="applications")
    op.drop_index("idx_applications_user_status", table_name="applications")
    op.drop_index("idx_applications_user_id", table_name="applications")
    op.drop_table("applications")

    op.drop_index("idx_batch_items_run_stage", table_name="batch_items")
    op.drop_index("idx_batch_items_run_id", table_name="batch_items")
    op.drop_table("batch_items")

    op.drop_index("idx_batch_runs_user_started", table_name="batch_runs")
    op.drop_index("idx_batch_runs_user_id", table_name="batch_runs")
    op.drop_table("batch_runs")

    op.drop_index("idx_scan_results_run_score", table_name="scan_results")
    op.drop_index("idx_scan_results_run_id", table_name="scan_results")
    op.drop_table("scan_results")

    op.drop_index("idx_scan_runs_user_started", table_name="scan_runs")
    op.drop_index("idx_scan_runs_status", table_name="scan_runs")
    op.drop_index("idx_scan_runs_user_id", table_name="scan_runs")
    op.drop_table("scan_runs")

    op.drop_index("idx_scan_configs_user_id", table_name="scan_configs")
    op.drop_table("scan_configs")
