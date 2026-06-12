from datetime import datetime
from typing import Any, Literal

from pydantic import BaseModel, ConfigDict, Field, model_validator


class ReleaseRange(BaseModel):
    type: Literal["tag_range", "last_days", "since_date"]
    from_tag: str | None = None
    to_tag: str | None = None
    days: int | None = Field(default=None, ge=1, le=365)
    since: datetime | None = None

    @model_validator(mode="after")
    def validate_range(self) -> "ReleaseRange":
        if self.type == "tag_range" and not (self.from_tag and self.to_tag):
            raise ValueError("tag_range requires from_tag and to_tag")
        if self.type == "last_days" and not self.days:
            raise ValueError("last_days requires days")
        if self.type == "since_date" and not self.since:
            raise ValueError("since_date requires since")
        return self


class AIConfig(BaseModel):
    provider: Literal["openai", "gemini"] | None = None
    temperature: float | None = Field(default=None, ge=0.0, le=1.0)


class ReleaseGenerateRequest(BaseModel):
    repository_id: int
    title: str | None = Field(default=None, max_length=255)
    range: ReleaseRange
    ai: AIConfig | None = None
    auto_publish: bool = False
    slack_channel: str | None = None


class ReleaseOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    repository_id: int
    repository_name: str = ""
    title: str
    status: str
    range_summary: str
    risk_level: str | None
    created_at: datetime
    completed_at: datetime | None
    slack_message_url: str | None
    error_message: str | None


class ReleaseNotesOut(BaseModel):
    executive: str | None
    technical: str | None
    markdown: str | None
    slack: str | None


class CommitOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    sha: str
    title: str
    author_name: str | None
    created_at: datetime | None = Field(default=None, validation_alias="authored_at")


class IssueOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    iid: int = Field(validation_alias="gitlab_iid")
    title: str
    state: str
    labels: list[str] = []
    web_url: str | None


class MergeRequestOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    iid: int = Field(validation_alias="gitlab_iid")
    title: str
    state: str
    author_name: str | None
    web_url: str | None


class ReleaseMetricsOut(BaseModel):
    generation_seconds: float | None
    commits_analyzed: int
    issues_analyzed: int
    mrs_analyzed: int


class ReleaseDetailOut(ReleaseOut):
    notes: ReleaseNotesOut
    qa_report: dict[str, Any] | None
    analysis: dict[str, Any] | None
    themes: list[str] | None
    commits: list[CommitOut]
    issues: list[IssueOut]
    merge_requests: list[MergeRequestOut]
    metrics: ReleaseMetricsOut


class ReleaseListOut(BaseModel):
    items: list[ReleaseOut]
    total: int
    page: int
    page_size: int
