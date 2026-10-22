
import pytest

from app.core.security import create_access_token, hash_password
from app.models.user import User, UserRole


ASSET_DATA = {
    "hostname": "pytest-audit-server",
    "ip_address": "10.40.50.60",
    "operating_system": "Ubuntu 24.04",
    "environment": "test",
    "description": "Asset for auditing",
}


@pytest.fixture
def admin_headers(db_session):
    user = User(
        email="audit-admin@vulnflow.dev",
        password_hash=hash_password("AuditTestPassword2026!"),
        full_name="Audit Test Admin",
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


def get_audit_logs(client, admin_headers, **filters):
    response = client.get(
        "/api/v1/audit-logs",
        headers=admin_headers,
        params={
            "page": 1,
            "page_size": 100,
            **filters,
        },
    )

    assert response.status_code == 200, response.text

    return response.json()


def test_asset_creation_generates_audit_log(
    client,
    admin_headers,
    created_asset,
):
    data = get_audit_logs(
        client,
        admin_headers,
        action="CREATE",
        entity_type="asset",
    )

    matching_logs = [
        log
        for log in data["items"]
        if log["entity_id"] == created_asset["id"]
    ]

    assert len(matching_logs) == 1

    log = matching_logs[0]

    assert log["action"] == "CREATE"
    assert log["entity_type"] == "asset"
    assert log["changes"]["hostname"] == (
        "pytest-audit-server"
    )
    assert log["user_id"]


def test_asset_update_generates_audit_log(
    client,
    admin_headers,
    created_asset,
):
    asset_id = created_asset["id"]

    response = client.patch(
        f"/api/v1/assets/{asset_id}",
        headers=admin_headers,
        json={
            "description": "Asset updated by Pytest",
        },
    )

    assert response.status_code == 200, response.text

    data = get_audit_logs(
        client,
        admin_headers,
        action="UPDATE",
        entity_type="asset",
    )

    matching_logs = [
        log
        for log in data["items"]
        if log["entity_id"] == asset_id
    ]

    assert len(matching_logs) == 1

    changes = matching_logs[0]["changes"]

    assert changes["description"]["old"] == (
        "Asset for auditing"
    )
    assert changes["description"]["new"] == (
        "Asset updated by Pytest"
    )


def test_asset_deletion_generates_audit_log(
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

    data = get_audit_logs(
        client,
        admin_headers,
        action="DELETE",
        entity_type="asset",
    )

    matching_logs = [
        log
        for log in data["items"]
        if log["entity_id"] == asset_id
    ]

    assert len(matching_logs) == 1
    assert matching_logs[0]["action"] == "DELETE"
    assert matching_logs[0]["changes"]["hostname"] == (
        "pytest-audit-server"
    )


def test_filter_audit_logs_by_action(
    client,
    admin_headers,
    created_asset,
):
    data = get_audit_logs(
        client,
        admin_headers,
        action="CREATE",
    )

    assert data["total"] >= 1

    assert all(
        log["action"] == "CREATE"
        for log in data["items"]
    )

    assert any(
        log["entity_id"] == created_asset["id"]
        for log in data["items"]
    )


def test_filter_audit_logs_by_entity_type(
    client,
    admin_headers,
    created_asset,
):
    data = get_audit_logs(
        client,
        admin_headers,
        entity_type="asset",
    )

    assert data["total"] >= 1

    assert all(
        log["entity_type"] == "asset"
        for log in data["items"]
    )

    assert any(
        log["entity_id"] == created_asset["id"]
        for log in data["items"]
    )


def test_audit_logs_pagination(
    client,
    admin_headers,
    created_asset,
):
    response = client.get(
        "/api/v1/audit-logs",
        headers=admin_headers,
        params={
            "page": 1,
            "page_size": 1,
        },
    )

    assert response.status_code == 200

    data = response.json()

    assert data["page"] == 1
    assert data["page_size"] == 1
    assert data["total"] >= 1
    assert len(data["items"]) == 1


def test_audit_logs_require_authentication(client):
    response = client.get("/api/v1/audit-logs")

    assert response.status_code == 401


def test_audit_logs_reject_invalid_page_size(
    client,
    admin_headers,
):
    response = client.get(
        "/api/v1/audit-logs",
        headers=admin_headers,
        params={
            "page": 1,
            "page_size": 101,
        },
    )

    assert response.status_code == 422
