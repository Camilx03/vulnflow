
import uuid

import pytest
from sqlalchemy import select

from app.core.security import create_access_token, hash_password
from app.models.audit_log import AuditLog
from app.models.user import User, UserRole


def make_user(db_session, email, role=UserRole.VIEWER):
    user = User(
        email=email,
        password_hash=hash_password("AdminTestPassword2026!"),
        full_name="Admin Endpoint Test",
        role=role,
        is_active=True,
    )

    db_session.add(user)
    db_session.flush()

    return user


def auth_headers(user):
    token = create_access_token(
        user_id=str(user.id),
        role=user.role.value,
    )

    return {"Authorization": f"Bearer {token}"}


def test_admin_can_change_user_role(client, db_session):
    admin = make_user(
        db_session,
        "admin-role@vulnflow.dev",
        UserRole.ADMIN,
    )
    target = make_user(
        db_session,
        "target-role@vulnflow.dev",
    )

    response = client.patch(
        f"/api/v1/users/{target.id}",
        headers=auth_headers(admin),
        json={"role": "analyst"},
    )

    assert response.status_code == 200
    assert response.json()["role"] == "analyst"

    audit = db_session.scalar(
        select(AuditLog).where(
            AuditLog.entity_type == "user",
            AuditLog.entity_id == target.id,
        )
    )

    assert audit is not None
    assert audit.user_id == admin.id
    assert audit.action == "UPDATE"
    assert audit.changes["role"] == {
        "old": "viewer",
        "new": "analyst",
    }


def test_admin_can_deactivate_user(client, db_session):
    admin = make_user(
        db_session,
        "admin-disable@vulnflow.dev",
        UserRole.ADMIN,
    )
    target = make_user(
        db_session,
        "target-disable@vulnflow.dev",
    )

    target_headers = auth_headers(target)

    response = client.patch(
        f"/api/v1/users/{target.id}",
        headers=auth_headers(admin),
        json={"is_active": False},
    )

    assert response.status_code == 200
    assert response.json()["is_active"] is False

    denied_response = client.get(
        "/api/v1/auth/me",
        headers=target_headers,
    )

    assert denied_response.status_code == 403


@pytest.mark.parametrize(
    "role",
    [UserRole.ANALYST, UserRole.VIEWER],
)
def test_non_admin_cannot_update_users(
    client,
    db_session,
    role,
):
    actor = make_user(
        db_session,
        f"actor-{role.value}@vulnflow.dev",
        role,
    )
    target = make_user(
        db_session,
        f"target-{role.value}@vulnflow.dev",
    )

    response = client.patch(
        f"/api/v1/users/{target.id}",
        headers=auth_headers(actor),
        json={"role": "admin"},
    )

    assert response.status_code == 403


def test_update_requires_authentication(client):
    response = client.patch(
        f"/api/v1/users/{uuid.uuid4()}",
        json={"role": "admin"},
    )

    assert response.status_code == 401


def test_admin_cannot_modify_self(client, db_session):
    admin = make_user(
        db_session,
        "admin-self@vulnflow.dev",
        UserRole.ADMIN,
    )

    response = client.patch(
        f"/api/v1/users/{admin.id}",
        headers=auth_headers(admin),
        json={"is_active": False},
    )

    assert response.status_code == 403


def test_update_nonexistent_user(client, db_session):
    admin = make_user(
        db_session,
        "admin-missing@vulnflow.dev",
        UserRole.ADMIN,
    )

    response = client.patch(
        f"/api/v1/users/{uuid.uuid4()}",
        headers=auth_headers(admin),
        json={"role": "analyst"},
    )

    assert response.status_code == 404


@pytest.mark.parametrize(
    "payload",
    [
        {},
        {"role": "superadmin"},
        {"is_active": None},
        {"password_hash": "invalid"},
    ],
)
def test_update_rejects_invalid_payload(
    client,
    db_session,
    payload,
):
    admin = make_user(
        db_session,
        "admin-invalid@vulnflow.dev",
        UserRole.ADMIN,
    )
    target = make_user(
        db_session,
        "target-invalid@vulnflow.dev",
    )

    response = client.patch(
        f"/api/v1/users/{target.id}",
        headers=auth_headers(admin),
        json=payload,
    )

    assert response.status_code == 422


def test_unchanged_user_does_not_create_audit(
    client,
    db_session,
):
    admin = make_user(
        db_session,
        "admin-unchanged@vulnflow.dev",
        UserRole.ADMIN,
    )
    target = make_user(
        db_session,
        "target-unchanged@vulnflow.dev",
    )

    response = client.patch(
        f"/api/v1/users/{target.id}",
        headers=auth_headers(admin),
        json={"role": "viewer"},
    )

    assert response.status_code == 200

    audits = db_session.scalars(
        select(AuditLog).where(
            AuditLog.entity_type == "user",
            AuditLog.entity_id == target.id,
        )
    ).all()

    assert audits == []
