"""ScanConfig — per-user saved scan configuration."""

from __future__ import annotations

import uuid
from datetime import datetime
from typing import Any

from sqlalchemy import Boolean, DateTime, ForeignKey, String
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column
from sqlalchemy.sql import func

from hireloop.models.base import Base


class ScanConfig(Base):
    __tablename__ = "scan_configs"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    user_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False,
    )
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    companies: Mapped[list[dict[str, Any]]] = mapped_column(JSONB, nullable=False)
    keywords: Mapped[list[str] | None] = mapped_column(JSONB, nullable=True)
    exclude_keywords: Mapped[list[str] | None] = mapped_column(JSONB, nullable=True)
    schedule: Mapped[str] = mapped_column(
        String(32), nullable=False, default="manual", server_default="manual"
    )
    is_active: Mapped[bool] = mapped_column(
        Boolean, nullable=False, default=True, server_default="true"
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )
