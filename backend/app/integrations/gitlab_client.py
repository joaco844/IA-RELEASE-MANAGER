"""GitLab integration: fetches commits, merge requests, issues, tags and releases.

Wraps python-gitlab behind a small typed interface so the rest of the app
(and the tests) never deal with the raw SDK objects.
"""

from dataclasses import dataclass, field
from datetime import UTC, datetime, timedelta
from typing import Any

from app.core.exceptions import ExternalServiceError
from app.core.logging import get_logger

logger = get_logger(__name__)

_MAX_ITEMS = 500  # safety cap per resource type


@dataclass
class ProjectInfo:
    id: int
    name: str
    path_with_namespace: str
    default_branch: str | None
    description: str | None
    web_url: str


@dataclass
class CommitData:
    sha: str
    title: str
    message: str
    author_name: str | None
    author_email: str | None
    authored_at: datetime | None
    web_url: str | None


@dataclass
class IssueData:
    iid: int
    title: str
    description: str | None
    state: str
    labels: list[str]
    author_name: str | None
    closed_at: datetime | None
    web_url: str | None


@dataclass
class MergeRequestData:
    iid: int
    title: str
    description: str | None
    state: str
    labels: list[str]
    author_name: str | None
    merged_at: datetime | None
    web_url: str | None


@dataclass
class ReleaseRangeWindow:
    """Resolved release range: refs for commit comparison plus a time window
    used to scope merge requests and issues."""

    summary: str
    since: datetime | None = None
    until: datetime | None = None
    from_ref: str | None = None
    to_ref: str | None = None


@dataclass
class PreviousRelease:
    tag_name: str
    name: str | None
    description: str | None
    released_at: datetime | None = None
    extra: dict[str, Any] = field(default_factory=dict)


def _parse_dt(value: str | None) -> datetime | None:
    if not value:
        return None
    try:
        parsed = datetime.fromisoformat(value.replace("Z", "+00:00"))
        return parsed if parsed.tzinfo else parsed.replace(tzinfo=UTC)
    except ValueError:
        return None


class GitLabClient:
    def __init__(self, gitlab_url: str, token: str) -> None:
        import gitlab  # lazy: keeps unit tests free of the dependency

        self._exceptions = gitlab.exceptions
        self._gl = gitlab.Gitlab(url=gitlab_url, private_token=token, timeout=30)

    def _project(self, project_path: str) -> Any:
        try:
            return self._gl.projects.get(project_path)
        except self._exceptions.GitlabError as exc:
            raise ExternalServiceError(
                f"Could not access GitLab project '{project_path}': {exc}"
            ) from exc

    def verify_project(self, project_path: str) -> ProjectInfo:
        project = self._project(project_path)
        return ProjectInfo(
            id=project.id,
            name=project.name,
            path_with_namespace=project.path_with_namespace,
            default_branch=getattr(project, "default_branch", None),
            description=getattr(project, "description", None),
            web_url=project.web_url,
        )

    def resolve_range(self, project_path: str, range_params: dict[str, Any]) -> ReleaseRangeWindow:
        """Translate a user-selected range into refs + a time window."""
        range_type = range_params["type"]
        try:
            if range_type == "tag_range":
                project = self._project(project_path)
                from_tag = project.tags.get(range_params["from_tag"])
                to_tag = project.tags.get(range_params["to_tag"])
                return ReleaseRangeWindow(
                    summary=f"{range_params['from_tag']} → {range_params['to_tag']}",
                    since=_parse_dt(from_tag.commit.get("created_at")),
                    until=_parse_dt(to_tag.commit.get("created_at")),
                    from_ref=range_params["from_tag"],
                    to_ref=range_params["to_tag"],
                )
            if range_type == "last_days":
                days = int(range_params["days"])
                return ReleaseRangeWindow(
                    summary=f"Last {days} days",
                    since=datetime.now(UTC) - timedelta(days=days),
                    until=datetime.now(UTC),
                )
            # since_date
            since = range_params["since"]
            if isinstance(since, str):
                since = _parse_dt(since)
            return ReleaseRangeWindow(
                summary=f"Since {since.date().isoformat()}",
                since=since,
                until=datetime.now(UTC),
            )
        except self._exceptions.GitlabError as exc:
            raise ExternalServiceError(f"Could not resolve release range: {exc}") from exc

    def fetch_commits(self, project_path: str, window: ReleaseRangeWindow) -> list[CommitData]:
        project = self._project(project_path)
        try:
            if window.from_ref and window.to_ref:
                comparison = project.repository_compare(window.from_ref, window.to_ref)
                raw_commits = comparison.get("commits", [])[:_MAX_ITEMS]
                return [
                    CommitData(
                        sha=c["id"],
                        title=c.get("title", ""),
                        message=c.get("message", ""),
                        author_name=c.get("author_name"),
                        author_email=c.get("author_email"),
                        authored_at=_parse_dt(c.get("created_at")),
                        web_url=f"{project.web_url}/-/commit/{c['id']}",
                    )
                    for c in raw_commits
                ]
            commits = project.commits.list(
                since=window.since.isoformat() if window.since else None,
                until=window.until.isoformat() if window.until else None,
                get_all=False,
                per_page=100,
                iterator=True,
            )
            result: list[CommitData] = []
            for c in commits:
                result.append(
                    CommitData(
                        sha=c.id,
                        title=c.title or "",
                        message=getattr(c, "message", "") or "",
                        author_name=getattr(c, "author_name", None),
                        author_email=getattr(c, "author_email", None),
                        authored_at=_parse_dt(getattr(c, "created_at", None)),
                        web_url=getattr(c, "web_url", None),
                    )
                )
                if len(result) >= _MAX_ITEMS:
                    break
            return result
        except self._exceptions.GitlabError as exc:
            raise ExternalServiceError(f"Could not fetch commits: {exc}") from exc

    def fetch_merge_requests(
        self, project_path: str, window: ReleaseRangeWindow
    ) -> list[MergeRequestData]:
        project = self._project(project_path)
        try:
            mrs = project.mergerequests.list(
                state="merged",
                updated_after=window.since.isoformat() if window.since else None,
                order_by="updated_at",
                per_page=100,
                iterator=True,
            )
            result: list[MergeRequestData] = []
            for mr in mrs:
                merged_at = _parse_dt(getattr(mr, "merged_at", None))
                if window.since and merged_at and merged_at < window.since:
                    continue
                if window.until and merged_at and merged_at > window.until:
                    continue
                result.append(
                    MergeRequestData(
                        iid=mr.iid,
                        title=mr.title or "",
                        description=getattr(mr, "description", None),
                        state=mr.state,
                        labels=list(getattr(mr, "labels", []) or []),
                        author_name=(getattr(mr, "author", None) or {}).get("name"),
                        merged_at=merged_at,
                        web_url=getattr(mr, "web_url", None),
                    )
                )
                if len(result) >= _MAX_ITEMS:
                    break
            return result
        except self._exceptions.GitlabError as exc:
            raise ExternalServiceError(f"Could not fetch merge requests: {exc}") from exc

    def fetch_issues(self, project_path: str, window: ReleaseRangeWindow) -> list[IssueData]:
        project = self._project(project_path)
        try:
            issues = project.issues.list(
                state="closed",
                updated_after=window.since.isoformat() if window.since else None,
                order_by="updated_at",
                per_page=100,
                iterator=True,
            )
            result: list[IssueData] = []
            for issue in issues:
                closed_at = _parse_dt(getattr(issue, "closed_at", None))
                if window.since and closed_at and closed_at < window.since:
                    continue
                if window.until and closed_at and closed_at > window.until:
                    continue
                result.append(
                    IssueData(
                        iid=issue.iid,
                        title=issue.title or "",
                        description=getattr(issue, "description", None),
                        state=issue.state,
                        labels=list(getattr(issue, "labels", []) or []),
                        author_name=(getattr(issue, "author", None) or {}).get("name"),
                        closed_at=closed_at,
                        web_url=getattr(issue, "web_url", None),
                    )
                )
                if len(result) >= _MAX_ITEMS:
                    break
            return result
        except self._exceptions.GitlabError as exc:
            raise ExternalServiceError(f"Could not fetch issues: {exc}") from exc

    def fetch_previous_releases(self, project_path: str, limit: int = 10) -> list[PreviousRelease]:
        """Previous GitLab releases, used as historical context for RAG."""
        project = self._project(project_path)
        try:
            releases = project.releases.list(per_page=limit, get_all=False)
            return [
                PreviousRelease(
                    tag_name=r.tag_name,
                    name=getattr(r, "name", None),
                    description=getattr(r, "description", None),
                    released_at=_parse_dt(getattr(r, "released_at", None)),
                )
                for r in releases
            ]
        except self._exceptions.GitlabError as exc:
            logger.warning("previous_releases_fetch_failed", error=str(exc))
            return []
