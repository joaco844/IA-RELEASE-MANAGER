from datetime import UTC, datetime

import pytest

from app.core.security import TokenCipher
from app.db.session import session_scope
from app.models import Repository, User
from app.schemas.release import ReleaseGenerateRequest, ReleaseRange
from app.services.release_service import ReleaseService


@pytest.fixture
def user_and_repo(client):
    with session_scope() as session:
        user = User(email="svc@example.com", hashed_password="x", full_name="Svc")
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
        return user.id, repo.id


def test_range_validation_rules():
    with pytest.raises(ValueError):
        ReleaseRange(type="tag_range", from_tag="v1.0.0")
    with pytest.raises(ValueError):
        ReleaseRange(type="last_days")
    with pytest.raises(ValueError):
        ReleaseRange(type="since_date")
    assert ReleaseRange(type="last_days", days=30).days == 30


def test_create_release_range_mapping(user_and_repo):
    user_id, repo_id = user_and_repo
    with session_scope() as session:
        user = session.get(User, user_id)
        service = ReleaseService(session, runner=lambda **kw: None)

        release = service.create_release(
            user,
            ReleaseGenerateRequest(
                repository_id=repo_id,
                range=ReleaseRange(type="last_days", days=14),
            ),
        )
        assert release.range_summary == "Last 14 days"
        assert release.range_from == "14"
        assert release.status == "pending"
        assert "Demo release" in release.title

        release = service.create_release(
            user,
            ReleaseGenerateRequest(
                repository_id=repo_id,
                title="Custom title",
                range=ReleaseRange(
                    type="since_date", since=datetime(2026, 5, 1, tzinfo=UTC)
                ),
            ),
        )
        assert release.title == "Custom title"
        assert release.range_summary == "Since 2026-05-01"
