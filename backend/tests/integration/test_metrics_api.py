from app.core.security import TokenCipher
from app.db.session import session_scope
from app.models import Release, ReleaseStatus, Repository, User


def _seed(email: str) -> None:
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
        for i, status in enumerate(
            [ReleaseStatus.COMPLETED.value, ReleaseStatus.PUBLISHED.value,
             ReleaseStatus.FAILED.value]
        ):
            session.add(
                Release(
                    repository_id=repo.id,
                    title=f"Release {i}",
                    status=status,
                    range_type="last_days",
                    range_from="30",
                    range_summary="Last 30 days",
                    commits_analyzed=10,
                    issues_analyzed=3,
                    mrs_analyzed=2,
                    generation_seconds=60.0,
                    slack_message_url=(
                        "https://slack/p1" if status == ReleaseStatus.PUBLISHED.value else None
                    ),
                    analysis={
                        "changes": [
                            {"category": "Features"},
                            {"category": "Bug Fixes"},
                        ]
                    },
                )
            )


def test_metrics_aggregation(client, auth_headers):
    headers = auth_headers()
    _seed("dev@example.com")

    response = client.get("/api/v1/metrics", headers=headers)
    assert response.status_code == 200
    body = response.json()

    assert body["totals"]["releases"] == 3
    assert body["totals"]["completed"] == 2
    assert body["totals"]["commits_analyzed"] == 20
    assert body["totals"]["issues_analyzed"] == 6
    assert body["totals"]["slack_publications"] == 1
    assert body["totals"]["hours_saved"] > 0
    assert body["avg_generation_seconds"] == 60.0
    assert len(body["releases_by_week"]) >= 1
    categories = {c["category"]: c["count"] for c in body["categories_breakdown"]}
    assert categories == {"Features": 2, "Bug Fixes": 2}


def test_metrics_empty(client, auth_headers):
    headers = auth_headers()
    response = client.get("/api/v1/metrics", headers=headers)
    body = response.json()
    assert body["totals"]["releases"] == 0
    assert body["avg_generation_seconds"] is None
