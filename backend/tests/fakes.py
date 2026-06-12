"""Shared fakes for external services and agents."""

from datetime import UTC, datetime

from app.ai.agents.publisher import SlackPublication
from app.ai.schemas import (
    AnalyzedChange,
    ChangeAnalysis,
    ChangeCategory,
    QAVerdict,
    ReleaseNotesDraft,
    RiskLevel,
)
from app.integrations.gitlab_client import (
    CommitData,
    IssueData,
    MergeRequestData,
    ProjectInfo,
    ReleaseRangeWindow,
)
from app.integrations.slack_client import SlackTeamInfo


def sample_commits() -> list[CommitData]:
    return [
        CommitData(
            sha="abc1234567",
            title="feat: add payment retries",
            message="feat: add payment retries\n\nRetries failed charges",
            author_name="Ana",
            author_email="ana@example.com",
            authored_at=datetime(2026, 6, 1, tzinfo=UTC),
            web_url="https://gitlab.example.com/-/commit/abc1234567",
        ),
        CommitData(
            sha="def7654321",
            title="fix: handle null invoice",
            message="fix: handle null invoice",
            author_name="Luis",
            author_email="luis@example.com",
            authored_at=datetime(2026, 6, 2, tzinfo=UTC),
            web_url="https://gitlab.example.com/-/commit/def7654321",
        ),
    ]


def sample_issues() -> list[IssueData]:
    return [
        IssueData(
            iid=10,
            title="Invoice crashes on null amount",
            description="Steps to reproduce...",
            state="closed",
            labels=["bug"],
            author_name="Luis",
            closed_at=datetime(2026, 6, 2, tzinfo=UTC),
            web_url="https://gitlab.example.com/-/issues/10",
        )
    ]


def sample_mrs() -> list[MergeRequestData]:
    return [
        MergeRequestData(
            iid=42,
            title="Add payment retries",
            description="Implements retry with backoff",
            state="merged",
            labels=["feature"],
            author_name="Ana",
            merged_at=datetime(2026, 6, 1, tzinfo=UTC),
            web_url="https://gitlab.example.com/-/merge_requests/42",
        )
    ]


class FakeGitLabClient:
    """Stands in for GitLabClient in services and workflow tests."""

    def __init__(self, gitlab_url: str = "", token: str = "") -> None:
        self.gitlab_url = gitlab_url
        self.token = token

    def verify_project(self, project_path: str) -> ProjectInfo:
        return ProjectInfo(
            id=123,
            name="Demo Project",
            path_with_namespace=project_path,
            default_branch="main",
            description="A demo project",
            web_url=f"https://gitlab.example.com/{project_path}",
        )

    def resolve_range(self, project_path: str, range_params: dict) -> ReleaseRangeWindow:
        return ReleaseRangeWindow(
            summary="v1.0.0 → v1.1.0",
            since=datetime(2026, 5, 1, tzinfo=UTC),
            until=datetime(2026, 6, 1, tzinfo=UTC),
            from_ref="v1.0.0",
            to_ref="v1.1.0",
        )

    def fetch_commits(self, project_path: str, window: ReleaseRangeWindow):
        return sample_commits()

    def fetch_issues(self, project_path: str, window: ReleaseRangeWindow):
        return sample_issues()

    def fetch_merge_requests(self, project_path: str, window: ReleaseRangeWindow):
        return sample_mrs()

    def fetch_previous_releases(self, project_path: str, limit: int = 10):
        return []


def sample_analysis() -> ChangeAnalysis:
    return ChangeAnalysis(
        changes=[
            AnalyzedChange(
                category=ChangeCategory.FEATURES,
                summary="Payment retries with exponential backoff",
                business_impact="Fewer lost sales from transient failures",
                technical_impact="New retry queue in the payment service",
                risk_level=RiskLevel.MEDIUM,
                source_refs=["commit:abc1234", "mr:!42"],
            ),
            AnalyzedChange(
                category=ChangeCategory.BUG_FIXES,
                summary="Fixed crash on invoices with null amount",
                business_impact="Invoice page no longer breaks for some customers",
                technical_impact="Null guard in invoice serializer",
                risk_level=RiskLevel.LOW,
                source_refs=["commit:def7654", "issue:#10"],
            ),
        ],
        themes=["payments reliability"],
        overall_risk=RiskLevel.MEDIUM,
    )


def sample_notes() -> ReleaseNotesDraft:
    return ReleaseNotesDraft(
        executive="## Highlights\nPayments are more reliable.",
        technical="## Bug Fixes\n- Null invoice crash (#10)",
        markdown="# Release v1.1.0\n\n## Features\n- Payment retries (!42)",
        slack=":rocket: *Features*\n• Payment retries",
    )


class FakeAnalystAgent:
    def run(self, commits, merge_requests, issues, rag_context=""):
        return sample_analysis()


class FakeWriterAgent:
    def __init__(self) -> None:
        self.calls: list[str | None] = []

    def run(self, analysis, repository_name, release_title, range_summary,
            rag_context="", reviewer_feedback=None):
        self.calls.append(reviewer_feedback)
        return sample_notes()


class FakeQAAgent:
    """Rejects the first draft, approves the second (exercises the revision loop)."""

    def __init__(self, reject_first: bool = True) -> None:
        self.reject_first = reject_first
        self.calls = 0

    def run(self, notes, source_digest):
        self.calls += 1
        if self.reject_first and self.calls == 1:
            return QAVerdict(
                approved=False,
                traceability_score=0.7,
                issues_found=["Claim about uptime is not traceable"],
                feedback="Remove the uptime claim",
            )
        return QAVerdict(approved=True, traceability_score=0.98, issues_found=[], feedback="")


class FakeSlackClient:
    def __init__(self, bot_token: str = "") -> None:
        self.bot_token = bot_token

    def verify_token(self) -> SlackTeamInfo:
        return SlackTeamInfo(team_id="T123", team_name="Acme Corp")


class FakePublisherAgent:
    def __init__(self, client=None) -> None:
        self.published: list[dict] = []

    def publish(self, **kwargs) -> SlackPublication:
        self.published.append(kwargs)
        return SlackPublication(
            channel="#releases",
            message_url="https://acme.slack.com/archives/C1/p123",
            ts="123.456",
        )
