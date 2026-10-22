
from datetime import datetime, timedelta, timezone

from sqlalchemy import select, update

from app.core.config import settings
from app.models.login_rate_limit import LoginRateLimit
from app.models.user import User
from app.services.login_rate_limit import cleanup_expired_login_attempts


def register_user(client, email, headers=None):
    return client.post(
        "/api/v1/auth/register",
        json={
            "email": email,
            "password": "StrongRegistrationTest2026!",
            "full_name": "Registration Test",
        },
        headers=headers or {},
    )


def test_registration_blocks_after_limit(
    client,
    db_session,
    monkeypatch,
):
    monkeypatch.setattr(
        settings,
        "registration_ip_max_attempts",
        2,
    )

    for index in range(2):
        response = register_user(
            client,
            f"register-limit-{index}@vulnflow.dev",
        )

        assert response.status_code == 201

    blocked_email = "register-blocked@vulnflow.dev"

    response = register_user(client, blocked_email)

    assert response.status_code == 429
    assert int(response.headers["Retry-After"]) > 0

    user = db_session.scalar(
        select(User).where(User.email == blocked_email)
    )

    assert user is None


def test_registration_window_expiration(
    client,
    db_session,
    monkeypatch,
):
    monkeypatch.setattr(
        settings,
        "registration_ip_max_attempts",
        1,
    )

    first_response = register_user(
        client,
        "register-window-first@vulnflow.dev",
    )

    assert first_response.status_code == 201

    blocked_response = register_user(
        client,
        "register-window-second@vulnflow.dev",
    )

    assert blocked_response.status_code == 429

    expired_time = datetime.now(timezone.utc) - timedelta(
        minutes=settings.registration_window_minutes + 1
    )

    db_session.execute(
        update(LoginRateLimit).values(
            window_started_at=expired_time
        )
    )
    db_session.commit()

    allowed_response = register_user(
        client,
        "register-window-third@vulnflow.dev",
    )

    assert allowed_response.status_code == 201


def test_registration_ignores_forged_forwarded_headers(
    client,
    monkeypatch,
):
    monkeypatch.setattr(
        settings,
        "registration_ip_max_attempts",
        1,
    )

    first_response = register_user(
        client,
        "register-proxy-first@vulnflow.dev",
        headers={
            "X-Forwarded-For": "198.51.100.10",
        },
    )

    assert first_response.status_code == 201

    second_response = register_user(
        client,
        "register-proxy-second@vulnflow.dev",
        headers={
            "X-Forwarded-For": "198.51.100.20",
        },
    )

    assert second_response.status_code == 429


def test_cleanup_preserves_active_registration_limit(
    client,
    db_session,
    monkeypatch,
):
    monkeypatch.setattr(
        settings,
        "registration_ip_max_attempts",
        1,
    )

    first_response = register_user(
        client,
        "registration-cleanup-first@vulnflow.dev",
    )

    assert first_response.status_code == 201

    blocked_response = register_user(
        client,
        "registration-cleanup-second@vulnflow.dev",
    )

    assert blocked_response.status_code == 429

    mid_window = datetime.now(timezone.utc) - timedelta(
        minutes=45
    )

    db_session.execute(
        update(LoginRateLimit).values(
            window_started_at=mid_window
        )
    )
    db_session.commit()

    cleanup_expired_login_attempts(db_session)

    still_blocked = register_user(
        client,
        "registration-cleanup-third@vulnflow.dev",
    )

    assert still_blocked.status_code == 429
