from datetime import UTC, datetime

from sqlalchemy import DateTime, ForeignKey, String, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base


class SlackWorkspace(Base):
    __tablename__ = "slack_workspaces"

    id: Mapped[int] = mapped_column(primary_key=True)
    owner_id: Mapped[int] = mapped_column(
        ForeignKey("users.id", ondelete="CASCADE"), unique=True, index=True
    )
    team_id: Mapped[str | None] = mapped_column(String(50), nullable=True)
    team_name: Mapped[str | None] = mapped_column(String(255), nullable=True)
    # Slack bot token, Fernet-encrypted at rest.
    encrypted_bot_token: Mapped[str] = mapped_column(Text)
    default_channel: Mapped[str] = mapped_column(String(255), default="#releases")
    connected_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=lambda: datetime.now(UTC)
    )

    owner: Mapped["User"] = relationship(back_populates="slack_workspace")  # noqa: F821
