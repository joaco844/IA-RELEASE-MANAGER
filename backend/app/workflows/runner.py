"""Entry point that executes the release workflow for a given release.

Runs in a background task: loads everything it needs from the database,
assembles the agents and the graph, executes it, and records the outcome
(release status + GenerationLog audit row) whatever happens.
"""

from datetime import UTC, datetime
from typing import Any

from app.ai.agents.analyst import RepositoryAnalystAgent
from app.ai.agents.publisher import SlackPublisherAgent
from app.ai.agents.qa import QAAgent
from app.ai.agents.writer import ReleaseWriterAgent
from app.ai.provider import get_chat_model, get_model_name, resolve_provider
from app.ai.rag.knowledge_base import make_knowledge_base
from app.core.logging import get_logger
from app.core.security import TokenCipher
from app.db.session import session_scope
from app.integrations.gitlab_client import GitLabClient
from app.integrations.slack_client import SlackClient
from app.models import GenerationLog, Release, ReleaseStatus, SlackWorkspace
from app.workflows.nodes import ReleaseWorkflowNodes
from app.workflows.release_workflow import build_release_workflow
from app.workflows.state import ReleaseWorkflowState

logger = get_logger(__name__)


def run_release_workflow(
    release_id: int,
    auto_publish: bool = False,
    slack_channel: str | None = None,
    provider: str | None = None,
    temperature: float | None = None,
) -> None:
    cipher = TokenCipher()
    resolved_provider = resolve_provider(provider)
    model_name = get_model_name(resolved_provider)

    # Phase 1: load inputs and mark the release as running.
    with session_scope() as session:
        release = session.get(Release, release_id)
        if release is None:
            logger.error("workflow_release_missing", release_id=release_id)
            return
        repository = release.repository
        owner_id = repository.owner_id
        gitlab_token = cipher.decrypt(repository.encrypted_token)
        gitlab_url = repository.gitlab_url
        project_path = repository.project_path
        repository_name = repository.name
        repository_id = repository.id
        release_title = release.title
        range_params: dict[str, Any] = {
            "type": release.range_type,
            "from_tag": release.range_from,
            "to_tag": release.range_to,
            "days": int(release.range_from) if release.range_type == "last_days" else None,
            "since": release.range_from if release.range_type == "since_date" else None,
        }

        release.status = ReleaseStatus.RUNNING.value
        release.started_at = datetime.now(UTC)
        release.provider = resolved_provider
        release.model_name = model_name

        log = GenerationLog(
            release_id=release_id,
            status="running",
            provider=resolved_provider,
            model_name=model_name,
        )
        session.add(log)
        session.flush()
        log_id = log.id

        slack_token: str | None = None
        if auto_publish:
            workspace = session.query(SlackWorkspace).filter_by(owner_id=owner_id).first()
            if workspace:
                slack_token = cipher.decrypt(workspace.encrypted_bot_token)
                slack_channel = slack_channel or workspace.default_channel

    # Phase 2: assemble agents and run the graph.
    started = datetime.now(UTC)
    try:
        llm = get_chat_model(resolved_provider, temperature)
        publisher = SlackPublisherAgent(SlackClient(slack_token)) if slack_token else None
        nodes = ReleaseWorkflowNodes(
            gitlab=GitLabClient(gitlab_url, gitlab_token),
            analyst=RepositoryAnalystAgent(llm),
            writer=ReleaseWriterAgent(llm),
            qa=QAAgent(llm),
            session_factory=session_scope,
            knowledge_base=make_knowledge_base(repository_id, resolved_provider),
            publisher=publisher,
        )
        workflow = build_release_workflow(nodes)

        initial_state: ReleaseWorkflowState = {
            "release_id": release_id,
            "repository_id": repository_id,
            "repository_name": repository_name,
            "project_path": project_path,
            "release_title": release_title,
            "range_params": range_params,
            "auto_publish": auto_publish,
            "slack_channel": slack_channel,
            "qa_attempts": 0,
            "node_timings": {},
        }

        logger.info("workflow_started", release_id=release_id, provider=resolved_provider)
        final_state = workflow.invoke(initial_state)

        with session_scope() as session:
            log = session.get(GenerationLog, log_id)
            if log:
                log.status = "completed"
                log.finished_at = datetime.now(UTC)
                log.duration_seconds = round(
                    (log.finished_at - started).total_seconds(), 2
                )
                log.node_timings = final_state.get("node_timings", {})
        logger.info(
            "workflow_completed",
            release_id=release_id,
            timings=final_state.get("node_timings", {}),
        )

    except Exception as exc:  # noqa: BLE001 - boundary: any failure marks the release failed
        logger.exception("workflow_failed", release_id=release_id)
        with session_scope() as session:
            release = session.get(Release, release_id)
            if release:
                release.status = ReleaseStatus.FAILED.value
                release.error_message = str(exc)[:2000]
                release.completed_at = datetime.now(UTC)
            log = session.get(GenerationLog, log_id)
            if log:
                log.status = "failed"
                log.finished_at = datetime.now(UTC)
                log.duration_seconds = round((log.finished_at - started).total_seconds(), 2)
                log.error_message = str(exc)[:2000]
