"""phase2b1_subscription_columns

Revision ID: 0004_phase2b1
Revises: 0003_phase2b
Create Date: 2026-04-10

Adds past_due_since (3-day grace tracker), cancel_at_period_end
(mirror of Stripe flag for UI), and plan_monthly_cost_cap_cents
(forward-compat hook for per-user quota enforcement) to subscriptions.
"""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

revision: str = "0004_phase2b1"
down_revision: Union[str, None] = "0003_phase2b"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column(
        "subscriptions",
        sa.Column("past_due_since", sa.DateTime(timezone=True), nullable=True),
    )
    op.add_column(
        "subscriptions",
        sa.Column(
            "cancel_at_period_end",
            sa.Boolean(),
            nullable=False,
            server_default=sa.text("false"),
        ),
    )
    op.add_column(
        "subscriptions",
        sa.Column("plan_monthly_cost_cap_cents", sa.Integer(), nullable=True),
    )


def downgrade() -> None:
    op.drop_column("subscriptions", "plan_monthly_cost_cap_cents")
    op.drop_column("subscriptions", "cancel_at_period_end")
    op.drop_column("subscriptions", "past_due_since")
