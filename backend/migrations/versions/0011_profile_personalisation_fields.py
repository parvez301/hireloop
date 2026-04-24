"""profile_personalisation_fields

Revision ID: 0011_personalisation
Revises: 0010_identity
Create Date: 2026-04-24

Adds the Layer-1 (rich profile) fields from PERSONALISATION_STRATEGY.md to
`profiles`. These power task-prompt personalisation: every downstream Sonnet
generator (CV rewrite, cover letter, STAR, negotiation) receives this profile
to ground its output in candidate-specific facts.

Skipped intentionally:
- `open_to_relocation` — overlaps with existing `work_arrangement`
- History fields (avg_eval_score, applied_count, interview_count, last_active)
  — these are derived; computed via queries against evaluations + applications
  rather than denormalised onto profiles

Array-typed fields use JSONB (matches existing target_roles convention) rather
than ARRAY(String) (which is Postgres-specific and harder to test on SQLite).
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects.postgresql import JSONB

revision: str = "0011_personalisation"
down_revision: str | None = "0010_identity"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.add_column("profiles", sa.Column("years_experience", sa.Integer(), nullable=True))
    op.add_column("profiles", sa.Column("seniority_level", sa.String(length=32), nullable=True))
    op.add_column("profiles", sa.Column("industry", sa.String(length=120), nullable=True))
    op.add_column("profiles", sa.Column("specialisation", sa.String(length=255), nullable=True))
    op.add_column("profiles", sa.Column("salary_current", sa.String(length=120), nullable=True))
    op.add_column("profiles", sa.Column("salary_target", sa.String(length=120), nullable=True))
    op.add_column("profiles", sa.Column("notice_period", sa.String(length=64), nullable=True))
    op.add_column("profiles", sa.Column("deal_breakers", JSONB(), nullable=True))
    op.add_column("profiles", sa.Column("non_negotiables", JSONB(), nullable=True))
    op.add_column("profiles", sa.Column("top_strengths", JSONB(), nullable=True))
    op.add_column("profiles", sa.Column("known_gaps", JSONB(), nullable=True))
    op.add_column("profiles", sa.Column("certifications", JSONB(), nullable=True))
    op.add_column("profiles", sa.Column("languages", JSONB(), nullable=True))
    op.add_column("profiles", sa.Column("cv_tone", sa.String(length=32), nullable=True))
    op.add_column("profiles", sa.Column("preferred_length", sa.String(length=32), nullable=True))


def downgrade() -> None:
    op.drop_column("profiles", "preferred_length")
    op.drop_column("profiles", "cv_tone")
    op.drop_column("profiles", "languages")
    op.drop_column("profiles", "certifications")
    op.drop_column("profiles", "known_gaps")
    op.drop_column("profiles", "top_strengths")
    op.drop_column("profiles", "non_negotiables")
    op.drop_column("profiles", "deal_breakers")
    op.drop_column("profiles", "notice_period")
    op.drop_column("profiles", "salary_target")
    op.drop_column("profiles", "salary_current")
    op.drop_column("profiles", "specialisation")
    op.drop_column("profiles", "industry")
    op.drop_column("profiles", "seniority_level")
    op.drop_column("profiles", "years_experience")
