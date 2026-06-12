"""Serialize GitLab source data into compact text digests for prompts."""

from app.integrations.gitlab_client import CommitData, IssueData, MergeRequestData

_MAX_COMMITS = 150
_MAX_ITEMS = 75
_MAX_DESC = 400


def _truncate(text: str | None, limit: int = _MAX_DESC) -> str:
    if not text:
        return ""
    cleaned = " ".join(text.split())
    return cleaned[:limit] + ("…" if len(cleaned) > limit else "")


def commits_digest(commits: list[CommitData]) -> str:
    if not commits:
        return "(no commits in range)"
    lines = [
        f"- commit:{c.sha[:8]} | {c.title} | author: {c.author_name or 'unknown'}"
        for c in commits[:_MAX_COMMITS]
    ]
    if len(commits) > _MAX_COMMITS:
        lines.append(f"... and {len(commits) - _MAX_COMMITS} more commits")
    return "\n".join(lines)


def merge_requests_digest(mrs: list[MergeRequestData]) -> str:
    if not mrs:
        return "(no merged merge requests in range)"
    lines = []
    for mr in mrs[:_MAX_ITEMS]:
        labels = f" [labels: {', '.join(mr.labels)}]" if mr.labels else ""
        desc = _truncate(mr.description)
        lines.append(
            f"- mr:!{mr.iid} | {mr.title}{labels} | author: {mr.author_name or 'unknown'}"
            + (f"\n  description: {desc}" if desc else "")
        )
    if len(mrs) > _MAX_ITEMS:
        lines.append(f"... and {len(mrs) - _MAX_ITEMS} more merge requests")
    return "\n".join(lines)


def issues_digest(issues: list[IssueData]) -> str:
    if not issues:
        return "(no closed issues in range)"
    lines = []
    for issue in issues[:_MAX_ITEMS]:
        labels = f" [labels: {', '.join(issue.labels)}]" if issue.labels else ""
        desc = _truncate(issue.description)
        lines.append(
            f"- issue:#{issue.iid} | {issue.title}{labels}"
            + (f"\n  description: {desc}" if desc else "")
        )
    if len(issues) > _MAX_ITEMS:
        lines.append(f"... and {len(issues) - _MAX_ITEMS} more issues")
    return "\n".join(lines)


def source_data_digest(
    commits: list[CommitData],
    mrs: list[MergeRequestData],
    issues: list[IssueData],
) -> str:
    return (
        "## Commits\n"
        + commits_digest(commits)
        + "\n\n## Merge Requests\n"
        + merge_requests_digest(mrs)
        + "\n\n## Issues\n"
        + issues_digest(issues)
    )
