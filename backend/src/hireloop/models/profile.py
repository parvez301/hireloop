from typing import TYPE_CHECKING, Any
from uuid import UUID

from sqlalchemy import ForeignKey, Integer, String, Text
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.dialects.postgresql import UUID as PG_UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from hireloop.models.base import Base, TimestampMixin, UUIDPKMixin

if TYPE_CHECKING:
    from hireloop.models.user import User


class Profile(Base, UUIDPKMixin, TimestampMixin):
    __tablename__ = "profiles"

    user_id: Mapped[UUID] = mapped_column(
        PG_UUID(as_uuid=True),
        ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False,
        unique=True,
        index=True,
    )
    master_resume_md: Mapped[str | None] = mapped_column(Text)
    master_resume_s3: Mapped[str | None] = mapped_column(String(500))
    parsed_resume_json: Mapped[dict[str, Any] | None] = mapped_column(JSONB)
    target_roles: Mapped[list[str] | None] = mapped_column(JSONB)
    target_locations: Mapped[list[str] | None] = mapped_column(JSONB)
    min_salary: Mapped[int | None] = mapped_column(Integer)
    preferred_industries: Mapped[list[str] | None] = mapped_column(JSONB)
    linkedin_url: Mapped[str | None] = mapped_column(String(500))
    github_url: Mapped[str | None] = mapped_column(String(500))
    portfolio_url: Mapped[str | None] = mapped_column(String(500))
    onboarding_state: Mapped[str] = mapped_column(
        String(50), nullable=False, default="resume_upload"
    )

    user: Mapped["User"] = relationship("User", back_populates="profile")
