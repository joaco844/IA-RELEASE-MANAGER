"""Test configuration: isolated SQLite database, test env, shared fixtures."""

import os
import tempfile

from cryptography.fernet import Fernet

_TMP_DIR = tempfile.mkdtemp(prefix="airm-tests-")
os.environ["ENVIRONMENT"] = "test"
os.environ["DATABASE_URL"] = f"sqlite:///{_TMP_DIR}/test.db"
os.environ["JWT_SECRET_KEY"] = "test-jwt-secret-with-at-least-32-bytes!"
os.environ["ENCRYPTION_KEY"] = Fernet.generate_key().decode()
os.environ["RAG_ENABLED"] = "false"
os.environ["OPENAI_API_KEY"] = "test-key"

import pytest  # noqa: E402
from fastapi.testclient import TestClient  # noqa: E402

from app.db.base import Base  # noqa: E402
from app.db.session import session_scope  # noqa: E402
from app.main import app  # noqa: E402


@pytest.fixture(scope="session")
def client():
    with TestClient(app) as test_client:
        yield test_client


@pytest.fixture(autouse=True)
def clean_db(client):
    yield
    with session_scope() as session:
        for table in reversed(Base.metadata.sorted_tables):
            session.execute(table.delete())


@pytest.fixture
def auth_headers(client):
    def _make(email: str = "dev@example.com") -> dict[str, str]:
        client.post(
            "/api/v1/auth/register",
            json={"email": email, "password": "supersecret123", "full_name": "Dev User"},
        )
        response = client.post(
            "/api/v1/auth/login", json={"email": email, "password": "supersecret123"}
        )
        token = response.json()["access_token"]
        return {"Authorization": f"Bearer {token}"}

    return _make
