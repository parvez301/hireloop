"""Per-output personalisation audit log (Layer 6)."""

from __future__ import annotations

import uuid
from datetime import datetime

from sqlalchemy import Boolean, DateTime, ForeignKey, Integer, String
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column
from sqlalchemy.sql import func

from hireloop.models.base import Base


class PersonalisationAudit(Base):
    __tablename__ = "personalisation_audits"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    user_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("users.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
    )
    task: Mapped[str] = mapped_column(String(64), nullable=False, index=True)
    passed: Mapped[bool] = mapped_column(Boolean, nullable=False)
    generic_phrases_found: Mapped[list[str]] = mapped_column(JSONB, nullable=False)
    mentions_company: Mapped[bool] = mapped_column(Boolean, nullable=False)
    specific_cv_facts_referenced: Mapped[int] = mapped_column(Integer, nullable=False)
    rewrite_attempted: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    rewrite_succeeded: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )
