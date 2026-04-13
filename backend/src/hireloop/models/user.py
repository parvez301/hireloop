from typing import TYPE_CHECKING

from sqlalchemy import String
from sqlalchemy.orm import Mapped, mapped_column, relationship

from hireloop.models.base import Base, TimestampMixin, UUIDPKMixin

if TYPE_CHECKING:
    from hireloop.models.profile import Profile
    from hireloop.models.star_story import StarStory
    from hireloop.models.subscription import Subscription


class User(Base, UUIDPKMixin, TimestampMixin):
    __tablename__ = "users"

    cognito_sub: Mapped[str] = mapped_column(String(255), unique=True, nullable=False, index=True)
    email: Mapped[str] = mapped_column(String(255), unique=True, nullable=False, index=True)
    name: Mapped[str] = mapped_column(String(255), nullable=False)

    profile: Mapped["Profile | None"] = relationship(
        "Profile", back_populates="user", uselist=False, cascade="all, delete-orphan"
    )
    subscription: Mapped["Subscription | None"] = relationship(
        "Subscription", back_populates="user", uselist=False, cascade="all, delete-orphan"
    )
    star_stories: Mapped[list["StarStory"]] = relationship(
        "StarStory", back_populates="user", cascade="all, delete-orphan"
    )
