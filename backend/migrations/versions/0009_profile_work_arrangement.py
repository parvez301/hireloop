"""profile_work_arrangement

Revision ID: 0009_work_arr
Revises: 0008_custom_auth
Create Date: 2026-04-23

Adds `profiles.work_arrangement` nullable string — captured in the new
onboarding Confirm step, editable on the Profile → Targets tab.
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "0009_work_arr"
down_revision: str | None = "0008_custom_auth"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.add_column(
        "profiles",
        sa.Column("work_arrangement", sa.String(length=32), nullable=True),
    )


def downgrade() -> None:
    op.drop_column("profiles", "work_arrangement")
