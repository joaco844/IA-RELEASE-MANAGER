from datetime import UTC, datetime

from sqlalchemy import DateTime, ForeignKey, String, Text, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base


class Repository(Base):
    __tablename__ = "repositories"
    __table_args__ = (UniqueConstraint("owner_id", "gitlab_url", "project_path"),)

    id: Mapped[int] = mapped_column(primary_key=True)
    owner_id: Mapped[int] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"), index=True)
    name: Mapped[str] = mapped_column(String(255))
    gitlab_url: Mapped[str] = mapped_column(String(500))
    project_path: Mapped[str] = mapped_column(String(500))
    gitlab_project_id: Mapped[int | None] = mapped_column(nullable=True)
    default_branch: Mapped[str | None] = mapped_column(String(255), nullable=True)
    description: Mapped[str | None] = mapped_column(Text, nullable=True)
    # GitLab personal access token, Fernet-encrypted at rest.
    encrypted_token: Mapped[str] = mapped_column(Text)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=lambda: datetime.now(UTC)
    )

    owner: Mapped["User"] = relationship(back_populates="repositories")  # noqa: F821
    releases: Mapped[list["Release"]] = relationship(  # noqa: F821
        back_populates="repository", cascade="all, delete-orphan", order_by="Release.id.desc()"
    )
