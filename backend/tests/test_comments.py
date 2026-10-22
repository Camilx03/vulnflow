
import pytest

from app.core.security import create_access_token, hash_password
from app.models.user import User, UserRole


@pytest.fixture
def admin_headers(db_session):
    user = User(
        email="comments-admin@vulnflow.dev",
        password_hash=hash_password("CommentsTestPassword2026!"),
        full_name="Comments Test Admin",
        role=UserRole.ADMIN,
        is_active=True,
    )

    db_session.add(user)
    db_session.flush()

    token = create_access_token(
        user_id=str(user.id),
        role=user.role.value,
    )

    return {"Authorization": f"Bearer {token}"}


@pytest.fixture
def created_asset(client, admin_headers):
    response = client.post(
        "/api/v1/assets",
        headers=admin_headers,
        json={
            "hostname": "pytest-comments-server",
            "ip_address": "10.30.40.50",
            "operating_system": "Ubuntu 24.04",
            "environment": "test",
            "description": "Asset for comment testing",
        },
    )

    assert response.status_code == 201, response.text

    return response.json()


@pytest.fixture
def created_vulnerability(client, admin_headers, created_asset):
    response = client.post(
        "/api/v1/vulnerabilities",
        headers=admin_headers,
        json={
            "cve": "CVE-2026-88888",
            "title": "Comments Test Vulnerability",
            "description": "Vulnerability for comment testing",
            "severity": "medium",
            "cvss": 5.5,
            "asset_id": created_asset["id"],
            "assigned_user_id": None,
        },
    )

    assert response.status_code == 201, response.text

    return response.json()


@pytest.fixture
def created_comment(client, admin_headers, created_vulnerability):
    vulnerability_id = created_vulnerability["id"]

    response = client.post(
        f"/api/v1/vulnerabilities/{vulnerability_id}/comments",
        headers=admin_headers,
        json={
            "content": "Security team is reviewing this vulnerability.",
        },
    )

    assert response.status_code == 201, response.text

    return response.json()


def test_create_comment(created_comment, created_vulnerability):
    assert created_comment["id"]
    assert created_comment["user_id"]
    assert created_comment["content"] == (
        "Security team is reviewing this vulnerability."
    )
    assert created_comment["vulnerability_id"] == (
        created_vulnerability["id"]
    )


def test_list_comments(
    client,
    admin_headers,
    created_vulnerability,
    created_comment,
):
    vulnerability_id = created_vulnerability["id"]

    response = client.get(
        f"/api/v1/vulnerabilities/{vulnerability_id}/comments",
        headers=admin_headers,
    )

    assert response.status_code == 200

    comments = response.json()

    assert any(
        comment["id"] == created_comment["id"]
        for comment in comments
    )


def test_delete_comment(
    client,
    admin_headers,
    created_vulnerability,
    created_comment,
):
    comment_id = created_comment["id"]

    delete_response = client.delete(
        f"/api/v1/comments/{comment_id}",
        headers=admin_headers,
    )

    assert delete_response.status_code == 204

    vulnerability_id = created_vulnerability["id"]

    list_response = client.get(
        f"/api/v1/vulnerabilities/{vulnerability_id}/comments",
        headers=admin_headers,
    )

    assert list_response.status_code == 200

    assert all(
        comment["id"] != comment_id
        for comment in list_response.json()
    )


def test_create_comment_nonexistent_vulnerability(
    client,
    admin_headers,
):
    vulnerability_id = "11111111-1111-1111-1111-111111111111"

    response = client.post(
        f"/api/v1/vulnerabilities/{vulnerability_id}/comments",
        headers=admin_headers,
        json={
            "content": "Comment on nonexistent vulnerability",
        },
    )

    assert response.status_code == 404


def test_delete_nonexistent_comment(client, admin_headers):
    comment_id = "11111111-1111-1111-1111-111111111111"

    response = client.delete(
        f"/api/v1/comments/{comment_id}",
        headers=admin_headers,
    )

    assert response.status_code == 404


def test_unauthenticated_cannot_create_comment(
    client,
    created_vulnerability,
):
    vulnerability_id = created_vulnerability["id"]

    response = client.post(
        f"/api/v1/vulnerabilities/{vulnerability_id}/comments",
        json={
            "content": "Unauthorized comment attempt",
        },
    )

    assert response.status_code == 401


def test_unauthenticated_cannot_list_comments(
    client,
    created_vulnerability,
):
    vulnerability_id = created_vulnerability["id"]

    response = client.get(
        f"/api/v1/vulnerabilities/{vulnerability_id}/comments"
    )

    assert response.status_code == 401
