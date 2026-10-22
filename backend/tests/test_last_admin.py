
import uuid

from app.core.security import create_access_token, hash_password
from app.models.user import User, UserRole


def create_admin(db_session):
    user = User(
        email=f"admin-{uuid.uuid4().hex}@vulnflow.dev",
        password_hash=hash_password("AdminTestPassword2026!"),
        full_name="Test Administrator",
        role=UserRole.ADMIN,
        is_active=True,
    )

    db_session.add(user)
    db_session.flush()

    return user


def admin_headers(user):
    token = create_access_token(
        user_id=str(user.id),
        role=user.role.value,
    )

    return {"Authorization": f"Bearer {token}"}


def test_admin_can_downgrade_another_admin(
    client,
    db_session,
):
    admin_a = create_admin(db_session)
    admin_b = create_admin(db_session)

    response = client.patch(
        f"/api/v1/users/{admin_b.id}",
        headers=admin_headers(admin_a),
        json={"role": "viewer"},
    )

    assert response.status_code == 200

    db_session.refresh(admin_a)
    db_session.refresh(admin_b)

    assert admin_a.role == UserRole.ADMIN
    assert admin_a.is_active is True
    assert admin_b.role == UserRole.VIEWER


def test_revoked_admin_cannot_downgrade_remaining_admin(
    client,
    db_session,
):
    admin_a = create_admin(db_session)
    admin_b = create_admin(db_session)

    headers_a = admin_headers(admin_a)
    headers_b = admin_headers(admin_b)

    first_response = client.patch(
        f"/api/v1/users/{admin_b.id}",
        headers=headers_a,
        json={"role": "viewer"},
    )

    assert first_response.status_code == 200

    second_response = client.patch(
        f"/api/v1/users/{admin_a.id}",
        headers=headers_b,
        json={"role": "viewer"},
    )

    assert second_response.status_code == 403

    db_session.refresh(admin_a)

    assert admin_a.role == UserRole.ADMIN
    assert admin_a.is_active is True


def test_admin_can_deactivate_another_admin(
    client,
    db_session,
):
    admin_a = create_admin(db_session)
    admin_b = create_admin(db_session)

    response = client.patch(
        f"/api/v1/users/{admin_b.id}",
        headers=admin_headers(admin_a),
        json={"is_active": False},
    )

    assert response.status_code == 200

    db_session.refresh(admin_a)
    db_session.refresh(admin_b)

    assert admin_a.is_active is True
    assert admin_a.role == UserRole.ADMIN
    assert admin_b.is_active is False
