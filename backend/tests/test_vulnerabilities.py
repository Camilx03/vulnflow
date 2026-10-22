
import pytest

from app.core.security import create_access_token, hash_password
from app.models.user import User, UserRole


ASSET_DATA = {
    "hostname": "pytest-vulnerability-server",
    "ip_address": "10.20.30.40",
    "operating_system": "Ubuntu 24.04",
    "environment": "test",
    "description": "Asset for vulnerability testing",
}

VULNERABILITY_DATA = {
    "cve": "CVE-2026-77777",
    "title": "Pytest Vulnerability",
    "description": "Security vulnerability created by Pytest",
    "severity": "medium",
    "cvss": 5.5,
    "assigned_user_id": None,
}


@pytest.fixture
def admin_headers(db_session):
    user = User(
        email="vulnerability-admin@vulnflow.dev",
        password_hash=hash_password("VulnerabilityTest2026!"),
        full_name="Vulnerability Test Admin",
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
        json=ASSET_DATA,
    )

    assert response.status_code == 201, response.text

    return response.json()


@pytest.fixture
def created_vulnerability(client, admin_headers, created_asset):
    data = {
        **VULNERABILITY_DATA,
        "asset_id": created_asset["id"],
    }

    response = client.post(
        "/api/v1/vulnerabilities",
        headers=admin_headers,
        json=data,
    )

    assert response.status_code == 201, response.text

    return response.json()


def test_create_vulnerability(created_vulnerability, created_asset):
    assert created_vulnerability["title"] == "Pytest Vulnerability"
    assert created_vulnerability["severity"] == "medium"
    assert created_vulnerability["cvss"] == 5.5
    assert created_vulnerability["status"] == "open"
    assert created_vulnerability["asset_id"] == created_asset["id"]


def test_get_vulnerability(
    client,
    admin_headers,
    created_vulnerability,
):
    vulnerability_id = created_vulnerability["id"]

    response = client.get(
        f"/api/v1/vulnerabilities/{vulnerability_id}",
        headers=admin_headers,
    )

    assert response.status_code == 200
    assert response.json()["id"] == vulnerability_id


def test_list_vulnerabilities(
    client,
    admin_headers,
    created_vulnerability,
):
    response = client.get(
        "/api/v1/vulnerabilities",
        headers=admin_headers,
    )

    assert response.status_code == 200

    vulnerabilities = response.json()

    assert any(
        item["id"] == created_vulnerability["id"]
        for item in vulnerabilities
    )


def test_filter_vulnerabilities_by_severity(
    client,
    admin_headers,
    created_vulnerability,
):
    response = client.get(
        "/api/v1/vulnerabilities",
        headers=admin_headers,
        params={"severity": "medium"},
    )

    assert response.status_code == 200

    vulnerabilities = response.json()

    assert any(
        item["id"] == created_vulnerability["id"]
        for item in vulnerabilities
    )

    assert all(
        item["severity"] == "medium"
        for item in vulnerabilities
    )


def test_update_vulnerability(
    client,
    admin_headers,
    created_vulnerability,
):
    vulnerability_id = created_vulnerability["id"]

    response = client.patch(
        f"/api/v1/vulnerabilities/{vulnerability_id}",
        headers=admin_headers,
        json={
            "severity": "high",
            "cvss": 8.1,
            "status": "in_progress",
        },
    )

    assert response.status_code == 200, response.text

    data = response.json()

    assert data["severity"] == "high"
    assert data["cvss"] == 8.1
    assert data["status"] == "in_progress"

    get_response = client.get(
        f"/api/v1/vulnerabilities/{vulnerability_id}",
        headers=admin_headers,
    )

    assert get_response.status_code == 200
    assert get_response.json()["status"] == "in_progress"


def test_invalid_cvss(
    client,
    admin_headers,
    created_asset,
):
    data = {
        **VULNERABILITY_DATA,
        "asset_id": created_asset["id"],
        "cvss": 15,
    }

    response = client.post(
        "/api/v1/vulnerabilities",
        headers=admin_headers,
        json=data,
    )

    assert response.status_code == 422


def test_get_nonexistent_vulnerability(client, admin_headers):
    vulnerability_id = "11111111-1111-1111-1111-111111111111"

    response = client.get(
        f"/api/v1/vulnerabilities/{vulnerability_id}",
        headers=admin_headers,
    )

    assert response.status_code == 404


def test_delete_vulnerability(
    client,
    admin_headers,
    created_vulnerability,
):
    vulnerability_id = created_vulnerability["id"]

    response = client.delete(
        f"/api/v1/vulnerabilities/{vulnerability_id}",
        headers=admin_headers,
    )

    assert response.status_code == 204

    get_response = client.get(
        f"/api/v1/vulnerabilities/{vulnerability_id}",
        headers=admin_headers,
    )

    assert get_response.status_code == 404


def test_unauthenticated_cannot_list_vulnerabilities(client):
    response = client.get("/api/v1/vulnerabilities")

    assert response.status_code == 401


def test_viewer_cannot_create_vulnerability(client, created_asset):
    email = "vulnerability-viewer@vulnflow.dev"
    password = "ViewerVulnerabilityTest2026!"

    register_response = client.post(
        "/api/v1/auth/register",
        json={
            "email": email,
            "password": password,
            "full_name": "Vulnerability Viewer",
        },
    )

    assert register_response.status_code == 201

    login_response = client.post(
        "/api/v1/auth/login",
        json={
            "email": email,
            "password": password,
        },
    )

    assert login_response.status_code == 200

    token = login_response.json()["access_token"]

    response = client.post(
        "/api/v1/vulnerabilities",
        headers={"Authorization": f"Bearer {token}"},
        json={
            **VULNERABILITY_DATA,
            "asset_id": created_asset["id"],
        },
    )

    assert response.status_code == 403


@pytest.mark.parametrize(
    "title",
    [
        "   ",
        "\t\t",
        " \n ",
    ],
)
def test_create_vulnerability_rejects_blank_title(
    client,
    admin_headers,
    created_asset,
    title,
):
    response = client.post(
        "/api/v1/vulnerabilities",
        headers=admin_headers,
        json={
            **VULNERABILITY_DATA,
            "asset_id": created_asset["id"],
            "title": title,
        },
    )

    assert response.status_code == 422


@pytest.mark.parametrize(
    "title",
    [
        "   ",
        "\t\t",
        " \n ",
    ],
)
def test_update_vulnerability_rejects_blank_title(
    client,
    admin_headers,
    created_vulnerability,
    title,
):
    vulnerability_id = created_vulnerability["id"]

    response = client.patch(
        f"/api/v1/vulnerabilities/{vulnerability_id}",
        headers=admin_headers,
        json={
            "title": title,
        },
    )

    assert response.status_code == 422

    check_response = client.get(
        f"/api/v1/vulnerabilities/{vulnerability_id}",
        headers=admin_headers,
    )

    assert check_response.status_code == 200
    assert (
        check_response.json()["title"]
        == created_vulnerability["title"]
    )


def test_create_vulnerability_normalizes_title(
    client,
    admin_headers,
    created_asset,
):
    response = client.post(
        "/api/v1/vulnerabilities",
        headers=admin_headers,
        json={
            **VULNERABILITY_DATA,
            "asset_id": created_asset["id"],
            "title": "  Critical Security Finding  ",
        },
    )

    assert response.status_code == 201, response.text
    assert response.json()["title"] == "Critical Security Finding"


def test_update_vulnerability_normalizes_title(
    client,
    admin_headers,
    created_vulnerability,
):
    vulnerability_id = created_vulnerability["id"]

    response = client.patch(
        f"/api/v1/vulnerabilities/{vulnerability_id}",
        headers=admin_headers,
        json={
            "title": "  Updated Security Finding  ",
        },
    )

    assert response.status_code == 200, response.text
    assert response.json()["title"] == "Updated Security Finding"
