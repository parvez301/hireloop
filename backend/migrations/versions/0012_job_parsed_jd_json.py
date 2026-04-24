"""job_parsed_jd_json

Revision ID: 0012_parsed_jd
Revises: 0011_personalisation
Create Date: 2026-04-24

Adds `parsed_jd_json` to `jobs` for Layer-3 structured JD extraction
(PERSONALISATION_STRATEGY.md). Populated lazily by services.jd_extractor
the first time downstream personalised generators (eval, cover letter,
crossref map) need structured JD facts.

The existing `requirements_json` column stays — it carries lightweight
adapter-extracted hints from the scanner (e.g. detected skills from a
Greenhouse/Lever payload). `parsed_jd_json` is the richer LLM-produced
structure: must_have_skills, nice_to_have_skills, red_flag_requirements,
company_stage, key_responsibilities, application_questions, etc.
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects.postgresql import JSONB

revision: str = "0012_parsed_jd"
down_revision: str | None = "0011_personalisation"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.add_column("jobs", sa.Column("parsed_jd_json", JSONB(), nullable=True))


def downgrade() -> None:
    op.drop_column("jobs", "parsed_jd_json")
