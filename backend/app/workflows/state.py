"""Shared state for the release generation LangGraph workflow."""

import operator
from typing import Annotated, Any, TypedDict

from app.ai.schemas import ChangeAnalysis, QAVerdict, ReleaseNotesDraft
from app.integrations.gitlab_client import (
    CommitData,
    IssueData,
    MergeRequestData,
    PreviousRelease,
    ReleaseRangeWindow,
)


class ReleaseWorkflowState(TypedDict, total=False):
    # Inputs
    release_id: int
    repository_id: int
    repository_name: str
    project_path: str
    release_title: str
    range_params: dict[str, Any]
    auto_publish: bool
    slack_channel: str | None
    release_url: str | None

    # Fetched data
    window: ReleaseRangeWindow
    range_summary: str
    commits: list[CommitData]
    issues: list[IssueData]
    merge_requests: list[MergeRequestData]
    previous_releases: list[PreviousRelease]

    # AI artifacts
    rag_context: str
    analysis: ChangeAnalysis
    notes: ReleaseNotesDraft
    qa_verdict: QAVerdict
    qa_attempts: int

    # Publication
    slack_message_url: str | None
    slack_published_channel: str | None

    # Telemetry: merged across nodes via dict union
    node_timings: Annotated[dict[str, float], operator.or_]
