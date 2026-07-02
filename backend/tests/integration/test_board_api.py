from datetime import UTC, datetime

import pytest

from app.api.deps import get_board_service, get_repository_service
from app.core.exceptions import NotFoundError
from app.db.session import get_db
from app.integrations.gitlab_client import BoardIssueData
from app.main import app
from app.services.board_service import BoardService
from app.services.repository_service import RepositoryService
from tests.fakes import FakeGitLabClient, sample_board_issues

CONNECT_PAYLOAD = {
    "gitlab_url": "https://gitlab.example.com",
    "project_path": "acme/demo",
    "access_token": "glpat-test-token",
}


class StatefulFakeGitLabClient(FakeGitLabClient):
    """Board fake with a shared issue store so writes persist across requests."""

    issues: list[BoardIssueData] = []

    def fetch_board_issues(self, project_path: str):
        return list(type(self).issues)

    def create_issue(self, project_path, title, description=None, labels=None):
        issue = BoardIssueData(
            iid=max((i.iid for i in type(self).issues), default=0) + 1,
            title=title,
            state="opened",
            labels=list(labels or []),
            author_name="Dev User",
            assignee_names=[],
            milestone=None,
            created_at=datetime(2026, 6, 20, tzinfo=UTC),
            closed_at=None,
            web_url="https://gitlab.example.com/-/issues/new",
            user_notes_count=0,
        )
        type(self).issues.append(issue)
        return issue

    def update_board_issue(
        self, project_path, issue_iid, add_label=None, remove_label=None, state_event=None
    ):
        for issue in type(self).issues:
            if issue.iid == issue_iid:
                labels = set(issue.labels)
                if remove_label:
                    labels.discard(remove_label)
                if add_label:
                    labels.add(add_label)
                issue.labels = sorted(labels)
                if state_event == "close":
                    issue.state = "closed"
                elif state_event == "reopen":
                    issue.state = "opened"
                return issue
        raise NotFoundError(f"Issue #{issue_iid} not found")


@pytest.fixture(autouse=True)
def fake_gitlab():
    from fastapi import Depends

    StatefulFakeGitLabClient.issues = sample_board_issues()

    def repo_dependency(db=Depends(get_db)):
        return RepositoryService(db, gitlab_client_factory=FakeGitLabClient)

    def board_dependency(db=Depends(get_db)):
        return BoardService(db, gitlab_client_factory=StatefulFakeGitLabClient)

    app.dependency_overrides[get_repository_service] = repo_dependency
    app.dependency_overrides[get_board_service] = board_dependency
    yield
    app.dependency_overrides.pop(get_repository_service, None)
    app.dependency_overrides.pop(get_board_service, None)


def _connect_repo(client, headers) -> int:
    return client.post(
        "/api/v1/repositories/connect", json=CONNECT_PAYLOAD, headers=headers
    ).json()["id"]


def test_default_board_has_open_and_closed_columns(client, auth_headers):
    headers = auth_headers()
    repo_id = _connect_repo(client, headers)

    response = client.get(f"/api/v1/repositories/{repo_id}/board", headers=headers)
    assert response.status_code == 200
    board = response.json()

    assert board["repository_id"] == repo_id
    assert [c["type"] for c in board["columns"]] == ["open", "closed"]
    open_col, closed_col = board["columns"]
    assert {i["iid"] for i in open_col["issues"]} == {1, 2, 3}
    assert {i["iid"] for i in closed_col["issues"]} == {4}
    assert {label["name"] for label in board["labels"]} == {"bug", "feature", "backend"}


def test_add_label_list_moves_matching_open_issues(client, auth_headers):
    headers = auth_headers()
    repo_id = _connect_repo(client, headers)

    response = client.post(
        f"/api/v1/repositories/{repo_id}/board/lists", json={"label": "bug"}, headers=headers
    )
    assert response.status_code == 201
    assert response.json()["label"] == "bug"

    board = client.get(f"/api/v1/repositories/{repo_id}/board", headers=headers).json()
    assert [c["type"] for c in board["columns"]] == ["open", "label", "closed"]
    open_col, bug_col, closed_col = board["columns"]

    # The open bug issue moved to the label list; the closed one stays in Closed.
    assert {i["iid"] for i in bug_col["issues"]} == {1}
    assert {i["iid"] for i in open_col["issues"]} == {2, 3}
    assert {i["iid"] for i in closed_col["issues"]} == {4}
    assert bug_col["label"]["color"] == "#d9534f"


def test_add_list_validations(client, auth_headers):
    headers = auth_headers()
    repo_id = _connect_repo(client, headers)

    assert (
        client.post(
            f"/api/v1/repositories/{repo_id}/board/lists", json={"label": "bug"}, headers=headers
        ).status_code
        == 201
    )
    # Duplicate list.
    assert (
        client.post(
            f"/api/v1/repositories/{repo_id}/board/lists", json={"label": "bug"}, headers=headers
        ).status_code
        == 409
    )
    # Label that does not exist in the GitLab project.
    assert (
        client.post(
            f"/api/v1/repositories/{repo_id}/board/lists",
            json={"label": "nope"},
            headers=headers,
        ).status_code
        == 404
    )


def test_remove_list_restores_open_column(client, auth_headers):
    headers = auth_headers()
    repo_id = _connect_repo(client, headers)
    list_id = client.post(
        f"/api/v1/repositories/{repo_id}/board/lists", json={"label": "feature"}, headers=headers
    ).json()["id"]

    response = client.delete(
        f"/api/v1/repositories/{repo_id}/board/lists/{list_id}", headers=headers
    )
    assert response.status_code == 204

    board = client.get(f"/api/v1/repositories/{repo_id}/board", headers=headers).json()
    assert [c["type"] for c in board["columns"]] == ["open", "closed"]
    assert {i["iid"] for i in board["columns"][0]["issues"]} == {1, 2, 3}

    # Deleting it again is a 404.
    assert (
        client.delete(
            f"/api/v1/repositories/{repo_id}/board/lists/{list_id}", headers=headers
        ).status_code
        == 404
    )


def test_create_issue_appears_on_board(client, auth_headers):
    headers = auth_headers()
    repo_id = _connect_repo(client, headers)

    response = client.post(
        f"/api/v1/repositories/{repo_id}/board/issues",
        json={"title": "New dashboard widget", "description": "Details", "labels": ["feature"]},
        headers=headers,
    )
    assert response.status_code == 201
    created = response.json()
    assert created["state"] == "opened"
    assert created["labels"] == ["feature"]

    board = client.get(f"/api/v1/repositories/{repo_id}/board", headers=headers).json()
    open_col = board["columns"][0]
    assert created["iid"] in {i["iid"] for i in open_col["issues"]}


def test_create_issue_with_unknown_label(client, auth_headers):
    headers = auth_headers()
    repo_id = _connect_repo(client, headers)

    response = client.post(
        f"/api/v1/repositories/{repo_id}/board/issues",
        json={"title": "Broken", "labels": ["nope"]},
        headers=headers,
    )
    assert response.status_code == 404


def test_move_issue_open_to_closed_and_back(client, auth_headers):
    headers = auth_headers()
    repo_id = _connect_repo(client, headers)

    response = client.post(
        f"/api/v1/repositories/{repo_id}/board/issues/3/move",
        json={"from_column": {"type": "open"}, "to_column": {"type": "closed"}},
        headers=headers,
    )
    assert response.status_code == 200
    assert response.json()["state"] == "closed"

    board = client.get(f"/api/v1/repositories/{repo_id}/board", headers=headers).json()
    assert {i["iid"] for i in board["columns"][-1]["issues"]} == {3, 4}

    response = client.post(
        f"/api/v1/repositories/{repo_id}/board/issues/3/move",
        json={"from_column": {"type": "closed"}, "to_column": {"type": "open"}},
        headers=headers,
    )
    assert response.status_code == 200
    assert response.json()["state"] == "opened"


def test_move_issue_between_label_lists(client, auth_headers):
    headers = auth_headers()
    repo_id = _connect_repo(client, headers)
    for label in ("bug", "feature"):
        client.post(
            f"/api/v1/repositories/{repo_id}/board/lists", json={"label": label}, headers=headers
        )

    # Issue 1 (bug) → feature list: swaps the labels and stays open.
    response = client.post(
        f"/api/v1/repositories/{repo_id}/board/issues/1/move",
        json={
            "from_column": {"type": "label", "label": "bug"},
            "to_column": {"type": "label", "label": "feature"},
        },
        headers=headers,
    )
    assert response.status_code == 200
    moved = response.json()
    assert moved["state"] == "opened"
    assert "bug" not in moved["labels"]
    assert "feature" in moved["labels"]

    board = client.get(f"/api/v1/repositories/{repo_id}/board", headers=headers).json()
    columns = {c["title"]: c for c in board["columns"]}
    assert {i["iid"] for i in columns["feature"]["issues"]} == {1, 2}
    assert columns["bug"]["issues"] == []


def test_move_issue_to_unknown_list_or_issue(client, auth_headers):
    headers = auth_headers()
    repo_id = _connect_repo(client, headers)

    # No board list configured for that label.
    response = client.post(
        f"/api/v1/repositories/{repo_id}/board/issues/1/move",
        json={
            "from_column": {"type": "open"},
            "to_column": {"type": "label", "label": "bug"},
        },
        headers=headers,
    )
    assert response.status_code == 404

    # Unknown issue iid.
    response = client.post(
        f"/api/v1/repositories/{repo_id}/board/issues/999/move",
        json={"from_column": {"type": "open"}, "to_column": {"type": "closed"}},
        headers=headers,
    )
    assert response.status_code == 404


def test_board_isolated_between_users(client, auth_headers):
    headers_a = auth_headers("a@example.com")
    headers_b = auth_headers("b@example.com")
    repo_id = _connect_repo(client, headers_a)

    assert (
        client.get(f"/api/v1/repositories/{repo_id}/board", headers=headers_b).status_code == 404
    )
    assert (
        client.post(
            f"/api/v1/repositories/{repo_id}/board/lists",
            json={"label": "bug"},
            headers=headers_b,
        ).status_code
        == 404
    )
