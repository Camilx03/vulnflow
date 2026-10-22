
import pytest

from app.core.security import create_access_token, hash_password
from app.models.user import User, UserRole


@pytest.fixture
def admin_headers(db_session):
    user = User(
        email="dashboard-admin@vulnflow.dev",
        password_hash=hash_password("DashboardTestPassword2026!"),
        full_name="Dashboard Test Admin",
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
            "hostname": "pytest-dashboard-server",
            "ip_address": "10.50.60.70",
            "operating_system": "Ubuntu 24.04",
            "environment": "test",
            "description": "Asset for dashboard testing",
        },
    )

    assert response.status_code == 201, response.text

    return response.json()


def get_stats(client, admin_headers):
    response = client.get(
        "/api/v1/dashboard/stats",
        headers=admin_headers,
    )

    assert response.status_code == 200, response.text

    return response.json()


def create_vulnerability(
    client,
    admin_headers,
    asset_id,
    cve="CVE-2026-91001",
):
    response = client.post(
        "/api/v1/vulnerabilities",
        headers=admin_headers,
        json={
            "cve": cve,
            "title": "Dashboard Test Vulnerability",
            "description": "Vulnerability for dashboard statistics",
            "severity": "high",
            "cvss": 8.5,
            "asset_id": asset_id,
            "assigned_user_id": None,
        },
    )

    assert response.status_code == 201, response.text

    return response.json()


def test_dashboard_requires_authentication(client):
    response = client.get("/api/v1/dashboard/stats")

    assert response.status_code == 401


def test_dashboard_returns_expected_fields(client, admin_headers):
    data = get_stats(client, admin_headers)

    expected_fields = {
        "total_assets",
        "total_vulnerabilities",
        "affected_assets",
        "unassigned_vulnerabilities",
        "active_vulnerabilities",
        "by_severity",
        "by_status",
    }

    assert expected_fields.issubset(data.keys())

    expected_severities = {
        "critical",
        "high",
        "medium",
        "low",
        "info",
    }

    assert expected_severities.issubset(
        data["by_severity"].keys()
    )

    expected_statuses = {
        "open",
        "in_progress",
        "resolved",
        "accepted_risk",
        "false_positive",
    }

    assert expected_statuses.issubset(
        data["by_status"].keys()
    )


def test_dashboard_counts_new_asset(
    client,
    admin_headers,
):
    before = get_stats(client, admin_headers)

    response = client.post(
        "/api/v1/assets",
        headers=admin_headers,
        json={
            "hostname": "pytest-dashboard-new-asset",
            "ip_address": "10.50.60.71",
            "operating_system": "Ubuntu 24.04",
            "environment": "test",
            "description": "Dashboard count test",
        },
    )

    assert response.status_code == 201, response.text

    after = get_stats(client, admin_headers)

    assert after["total_assets"] == (
        before["total_assets"] + 1
    )

    assert after["total_vulnerabilities"] == (
        before["total_vulnerabilities"]
    )


def test_dashboard_counts_new_vulnerability(
    client,
    admin_headers,
    created_asset,
):
    before = get_stats(client, admin_headers)

    create_vulnerability(
        client,
        admin_headers,
        created_asset["id"],
    )

    after = get_stats(client, admin_headers)

    assert after["total_vulnerabilities"] == (
        before["total_vulnerabilities"] + 1
    )

    assert after["active_vulnerabilities"] == (
        before["active_vulnerabilities"] + 1
    )

    assert after["unassigned_vulnerabilities"] == (
        before["unassigned_vulnerabilities"] + 1
    )

    assert after["affected_assets"] == (
        before["affected_assets"] + 1
    )

    assert after["by_severity"]["high"] == (
        before["by_severity"]["high"] + 1
    )

    assert after["by_status"]["open"] == (
        before["by_status"]["open"] + 1
    )


def test_dashboard_counts_unique_affected_assets(
    client,
    admin_headers,
    created_asset,
):
    before = get_stats(client, admin_headers)

    create_vulnerability(
        client,
        admin_headers,
        created_asset["id"],
        cve="CVE-2026-91002",
    )

    create_vulnerability(
        client,
        admin_headers,
        created_asset["id"],
        cve="CVE-2026-91003",
    )

    after = get_stats(client, admin_headers)

    assert after["total_vulnerabilities"] == (
        before["total_vulnerabilities"] + 2
    )

    assert after["affected_assets"] == (
        before["affected_assets"] + 1
    )


def test_dashboard_updates_when_vulnerability_resolved(
    client,
    admin_headers,
    created_asset,
):
    vulnerability = create_vulnerability(
        client,
        admin_headers,
        created_asset["id"],
    )

    before = get_stats(client, admin_headers)

    response = client.patch(
        f"/api/v1/vulnerabilities/{vulnerability['id']}",
        headers=admin_headers,
        json={
            "status": "resolved",
        },
    )

    assert response.status_code == 200, response.text

    after = get_stats(client, admin_headers)

    assert after["by_status"]["open"] == (
        before["by_status"]["open"] - 1
    )

    assert after["by_status"]["resolved"] == (
        before["by_status"]["resolved"] + 1
    )

    assert after["active_vulnerabilities"] == (
        before["active_vulnerabilities"] - 1
    )

    assert after["total_vulnerabilities"] == (
        before["total_vulnerabilities"]
    )


def test_dashboard_updates_after_vulnerability_deletion(
    client,
    admin_headers,
    created_asset,
):
    vulnerability = create_vulnerability(
        client,
        admin_headers,
        created_asset["id"],
    )

    before = get_stats(client, admin_headers)

    response = client.delete(
        f"/api/v1/vulnerabilities/{vulnerability['id']}",
        headers=admin_headers,
    )

    assert response.status_code == 204

    after = get_stats(client, admin_headers)

    assert after["total_vulnerabilities"] == (
        before["total_vulnerabilities"] - 1
    )

    assert after["active_vulnerabilities"] == (
        before["active_vulnerabilities"] - 1
    )

    assert after["affected_assets"] == (
        before["affected_assets"] - 1
    )
