import pytest

from app.api.deps import get_repository_service
from app.db.session import get_db
from app.main import app
from app.services.repository_service import RepositoryService
from tests.fakes import FakeGitLabClient

CONNECT_PAYLOAD = {
    "gitlab_url": "https://gitlab.example.com",
    "project_path": "acme/demo",
    "access_token": "glpat-test-token",
}


@pytest.fixture(autouse=True)
def fake_gitlab():
    from fastapi import Depends

    def dependency(db=Depends(get_db)):
        return RepositoryService(db, gitlab_client_factory=FakeGitLabClient)

    app.dependency_overrides[get_repository_service] = dependency
    yield
    app.dependency_overrides.pop(get_repository_service, None)


def test_connect_and_list_repository(client, auth_headers):
    headers = auth_headers()
    response = client.post("/api/v1/repositories/connect", json=CONNECT_PAYLOAD, headers=headers)
    assert response.status_code == 201
    body = response.json()
    assert body["name"] == "Demo Project"
    assert body["default_branch"] == "main"
    assert "access_token" not in body
    assert "encrypted_token" not in body

    response = client.get("/api/v1/repositories", headers=headers)
    assert response.status_code == 200
    assert len(response.json()) == 1


def test_connect_duplicate_conflict(client, auth_headers):
    headers = auth_headers()
    assert (
        client.post(
            "/api/v1/repositories/connect", json=CONNECT_PAYLOAD, headers=headers
        ).status_code
        == 201
    )
    assert (
        client.post(
            "/api/v1/repositories/connect", json=CONNECT_PAYLOAD, headers=headers
        ).status_code
        == 409
    )


def test_repository_detail_and_delete(client, auth_headers):
    headers = auth_headers()
    repo_id = client.post(
        "/api/v1/repositories/connect", json=CONNECT_PAYLOAD, headers=headers
    ).json()["id"]

    response = client.get(f"/api/v1/repositories/{repo_id}", headers=headers)
    assert response.status_code == 200
    assert response.json()["recent_releases"] == []

    assert client.delete(f"/api/v1/repositories/{repo_id}", headers=headers).status_code == 204
    assert client.get(f"/api/v1/repositories/{repo_id}", headers=headers).status_code == 404


def test_repository_isolated_between_users(client, auth_headers):
    headers_a = auth_headers("a@example.com")
    headers_b = auth_headers("b@example.com")
    repo_id = client.post(
        "/api/v1/repositories/connect", json=CONNECT_PAYLOAD, headers=headers_a
    ).json()["id"]

    assert client.get(f"/api/v1/repositories/{repo_id}", headers=headers_b).status_code == 404
    assert client.get("/api/v1/repositories", headers=headers_b).json() == []
