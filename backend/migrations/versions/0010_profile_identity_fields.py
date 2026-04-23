"""profile_identity_fields

Revision ID: 0010_identity
Revises: 0009_work_arr
Create Date: 2026-04-23

Adds `full_name`, `headline`, `current_location` to `profiles` so the
Profile → Basics tab can collect the identity fields the prototype
shows. All three are nullable — existing rows stay valid.
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "0010_identity"
down_revision: str | None = "0009_work_arr"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.add_column(
        "profiles",
        sa.Column("full_name", sa.String(length=200), nullable=True),
    )
    op.add_column(
        "profiles",
        sa.Column("headline", sa.String(length=300), nullable=True),
    )
    op.add_column(
        "profiles",
        sa.Column("current_location", sa.String(length=200), nullable=True),
    )


def downgrade() -> None:
    op.drop_column("profiles", "current_location")
    op.drop_column("profiles", "headline")
    op.drop_column("profiles", "full_name")
