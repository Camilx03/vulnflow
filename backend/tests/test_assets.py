
import pytest

from app.core.security import create_access_token, hash_password
from app.models.user import User, UserRole


ASSET_DATA = {
    "hostname": "pytest-asset-server",
    "ip_address": "10.10.20.30",
    "operating_system": "Ubuntu 24.04",
    "environment": "test",
    "description": "Asset created by Pytest",
}


@pytest.fixture
def admin_headers(db_session):
    user = User(
        email="asset-admin-test@vulnflow.dev",
        password_hash=hash_password("AssetsTestPassword2026!"),
        full_name="Asset Test Admin",
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


def test_create_asset(created_asset):
    assert created_asset["hostname"] == "pytest-asset-server"
    assert created_asset["environment"] == "test"
    assert created_asset["ip_address"] == "10.10.20.30"
    assert created_asset["id"]


def test_get_asset(client, admin_headers, created_asset):
    asset_id = created_asset["id"]

    response = client.get(
        f"/api/v1/assets/{asset_id}",
        headers=admin_headers,
    )

    assert response.status_code == 200
    assert response.json()["id"] == asset_id


def test_list_assets(client, admin_headers, created_asset):
    response = client.get(
        "/api/v1/assets",
        headers=admin_headers,
    )

    assert response.status_code == 200

    assets = response.json()

    assert any(
        asset["id"] == created_asset["id"]
        for asset in assets
    )


def test_update_asset(client, admin_headers, created_asset):
    asset_id = created_asset["id"]

    response = client.patch(
        f"/api/v1/assets/{asset_id}",
        headers=admin_headers,
        json={
            "environment": "staging",
            "description": "Updated by Pytest",
        },
    )

    assert response.status_code == 200

    data = response.json()

    assert data["environment"] == "staging"
    assert data["description"] == "Updated by Pytest"

    get_response = client.get(
        f"/api/v1/assets/{asset_id}",
        headers=admin_headers,
    )

    assert get_response.status_code == 200
    assert get_response.json()["environment"] == "staging"


def test_duplicate_hostname(client, admin_headers, created_asset):
    response = client.post(
        "/api/v1/assets",
        headers=admin_headers,
        json=ASSET_DATA,
    )

    assert response.status_code == 409


def test_delete_asset_without_vulnerabilities(
    client,
    admin_headers,
    created_asset,
):
    asset_id = created_asset["id"]

    response = client.delete(
        f"/api/v1/assets/{asset_id}",
        headers=admin_headers,
    )

    assert response.status_code == 204

    get_response = client.get(
        f"/api/v1/assets/{asset_id}",
        headers=admin_headers,
    )

    assert get_response.status_code == 404


def test_cannot_delete_asset_with_vulnerabilities(
    client,
    admin_headers,
    created_asset,
):
    asset_id = created_asset["id"]

    vulnerability_response = client.post(
        "/api/v1/vulnerabilities",
        headers=admin_headers,
        json={
            "cve": "CVE-2026-56789",
            "title": "Pytest Security Vulnerability",
            "description": "Vulnerability associated with test asset",
            "severity": "medium",
            "cvss": 5.5,
            "asset_id": asset_id,
            "assigned_user_id": None,
        },
    )

    assert vulnerability_response.status_code == 201, (
        vulnerability_response.text
    )

    vulnerability_id = vulnerability_response.json()["id"]

    delete_response = client.delete(
        f"/api/v1/assets/{asset_id}",
        headers=admin_headers,
    )

    assert delete_response.status_code == 409
    assert delete_response.json()["detail"] == (
        "Cannot delete asset with associated vulnerabilities"
    )

    asset_response = client.get(
        f"/api/v1/assets/{asset_id}",
        headers=admin_headers,
    )

    assert asset_response.status_code == 200

    vulnerability_check = client.get(
        f"/api/v1/vulnerabilities/{vulnerability_id}",
        headers=admin_headers,
    )

    assert vulnerability_check.status_code == 200


def test_unauthenticated_cannot_list_assets(client):
    response = client.get("/api/v1/assets")

    assert response.status_code == 401
