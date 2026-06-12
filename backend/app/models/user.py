from datetime import UTC, datetime

from sqlalchemy import Boolean, DateTime, String
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base


class User(Base):
    __tablename__ = "users"

    id: Mapped[int] = mapped_column(primary_key=True)
    email: Mapped[str] = mapped_column(String(255), unique=True, index=True)
    hashed_password: Mapped[str] = mapped_column(String(255))
    full_name: Mapped[str] = mapped_column(String(255), default="")
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=lambda: datetime.now(UTC)
    )

    repositories: Mapped[list["Repository"]] = relationship(  # noqa: F821
        back_populates="owner", cascade="all, delete-orphan"
    )
    slack_workspace: Mapped["SlackWorkspace | None"] = relationship(  # noqa: F821
        back_populates="owner", uselist=False, cascade="all, delete-orphan"
    )
