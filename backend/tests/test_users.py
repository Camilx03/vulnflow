
import pytest

from app.core.security import create_access_token, hash_password
from app.models.user import User, UserRole


@pytest.fixture
def users(db_session):
    records = {}

    for role in UserRole:
        user = User(
            email=f"users-{role.value}@vulnflow.dev",
            password_hash=hash_password("UsersTestPassword2026!"),
            full_name=f"Test {role.value}",
            role=role,
            is_active=True,
        )

        db_session.add(user)
        records[role] = user

    inactive_user = User(
        email="users-inactive@vulnflow.dev",
        password_hash=hash_password("UsersTestPassword2026!"),
        full_name="Inactive User",
        role=UserRole.VIEWER,
        is_active=False,
    )

    db_session.add(inactive_user)
    db_session.flush()

    return records


@pytest.mark.parametrize(
    "role,expected_status",
    [
        (UserRole.ADMIN, 200),
        (UserRole.ANALYST, 200),
        (UserRole.VIEWER, 403),
    ],
)
def test_list_users_permissions(
    client,
    users,
    role,
    expected_status,
):
    user = users[role]

    token = create_access_token(
        user_id=str(user.id),
        role=user.role.value,
    )

    response = client.get(
        "/api/v1/users",
        headers={
            "Authorization": f"Bearer {token}"
        },
    )

    assert response.status_code == expected_status

    if expected_status == 403:
        assert response.json()["detail"] == "Insufficient permissions"
        return

    data = response.json()

    emails = {item["email"] for item in data}

    assert users[UserRole.ADMIN].email in emails
    assert users[UserRole.ANALYST].email in emails
    assert users[UserRole.VIEWER].email in emails
    assert "users-inactive@vulnflow.dev" not in emails

    for item in data:
        assert item["is_active"] is True
        assert "password" not in item
        assert "password_hash" not in item


def test_list_users_requires_authentication(client):
    response = client.get("/api/v1/users")

    assert response.status_code == 401


def test_token_role_cannot_override_database_role(client, users):
    viewer = users[UserRole.VIEWER]

    token = create_access_token(
        user_id=str(viewer.id),
        role=UserRole.ADMIN.value,
    )

    response = client.get(
        "/api/v1/users",
        headers={"Authorization": f"Bearer {token}"},
    )

    assert response.status_code == 403


def test_inactive_admin_cannot_use_existing_token(
    client,
    users,
    db_session,
):
    admin = users[UserRole.ADMIN]

    token = create_access_token(
        user_id=str(admin.id),
        role=admin.role.value,
    )

    admin.is_active = False
    db_session.flush()

    response = client.get(
        "/api/v1/users",
        headers={"Authorization": f"Bearer {token}"},
    )

    assert response.status_code == 403


def test_downgraded_admin_loses_permissions(
    client,
    users,
    db_session,
):
    admin = users[UserRole.ADMIN]

    token = create_access_token(
        user_id=str(admin.id),
        role=admin.role.value,
    )

    admin.role = UserRole.VIEWER
    db_session.flush()

    response = client.get(
        "/api/v1/users",
        headers={"Authorization": f"Bearer {token}"},
    )

    assert response.status_code == 403


def test_deleted_user_cannot_use_existing_token(
    client,
    users,
    db_session,
):
    admin = users[UserRole.ADMIN]

    token = create_access_token(
        user_id=str(admin.id),
        role=admin.role.value,
    )

    db_session.delete(admin)
    db_session.flush()

    response = client.get(
        "/api/v1/users",
        headers={"Authorization": f"Bearer {token}"},
    )

    assert response.status_code == 401
