"""Interview prep — generated questions + red-flag prompts per job or custom role."""

from __future__ import annotations

import uuid
from datetime import datetime
from typing import Any

from sqlalchemy import CheckConstraint, DateTime, ForeignKey, Integer, String
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column
from sqlalchemy.sql import func

from hireloop.models.base import Base


class InterviewPrep(Base):
    __tablename__ = "interview_preps"
    __table_args__ = (
        CheckConstraint(
            "(job_id IS NOT NULL AND custom_role IS NULL) "
            "OR (job_id IS NULL AND custom_role IS NOT NULL)",
            name="ck_interview_preps_job_xor_custom_role",
        ),
    )

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    user_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    job_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("jobs.id", ondelete="SET NULL"),
        nullable=True,
    )
    custom_role: Mapped[str | None] = mapped_column(String(255), nullable=True)
    questions: Mapped[list[dict[str, Any]]] = mapped_column(JSONB, nullable=False)
    red_flag_questions: Mapped[list[dict[str, Any]] | None] = mapped_column(JSONB, nullable=True)
    model_used: Mapped[str] = mapped_column(String(64), nullable=False)
    tokens_used: Mapped[int | None] = mapped_column(Integer, nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        nullable=False,
    )
