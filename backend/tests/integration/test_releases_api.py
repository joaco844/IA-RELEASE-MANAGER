import pytest
from fastapi import Depends

from app.api.deps import get_release_service
from app.core.security import TokenCipher
from app.db.session import get_db, session_scope
from app.main import app
from app.models import Release, ReleaseStatus, Repository, User
from app.services.release_service import ReleaseService

RUNS: list[dict] = []


def fake_runner(**kwargs):
    RUNS.append(kwargs)


@pytest.fixture(autouse=True)
def fake_workflow():
    RUNS.clear()

    def dependency(db=Depends(get_db)):
        return ReleaseService(db, runner=lambda **kw: fake_runner(**kw))

    app.dependency_overrides[get_release_service] = dependency
    yield
    app.dependency_overrides.pop(get_release_service, None)


def _create_repository(email: str = "dev@example.com") -> int:
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
        return repo.id


def test_generate_release_schedules_workflow(client, auth_headers):
    headers = auth_headers()
    repo_id = _create_repository()

    response = client.post(
        "/api/v1/releases/generate",
        json={
            "repository_id": repo_id,
            "range": {"type": "tag_range", "from_tag": "v1.0.0", "to_tag": "v1.1.0"},
            "ai": {"provider": "openai", "temperature": 0.1},
        },
        headers=headers,
    )
    assert response.status_code == 202
    body = response.json()
    assert body["status"] == "pending"
    assert body["range_summary"] == "v1.0.0 → v1.1.0"

    # TestClient runs background tasks before returning, so the runner was invoked.
    assert len(RUNS) == 1
    assert RUNS[0]["release_id"] == body["id"]
    assert RUNS[0]["provider"] == "openai"


def test_generate_validates_range(client, auth_headers):
    headers = auth_headers()
    repo_id = _create_repository()
    response = client.post(
        "/api/v1/releases/generate",
        json={"repository_id": repo_id, "range": {"type": "tag_range"}},
        headers=headers,
    )
    assert response.status_code == 422


def test_generate_for_foreign_repo_404(client, auth_headers):
    auth_headers("owner@example.com")
    repo_id = _create_repository("owner@example.com")
    headers_intruder = auth_headers("intruder@example.com")
    response = client.post(
        "/api/v1/releases/generate",
        json={"repository_id": repo_id, "range": {"type": "last_days", "days": 30}},
        headers=headers_intruder,
    )
    assert response.status_code == 404


def test_list_and_detail(client, auth_headers):
    headers = auth_headers()
    repo_id = _create_repository()
    with session_scope() as session:
        release = Release(
            repository_id=repo_id,
            title="Demo v1.1.0",
            status=ReleaseStatus.COMPLETED.value,
            range_type="last_days",
            range_from="30",
            range_summary="Last 30 days",
            executive_notes="exec",
            technical_notes="tech",
            markdown_notes="# md",
            slack_notes="slack",
            qa_report={"approved": True, "traceability_score": 0.95, "issues_found": []},
            analysis={
                "changes": [
                    {
                        "category": "Features",
                        "summary": "s",
                        "business_impact": "b",
                        "technical_impact": "t",
                        "risk_level": "low",
                        "source_refs": ["mr:!1"],
                    }
                ],
                "themes": ["x"],
                "overall_risk": "low",
            },
            risk_level="low",
            commits_analyzed=5,
            issues_analyzed=2,
            mrs_analyzed=1,
            generation_seconds=42.5,
        )
        session.add(release)
        session.flush()
        release_id = release.id

    response = client.get("/api/v1/releases", headers=headers)
    assert response.status_code == 200
    assert response.json()["total"] == 1

    response = client.get(f"/api/v1/releases/{release_id}", headers=headers)
    assert response.status_code == 200
    body = response.json()
    assert body["notes"]["markdown"] == "# md"
    assert body["qa_report"]["approved"] is True
    assert body["analysis"]["categories"][0]["category"] == "Features"
    assert body["metrics"]["generation_seconds"] == 42.5
    assert body["repository_name"] == "Demo"

    response = client.get("/api/v1/releases?status=failed", headers=headers)
    assert response.json()["total"] == 0
