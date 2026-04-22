"""custom_auth

Revision ID: 0008_custom_auth
Revises: 0007_onb_collapse
Create Date: 2026-04-22

Adds the columns + tables needed for the in-house auth flow that replaces
Cognito Hosted UI. Cognito-backed users coexist while AUTH_MODE='cognito';
cutover happens per-env by flipping the feature flag to 'custom'.

- users.password_hash      — argon2id encoded hash; NULL for legacy Cognito
                             accounts until they reset.
- users.email_verified_at  — NULL until the 6-digit code is consumed.

New tables:
- email_verification_codes — one live row per email; code is stored hashed.
- password_reset_tokens    — opaque 32-byte token, single-use.
- auth_refresh_tokens      — rotating refresh tokens for session continuity.
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision: str = "0008_custom_auth"
down_revision: str | None = "0007_onb_collapse"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.add_column(
        "users",
        sa.Column("password_hash", sa.String(length=255), nullable=True),
    )
    op.add_column(
        "users",
        sa.Column(
            "email_verified_at",
            sa.DateTime(timezone=True),
            nullable=True,
        ),
    )

    op.create_table(
        "email_verification_codes",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column(
            "user_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("users.id", ondelete="CASCADE"),
            nullable=False,
            index=True,
        ),
        sa.Column("code_hash", sa.String(length=128), nullable=False),
        sa.Column("expires_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column(
            "attempts",
            sa.Integer(),
            nullable=False,
            server_default=sa.text("0"),
        ),
        sa.Column("consumed_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.text("now()"),
        ),
    )

    op.create_table(
        "password_reset_tokens",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column(
            "user_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("users.id", ondelete="CASCADE"),
            nullable=False,
            index=True,
        ),
        sa.Column(
            "token_hash", sa.String(length=128), nullable=False, unique=True,
        ),
        sa.Column("expires_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("consumed_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.text("now()"),
        ),
    )

    op.create_table(
        "auth_refresh_tokens",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column(
            "user_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("users.id", ondelete="CASCADE"),
            nullable=False,
            index=True,
        ),
        sa.Column(
            "token_hash", sa.String(length=128), nullable=False, unique=True,
        ),
        sa.Column("expires_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("revoked_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("user_agent", sa.String(length=512), nullable=True),
        sa.Column("ip", sa.String(length=64), nullable=True),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.text("now()"),
        ),
    )


def downgrade() -> None:
    op.drop_table("auth_refresh_tokens")
    op.drop_table("password_reset_tokens")
    op.drop_table("email_verification_codes")
    op.drop_column("users", "email_verified_at")
    op.drop_column("users", "password_hash")
