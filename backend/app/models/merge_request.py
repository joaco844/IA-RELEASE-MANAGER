from datetime import datetime

from sqlalchemy import JSON, DateTime, ForeignKey, Integer, String, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base


class MergeRequest(Base):
    __tablename__ = "merge_requests"

    id: Mapped[int] = mapped_column(primary_key=True)
    release_id: Mapped[int] = mapped_column(
        ForeignKey("releases.id", ondelete="CASCADE"), index=True
    )
    gitlab_iid: Mapped[int] = mapped_column(Integer)
    title: Mapped[str] = mapped_column(String(500))
    description: Mapped[str | None] = mapped_column(Text, nullable=True)
    state: Mapped[str] = mapped_column(String(20), default="merged")
    labels: Mapped[list[str] | None] = mapped_column(JSON, nullable=True)
    author_name: Mapped[str | None] = mapped_column(String(255), nullable=True)
    merged_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    web_url: Mapped[str | None] = mapped_column(String(500), nullable=True)

    release: Mapped["Release"] = relationship(back_populates="merge_requests")  # noqa: F821
