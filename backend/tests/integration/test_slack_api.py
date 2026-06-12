import pytest
from fastapi import Depends

from app.api.deps import get_slack_service
from app.core.security import TokenCipher
from app.db.session import get_db, session_scope
from app.main import app
from app.models import Release, ReleaseStatus, Repository, User
from app.services.slack_service import SlackService
from tests.fakes import FakePublisherAgent, FakeSlackClient


@pytest.fixture(autouse=True)
def fake_slack():
    def dependency(db=Depends(get_db)):
        return SlackService(
            db,
            slack_client_factory=FakeSlackClient,
            publisher_factory=FakePublisherAgent,
        )

    app.dependency_overrides[get_slack_service] = dependency
    yield
    app.dependency_overrides.pop(get_slack_service, None)


def _create_release(email: str, status: str) -> int:
    with session_scope() as session:
        user = session.query(User).filter_by(email=email).one()
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
            status=status,
            range_type="last_days",
            range_from="30",
            range_summary="Last 30 days",
            slack_notes=":rocket: notes",
            markdown_notes="# notes",
            risk_level="low",
        )
        session.add(release)
        session.flush()
        return release.id


def test_connect_workspace(client, auth_headers):
    headers = auth_headers()
    response = client.post(
        "/api/v1/slack/connect",
        json={"bot_token": "xoxb-test-token", "default_channel": "#releases"},
        headers=headers,
    )
    assert response.status_code == 201
    assert response.json()["team_name"] == "Acme Corp"

    response = client.get("/api/v1/slack/workspace", headers=headers)
    assert response.status_code == 200
    assert response.json()["default_channel"] == "#releases"


def test_workspace_404_when_not_connected(client, auth_headers):
    headers = auth_headers()
    assert client.get("/api/v1/slack/workspace", headers=headers).status_code == 404


def test_publish_completed_release(client, auth_headers):
    headers = auth_headers()
    client.post(
        "/api/v1/slack/connect",
        json={"bot_token": "xoxb-test-token", "default_channel": "#releases"},
        headers=headers,
    )
    release_id = _create_release("dev@example.com", ReleaseStatus.COMPLETED.value)

    response = client.post(
        "/api/v1/slack/publish",
        json={"release_id": release_id, "channel": "#engineering"},
        headers=headers,
    )
    assert response.status_code == 200
    assert response.json()["message_url"].startswith("https://")

    detail = client.get(f"/api/v1/releases/{release_id}", headers=headers).json()
    assert detail["status"] == "published"


def test_publish_rejects_unfinished_release(client, auth_headers):
    headers = auth_headers()
    client.post(
        "/api/v1/slack/connect",
        json={"bot_token": "xoxb-test-token", "default_channel": "#releases"},
        headers=headers,
    )
    release_id = _create_release("dev@example.com", ReleaseStatus.PENDING.value)
    response = client.post(
        "/api/v1/slack/publish", json={"release_id": release_id}, headers=headers
    )
    assert response.status_code == 422
