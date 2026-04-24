"""crossref_maps

Revision ID: 0013_crossref
Revises: 0012_parsed_jd
Create Date: 2026-04-24

Layer-4 cross-reference map table (PERSONALISATION_STRATEGY.md). One row per
(user, job) capturing the LLM-built mapping between CV evidence and JD
requirements: strong_matches, gaps, unique_angles, fit_summary.

Built lazily by services.crossref.ensure_crossref_map() the first time a
downstream personalised generator needs it, then cached for reuse across
evaluation, CV rewrite, cover letter, interview prep, and negotiation calls.
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects.postgresql import JSONB

revision: str = "0013_crossref"
down_revision: str | None = "0012_parsed_jd"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "crossref_maps",
        sa.Column(
            "id",
            sa.dialects.postgresql.UUID(as_uuid=True),
            primary_key=True,
            server_default=sa.text("gen_random_uuid()"),
        ),
        sa.Column(
            "user_id",
            sa.dialects.postgresql.UUID(as_uuid=True),
            sa.ForeignKey("users.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column(
            "job_id",
            sa.dialects.postgresql.UUID(as_uuid=True),
            sa.ForeignKey("jobs.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("body", JSONB(), nullable=False),
        sa.Column("model_used", sa.String(length=64), nullable=False),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.func.now(),
            nullable=False,
        ),
        sa.UniqueConstraint("user_id", "job_id", name="uq_crossref_maps_user_job"),
    )
    op.create_index("ix_crossref_maps_user_id", "crossref_maps", ["user_id"], unique=False)
    op.create_index("ix_crossref_maps_job_id", "crossref_maps", ["job_id"], unique=False)


def downgrade() -> None:
    op.drop_index("ix_crossref_maps_job_id", table_name="crossref_maps")
    op.drop_index("ix_crossref_maps_user_id", table_name="crossref_maps")
    op.drop_table("crossref_maps")
