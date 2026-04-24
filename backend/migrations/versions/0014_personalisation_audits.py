"""personalisation_audits

Revision ID: 0014_audits
Revises: 0013_crossref
Create Date: 2026-04-24

Layer-6 audit log (PERSONALISATION_STRATEGY.md). Every personalised generator
call writes a row capturing the validator's verdict on its output: banned
phrases found, whether the company was named, how many CV facts were quoted,
whether an auto-rewrite was triggered and whether it improved things.

Used to identify which prompts misbehave most often so Phase 5b prompt
refinement can target them specifically. `user_id` is nullable so background /
system tasks (batch eval, scheduled rewrites) can audit without attribution.
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects.postgresql import JSONB

revision: str = "0014_audits"
down_revision: str | None = "0013_crossref"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "personalisation_audits",
        sa.Column(
            "id",
            sa.dialects.postgresql.UUID(as_uuid=True),
            primary_key=True,
            server_default=sa.text("gen_random_uuid()"),
        ),
        sa.Column(
            "user_id",
            sa.dialects.postgresql.UUID(as_uuid=True),
            sa.ForeignKey("users.id", ondelete="SET NULL"),
            nullable=True,
        ),
        sa.Column("task", sa.String(length=64), nullable=False),
        sa.Column("passed", sa.Boolean(), nullable=False),
        sa.Column("generic_phrases_found", JSONB(), nullable=False),
        sa.Column("mentions_company", sa.Boolean(), nullable=False),
        sa.Column("specific_cv_facts_referenced", sa.Integer(), nullable=False),
        sa.Column("rewrite_attempted", sa.Boolean(), nullable=False, server_default=sa.false()),
        sa.Column("rewrite_succeeded", sa.Boolean(), nullable=False, server_default=sa.false()),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.func.now(),
            nullable=False,
        ),
    )
    op.create_index(
        "ix_personalisation_audits_user_id",
        "personalisation_audits",
        ["user_id"],
        unique=False,
    )
    op.create_index(
        "ix_personalisation_audits_task",
        "personalisation_audits",
        ["task"],
        unique=False,
    )


def downgrade() -> None:
    op.drop_index("ix_personalisation_audits_task", table_name="personalisation_audits")
    op.drop_index("ix_personalisation_audits_user_id", table_name="personalisation_audits")
    op.drop_table("personalisation_audits")
