"""End-to-end test of the LangGraph workflow with fake agents and GitLab.

Exercises: the full node sequence, the QA revision loop, conditional Slack
publication and final persistence."""

from datetime import UTC, datetime

import pytest

from app.core.security import TokenCipher
from app.db.session import session_scope
from app.models import Release, ReleaseStatus, Repository, User
from app.workflows.nodes import ReleaseWorkflowNodes
from app.workflows.release_workflow import build_release_workflow
from tests.fakes import (
    FakeAnalystAgent,
    FakeGitLabClient,
    FakePublisherAgent,
    FakeQAAgent,
    FakeWriterAgent,
)


@pytest.fixture
def pending_release(client):
    with session_scope() as session:
        user = User(email="wf@example.com", hashed_password="x", full_name="WF")
        session.add(user)
        session.flush()
        repo = Repository(
            owner_id=user.id,
            name="Demo",
            gitlab_url="https://gitlab.example.com",
            project_path="acme/demo",
            encrypted_token=TokenCipher().encrypt("glpat-test"),
        )
        session.add(repo)
        session.flush()
        release = Release(
            repository_id=repo.id,
            title="Demo v1.1.0",
            status=ReleaseStatus.RUNNING.value,
            range_type="tag_range",
            range_from="v1.0.0",
            range_to="v1.1.0",
            range_summary="v1.0.0 → v1.1.0",
            started_at=datetime.now(UTC),
        )
        session.add(release)
        session.flush()
        return release.id


def _run(release_id: int, auto_publish: bool, publisher=None):
    writer = FakeWriterAgent()
    qa = FakeQAAgent(reject_first=True)
    nodes = ReleaseWorkflowNodes(
        gitlab=FakeGitLabClient(),
        analyst=FakeAnalystAgent(),
        writer=writer,
        qa=qa,
        session_factory=session_scope,
        knowledge_base=None,
        publisher=publisher,
    )
    workflow = build_release_workflow(nodes)
    final_state = workflow.invoke(
        {
            "release_id": release_id,
            "repository_id": 1,
            "repository_name": "Demo",
            "project_path": "acme/demo",
            "release_title": "Demo v1.1.0",
            "range_params": {"type": "tag_range", "from_tag": "v1.0.0", "to_tag": "v1.1.0"},
            "auto_publish": auto_publish,
            "slack_channel": "#releases" if auto_publish else None,
            "qa_attempts": 0,
            "node_timings": {},
        }
    )
    return final_state, writer, qa


def test_workflow_completes_with_qa_revision_loop(pending_release):
    final_state, writer, qa = _run(pending_release, auto_publish=False)

    # QA rejected the first draft -> writer ran twice, second time with feedback.
    assert qa.calls == 2
    assert len(writer.calls) == 2
    assert writer.calls[0] is None
    assert writer.calls[1] == "Remove the uptime claim"
    assert final_state["qa_verdict"].approved

    # All nodes reported timings.
    for node in (
        "fetch_release_data",
        "fetch_gitlab_issues",
        "fetch_merge_requests",
        "analyze_changes",
        "generate_release_notes",
        "review_output",
        "publish_to_slack",
        "persist_release",
    ):
        assert node in final_state["node_timings"]

    with session_scope() as session:
        release = session.get(Release, pending_release)
        assert release.status == ReleaseStatus.COMPLETED.value
        assert release.markdown_notes.startswith("# Release")
        assert release.qa_report["approved"] is True
        assert release.risk_level == "medium"
        assert release.commits_analyzed == 2
        assert release.issues_analyzed == 1
        assert release.mrs_analyzed == 1
        assert release.generation_seconds is not None
        assert len(release.commits) == 2
        assert len(release.issues) == 1
        assert len(release.merge_requests) == 1


def test_workflow_auto_publishes_to_slack(pending_release):
    publisher = FakePublisherAgent()
    final_state, _, _ = _run(pending_release, auto_publish=True, publisher=publisher)

    assert len(publisher.published) == 1
    assert publisher.published[0]["channel"] == "#releases"
    with session_scope() as session:
        release = session.get(Release, pending_release)
        assert release.status == ReleaseStatus.PUBLISHED.value
        assert release.slack_message_url
