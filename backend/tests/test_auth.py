
from sqlalchemy import select

from app.models.user import User


TEST_PASSWORD = "StrongTestPassword2026!"


def register_user(client, email, **extra_fields):
    data = {
        "email": email,
        "password": TEST_PASSWORD,
        "full_name": "Test User",
    }

    data.update(extra_fields)

    return client.post("/api/v1/auth/register", json=data)


def test_register_creates_viewer(client):
    response = register_user(
        client,
        "new-viewer@vulnflow.dev",
    )

    assert response.status_code == 201

    data = response.json()

    assert data["email"] == "new-viewer@vulnflow.dev"
    assert data["role"] == "viewer"
    assert data["is_active"] is True
    assert "password" not in data
    assert "password_hash" not in data


def test_register_rejects_admin_role(client, db_session):
    email = "admin-attempt@vulnflow.dev"

    response = register_user(
        client,
        email,
        role="admin",
    )

    assert response.status_code == 422

    errors = response.json()["detail"]

    assert any(
        error["type"] == "extra_forbidden"
        and error["loc"] == ["body", "role"]
        for error in errors
    )

    user = db_session.scalar(
        select(User).where(User.email == email)
    )

    assert user is None


def test_register_duplicate_email(client):
    email = "duplicate@vulnflow.dev"

    first_response = register_user(client, email)

    assert first_response.status_code == 201

    second_response = register_user(client, email)

    assert second_response.status_code == 409


def test_login_returns_valid_token(client):
    email = "login-test@vulnflow.dev"

    register_response = register_user(client, email)

    assert register_response.status_code == 201

    login_response = client.post(
        "/api/v1/auth/login",
        json={
            "email": email,
            "password": TEST_PASSWORD,
        },
    )

    assert login_response.status_code == 200

    token_data = login_response.json()

    assert token_data["token_type"] == "bearer"
    assert token_data["access_token"]

    me_response = client.get(
        "/api/v1/auth/me",
        headers={
            "Authorization": (
                f"Bearer {token_data['access_token']}"
            )
        },
    )

    assert me_response.status_code == 200
    assert me_response.json()["email"] == email
    assert me_response.json()["role"] == "viewer"


def test_login_rejects_wrong_password(client):
    email = "wrong-password@vulnflow.dev"

    register_response = register_user(client, email)

    assert register_response.status_code == 201

    response = client.post(
        "/api/v1/auth/login",
        json={
            "email": email,
            "password": "IncorrectPassword2026!",
        },
    )

    assert response.status_code == 401


def test_viewer_cannot_create_asset(client):
    email = "viewer-permissions@vulnflow.dev"

    register_response = register_user(client, email)

    assert register_response.status_code == 201

    login_response = client.post(
        "/api/v1/auth/login",
        json={
            "email": email,
            "password": TEST_PASSWORD,
        },
    )

    assert login_response.status_code == 200

    token = login_response.json()["access_token"]

    response = client.post(
        "/api/v1/assets",
        headers={
            "Authorization": f"Bearer {token}"
        },
        json={
            "hostname": "pytest-viewer-server",
            "ip_address": "10.0.0.150",
            "operating_system": "Ubuntu 24.04",
            "environment": "test",
            "description": "Permission test",
        },
    )

    assert response.status_code == 403
    assert (
        response.json()["detail"]
        == "Insufficient permissions"
    )
