def test_register_login_me_flow(client):
    response = client.post(
        "/api/v1/auth/register",
        json={"email": "ana@example.com", "password": "supersecret123", "full_name": "Ana"},
    )
    assert response.status_code == 201
    assert response.json()["email"] == "ana@example.com"

    response = client.post(
        "/api/v1/auth/login", json={"email": "ana@example.com", "password": "supersecret123"}
    )
    assert response.status_code == 200
    token = response.json()["access_token"]

    response = client.get("/api/v1/auth/me", headers={"Authorization": f"Bearer {token}"})
    assert response.status_code == 200
    assert response.json()["full_name"] == "Ana"


def test_duplicate_email_conflict(client):
    payload = {"email": "dup@example.com", "password": "supersecret123", "full_name": "Dup"}
    assert client.post("/api/v1/auth/register", json=payload).status_code == 201
    assert client.post("/api/v1/auth/register", json=payload).status_code == 409


def test_login_wrong_password(client):
    client.post(
        "/api/v1/auth/register",
        json={"email": "x@example.com", "password": "supersecret123", "full_name": "X"},
    )
    response = client.post(
        "/api/v1/auth/login", json={"email": "x@example.com", "password": "wrong-password"}
    )
    assert response.status_code == 401


def test_protected_route_requires_token(client):
    assert client.get("/api/v1/repositories").status_code == 401
    assert (
        client.get(
            "/api/v1/repositories", headers={"Authorization": "Bearer not-a-token"}
        ).status_code
        == 401
    )
