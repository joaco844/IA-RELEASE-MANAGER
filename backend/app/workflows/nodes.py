"""Nodes of the release generation workflow.

Each node is a small, retryable unit of work that receives the shared state
and returns a partial state update. External calls (GitLab, Slack) are retried
with exponential backoff; LLM calls rely on the provider client's built-in
retries.
"""

import time
from collections.abc import Callable
from datetime import UTC, datetime
from typing import Any

from tenacity import retry, retry_if_exception_type, stop_after_attempt, wait_exponential

from app.ai.agents.analyst import RepositoryAnalystAgent
from app.ai.agents.publisher import SlackPublisherAgent
from app.ai.agents.qa import QAAgent
from app.ai.agents.writer import ReleaseWriterAgent
from app.ai.context import source_data_digest
from app.ai.rag.knowledge_base import build_documents, index_release_notes
from app.core.config import get_settings
from app.core.exceptions import ExternalServiceError
from app.core.logging import get_logger
from app.integrations.gitlab_client import GitLabClient
from app.models import Commit, Issue, MergeRequest, Release, ReleaseStatus
from app.workflows.state import ReleaseWorkflowState

logger = get_logger(__name__)

_external_retry = retry(
    retry=retry_if_exception_type(ExternalServiceError),
    stop=stop_after_attempt(get_settings().node_max_retries),
    wait=wait_exponential(multiplier=1, min=1, max=15),
    reraise=True,
)


def _timed(name: str, fn: Callable[[], dict[str, Any]]) -> dict[str, Any]:
    start = time.perf_counter()
    update = fn()
    update.setdefault("node_timings", {})[name] = round(time.perf_counter() - start, 3)
    logger.info("workflow_node_done", node=name, seconds=update["node_timings"][name])
    return update


class ReleaseWorkflowNodes:
    def __init__(
        self,
        gitlab: GitLabClient,
        analyst: RepositoryAnalystAgent,
        writer: ReleaseWriterAgent,
        qa: QAAgent,
        session_factory: Callable[..., Any],
        knowledge_base: Any | None = None,
        publisher: SlackPublisherAgent | None = None,
    ) -> None:
        self.gitlab = gitlab
        self.analyst = analyst
        self.writer = writer
        self.qa = qa
        self.session_factory = session_factory
        self.kb = knowledge_base
        self.publisher = publisher

    # 1 ──────────────────────────────────────────────────────────────────
    def fetch_release_data(self, state: ReleaseWorkflowState) -> dict[str, Any]:
        @_external_retry
        def _fetch() -> dict[str, Any]:
            window = self.gitlab.resolve_range(state["project_path"], state["range_params"])
            commits = self.gitlab.fetch_commits(state["project_path"], window)
            previous = self.gitlab.fetch_previous_releases(state["project_path"])
            return {
                "window": window,
                "range_summary": window.summary,
                "commits": commits,
                "previous_releases": previous,
            }

        return _timed("fetch_release_data", _fetch)

    # 2 ──────────────────────────────────────────────────────────────────
    def fetch_gitlab_issues(self, state: ReleaseWorkflowState) -> dict[str, Any]:
        @_external_retry
        def _fetch() -> dict[str, Any]:
            issues = self.gitlab.fetch_issues(state["project_path"], state["window"])
            return {"issues": issues}

        return _timed("fetch_gitlab_issues", _fetch)

    # 3 ──────────────────────────────────────────────────────────────────
    def fetch_merge_requests(self, state: ReleaseWorkflowState) -> dict[str, Any]:
        @_external_retry
        def _fetch() -> dict[str, Any]:
            mrs = self.gitlab.fetch_merge_requests(state["project_path"], state["window"])
            return {"merge_requests": mrs}

        return _timed("fetch_merge_requests", _fetch)

    # 4 ──────────────────────────────────────────────────────────────────
    def analyze_changes(self, state: ReleaseWorkflowState) -> dict[str, Any]:
        def _analyze() -> dict[str, Any]:
            commits = state.get("commits", [])
            mrs = state.get("merge_requests", [])
            issues = state.get("issues", [])
            if not commits and not mrs and not issues:
                raise ValueError("No changes found in the selected release range")

            # RAG: index current sources + previous releases, then retrieve
            # the most relevant historical context for the analysis.
            rag_context = ""
            if self.kb is not None:
                try:
                    docs = build_documents(
                        commits, mrs, issues, state.get("previous_releases", [])
                    )
                    self.kb.index(docs)
                    query = "release notes context: " + "; ".join(
                        c.title for c in commits[:15]
                    )
                    rag_context = self.kb.retrieve_context(query)
                except Exception as exc:  # noqa: BLE001 - RAG must not break generation
                    logger.warning("rag_step_failed", error=str(exc))

            analysis = self.analyst.run(commits, mrs, issues, rag_context)
            return {"analysis": analysis, "rag_context": rag_context}

        return _timed("analyze_changes", _analyze)

    # 5 ──────────────────────────────────────────────────────────────────
    def generate_release_notes(self, state: ReleaseWorkflowState) -> dict[str, Any]:
        def _generate() -> dict[str, Any]:
            verdict = state.get("qa_verdict")
            feedback = verdict.feedback if verdict and not verdict.approved else None
            notes = self.writer.run(
                analysis=state["analysis"],
                repository_name=state["repository_name"],
                release_title=state["release_title"],
                range_summary=state.get("range_summary", ""),
                rag_context=state.get("rag_context", ""),
                reviewer_feedback=feedback,
            )
            return {"notes": notes}

        return _timed("generate_release_notes", _generate)

    # 6 ──────────────────────────────────────────────────────────────────
    def review_output(self, state: ReleaseWorkflowState) -> dict[str, Any]:
        def _review() -> dict[str, Any]:
            digest = source_data_digest(
                state.get("commits", []),
                state.get("merge_requests", []),
                state.get("issues", []),
            )
            verdict = self.qa.run(state["notes"], digest)
            return {"qa_verdict": verdict, "qa_attempts": state.get("qa_attempts", 0) + 1}

        return _timed("review_output", _review)

    def decide_after_review(self, state: ReleaseWorkflowState) -> str:
        verdict = state["qa_verdict"]
        settings = get_settings()
        if not verdict.approved and state.get("qa_attempts", 0) <= settings.qa_max_revisions:
            logger.info(
                "qa_requested_revision",
                attempt=state.get("qa_attempts", 0),
                issues=verdict.issues_found,
            )
            return "revise"
        return "continue"

    # 7 ──────────────────────────────────────────────────────────────────
    def publish_to_slack(self, state: ReleaseWorkflowState) -> dict[str, Any]:
        def _publish() -> dict[str, Any]:
            if not state.get("auto_publish") or self.publisher is None:
                return {"slack_message_url": None, "slack_published_channel": None}
            channel = state.get("slack_channel")
            if not channel:
                return {"slack_message_url": None, "slack_published_channel": None}

            @_external_retry
            def _do() -> dict[str, Any]:
                notes = state["notes"]
                analysis = state["analysis"]
                publication = self.publisher.publish(
                    channel=channel,
                    repository_name=state["repository_name"],
                    release_title=state["release_title"],
                    range_summary=state.get("range_summary", ""),
                    slack_notes=notes.slack,
                    risk_level=analysis.overall_risk.value,
                    markdown_notes=notes.markdown,
                    release_url=state.get("release_url"),
                )
                return {
                    "slack_message_url": publication.message_url,
                    "slack_published_channel": publication.channel,
                }

            return _do()

        return _timed("publish_to_slack", _publish)

    # 8 ──────────────────────────────────────────────────────────────────
    def persist_release(self, state: ReleaseWorkflowState) -> dict[str, Any]:
        def _persist() -> dict[str, Any]:
            notes = state["notes"]
            analysis = state["analysis"]
            verdict = state["qa_verdict"]

            with self.session_factory() as session:
                release = session.get(Release, state["release_id"])
                if release is None:
                    raise ValueError(f"Release {state['release_id']} disappeared")

                release.range_summary = state.get("range_summary", "")
                release.executive_notes = notes.executive
                release.technical_notes = notes.technical
                release.markdown_notes = notes.markdown
                release.slack_notes = notes.slack
                release.analysis = analysis.model_dump(mode="json")
                release.qa_report = verdict.model_dump(mode="json")
                release.themes = analysis.themes
                release.risk_level = analysis.overall_risk.value
                release.commits_analyzed = len(state.get("commits", []))
                release.issues_analyzed = len(state.get("issues", []))
                release.mrs_analyzed = len(state.get("merge_requests", []))
                release.completed_at = datetime.now(UTC)
                if release.started_at:
                    started = release.started_at
                    if started.tzinfo is None:
                        started = started.replace(tzinfo=UTC)
                    release.generation_seconds = round(
                        (release.completed_at - started).total_seconds(), 2
                    )

                if state.get("slack_message_url"):
                    release.slack_message_url = state["slack_message_url"]
                    release.slack_channel = state.get("slack_published_channel")
                    release.slack_published_at = datetime.now(UTC)
                    release.status = ReleaseStatus.PUBLISHED.value
                else:
                    release.status = ReleaseStatus.COMPLETED.value

                for c in state.get("commits", []):
                    session.add(
                        Commit(
                            release_id=release.id,
                            sha=c.sha,
                            title=c.title[:500],
                            message=c.message,
                            author_name=c.author_name,
                            author_email=c.author_email,
                            authored_at=c.authored_at,
                            web_url=c.web_url,
                        )
                    )
                for issue in state.get("issues", []):
                    session.add(
                        Issue(
                            release_id=release.id,
                            gitlab_iid=issue.iid,
                            title=issue.title[:500],
                            description=issue.description,
                            state=issue.state,
                            labels=issue.labels,
                            author_name=issue.author_name,
                            closed_at=issue.closed_at,
                            web_url=issue.web_url,
                        )
                    )
                for mr in state.get("merge_requests", []):
                    session.add(
                        MergeRequest(
                            release_id=release.id,
                            gitlab_iid=mr.iid,
                            title=mr.title[:500],
                            description=mr.description,
                            state=mr.state,
                            labels=mr.labels,
                            author_name=mr.author_name,
                            merged_at=mr.merged_at,
                            web_url=mr.web_url,
                        )
                    )

            # Feed the final notes back into the knowledge base for future releases.
            if self.kb is not None:
                index_release_notes(self.kb, state["release_title"], notes.markdown)

            return {}

        return _timed("persist_release", _persist)
