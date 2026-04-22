"""onboarding_collapse_preferences

Revision ID: 0007_onb_collapse
Revises: 0006_phase2d
Create Date: 2026-04-22

Flips any `profiles.onboarding_state='preferences'` rows whose profile already
has a parsed resume (master_resume_md IS NOT NULL) to 'done'. The 'preferences'
string stays a legal value in the column (no enum change, no downgrade pain)
but the application no longer writes it.

Profiles that had 'preferences' state but no resume remain as-is — they're
inconsistent data from before the state machine was fully enforced and will
self-heal on next resume upload.
"""

from collections.abc import Sequence

from alembic import op

revision: str = "0007_onb_collapse"
down_revision: str | None = "0006_phase2d"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.execute(
        """
        UPDATE profiles
        SET onboarding_state = 'done'
        WHERE onboarding_state = 'preferences'
          AND master_resume_md IS NOT NULL
        """
    )


def downgrade() -> None:
    # No-op. We cannot know which of the now-'done' rows were formerly
    # 'preferences' without an audit column, and re-demoting everyone to
    # 'preferences' would trigger the onboarding gate for users who finished.
    pass
