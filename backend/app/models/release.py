import enum
from datetime import UTC, datetime
from typing import Any

from sqlalchemy import JSON, DateTime, Float, ForeignKey, Integer, String, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base


class ReleaseStatus(str, enum.Enum):
    PENDING = "pending"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"
    PUBLISHED = "published"


class RiskLevel(str, enum.Enum):
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"


class Release(Base):
    __tablename__ = "releases"

    id: Mapped[int] = mapped_column(primary_key=True)
    repository_id: Mapped[int] = mapped_column(
        ForeignKey("repositories.id", ondelete="CASCADE"), index=True
    )
    title: Mapped[str] = mapped_column(String(255))
    status: Mapped[str] = mapped_column(String(20), default=ReleaseStatus.PENDING.value, index=True)

    # Release range
    range_type: Mapped[str] = mapped_column(String(20))  # tag_range | last_days | since_date
    range_from: Mapped[str | None] = mapped_column(String(255), nullable=True)
    range_to: Mapped[str | None] = mapped_column(String(255), nullable=True)
    range_summary: Mapped[str] = mapped_column(String(255), default="")

    # Generated content (one column per output format)
    executive_notes: Mapped[str | None] = mapped_column(Text, nullable=True)
    technical_notes: Mapped[str | None] = mapped_column(Text, nullable=True)
    markdown_notes: Mapped[str | None] = mapped_column(Text, nullable=True)
    slack_notes: Mapped[str | None] = mapped_column(Text, nullable=True)

    # AI artifacts
    analysis: Mapped[dict[str, Any] | None] = mapped_column(JSON, nullable=True)
    qa_report: Mapped[dict[str, Any] | None] = mapped_column(JSON, nullable=True)
    themes: Mapped[list[str] | None] = mapped_column(JSON, nullable=True)
    risk_level: Mapped[str | None] = mapped_column(String(10), nullable=True)
    provider: Mapped[str | None] = mapped_column(String(20), nullable=True)
    model_name: Mapped[str | None] = mapped_column(String(100), nullable=True)

    # Slack publication
    slack_channel: Mapped[str | None] = mapped_column(String(255), nullable=True)
    slack_message_url: Mapped[str | None] = mapped_column(String(500), nullable=True)
    slack_published_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )

    # Lifecycle & metrics
    error_message: Mapped[str | None] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=lambda: datetime.now(UTC)
    )
    started_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    completed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    generation_seconds: Mapped[float | None] = mapped_column(Float, nullable=True)
    commits_analyzed: Mapped[int] = mapped_column(Integer, default=0)
    issues_analyzed: Mapped[int] = mapped_column(Integer, default=0)
    mrs_analyzed: Mapped[int] = mapped_column(Integer, default=0)

    repository: Mapped["Repository"] = relationship(back_populates="releases")  # noqa: F821

    @property
    def repository_name(self) -> str:
        return self.repository.name if self.repository else ""
    commits: Mapped[list["Commit"]] = relationship(  # noqa: F821
        back_populates="release", cascade="all, delete-orphan"
    )
    issues: Mapped[list["Issue"]] = relationship(  # noqa: F821
        back_populates="release", cascade="all, delete-orphan"
    )
    merge_requests: Mapped[list["MergeRequest"]] = relationship(  # noqa: F821
        back_populates="release", cascade="all, delete-orphan"
    )
    generation_logs: Mapped[list["GenerationLog"]] = relationship(  # noqa: F821
        back_populates="release", cascade="all, delete-orphan"
    )
