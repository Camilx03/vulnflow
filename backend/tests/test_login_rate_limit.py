
from app.core.config import settings

from datetime import datetime, timedelta, timezone

from sqlalchemy import func, select, update

from app.models.login_rate_limit import LoginRateLimit
from app.services.login_rate_limit import (
    cleanup_expired_login_attempts,
    consume_login_attempt,
    reset_account_login_attempts,
)

PASSWORD = "StrongRateLimitPassword2026!"


def create_user(client, email):
    response = client.post(
        "/api/v1/auth/register",
        json={
            "email": email,
            "password": PASSWORD,
            "full_name": "Rate Limit Test",
        },
    )
    assert response.status_code == 201


def login(client, email, password):
    return client.post(
        "/api/v1/auth/login",
        json={
            "email": email,
            "password": password,
        },
    )


def test_login_blocks_after_five_attempts(client):
    email = "rate-limit-test@vulnflow.dev"
    create_user(client, email)

    for _ in range(5):
        response = login(
            client,
            email,
            "IncorrectPassword2026!",
        )
        assert response.status_code == 401

    response = login(client, email, PASSWORD)

    assert response.status_code == 429
    assert int(response.headers["Retry-After"]) > 0


def test_successful_login_resets_account_counter(client):
    email = "rate-limit-reset@vulnflow.dev"
    create_user(client, email)

    for _ in range(4):
        response = login(
            client,
            email,
            "IncorrectPassword2026!",
        )
        assert response.status_code == 401

    response = login(client, email, PASSWORD)
    assert response.status_code == 200

    for _ in range(5):
        response = login(
            client,
            email,
            "IncorrectPassword2026!",
        )
        assert response.status_code == 401

    response = login(client, email, PASSWORD)
    assert response.status_code == 429


def test_nonexistent_account_is_rate_limited(client):
    email = "unknown-rate-limit@vulnflow.dev"

    for _ in range(5):
        response = login(
            client,
            email,
            "IncorrectPassword2026!",
        )
        assert response.status_code == 401

    response = login(
        client,
        email,
        "IncorrectPassword2026!",
    )
    assert response.status_code == 429


def test_ip_rate_limit(client, monkeypatch):
    monkeypatch.setattr(
        settings,
        "login_ip_max_attempts",
        2,
    )

    for index in range(2):
        response = login(
            client,
            f"ip-limit-{index}@vulnflow.dev",
            "IncorrectPassword2026!",
        )
        assert response.status_code == 401

    response = login(
        client,
        "ip-limit-final@vulnflow.dev",
        "IncorrectPassword2026!",
    )

    assert response.status_code == 429


def test_expired_login_window_allows_access(client, db_session):
    email = "expired-login-window@vulnflow.dev"
    create_user(client, email)

    for _ in range(settings.login_account_max_attempts):
        response = login(
            client,
            email,
            "IncorrectPassword2026!",
        )
        assert response.status_code == 401

    response = login(client, email, PASSWORD)
    assert response.status_code == 429

    expired_time = datetime.now(timezone.utc) - timedelta(
        minutes=settings.login_window_minutes + 1
    )

    db_session.execute(
        update(LoginRateLimit).values(
            window_started_at=expired_time
        )
    )
    db_session.commit()

    response = login(client, email, PASSWORD)

    assert response.status_code == 200


def test_cleanup_expired_login_attempts(client, db_session):
    response = login(
        client,
        "cleanup-login@vulnflow.dev",
        "IncorrectPassword2026!",
    )
    assert response.status_code == 401

    before = db_session.scalar(
        select(func.count()).select_from(LoginRateLimit)
    )
    assert before >= 2

    expired_time = datetime.now(timezone.utc) - timedelta(
        minutes=settings.login_window_minutes * 2 + 1
    )

    db_session.execute(
        update(LoginRateLimit).values(
            window_started_at=expired_time
        )
    )
    db_session.commit()

    deleted = cleanup_expired_login_attempts(db_session)

    remaining = db_session.scalar(
        select(func.count()).select_from(LoginRateLimit)
    )

    assert deleted == before
    assert remaining == 0


def test_blocked_ip_does_not_create_account_counters(
    client,
    db_session,
    monkeypatch,
):
    monkeypatch.setattr(
        settings,
        "login_ip_max_attempts",
        1,
    )

    first_response = login(
        client,
        "first-ip-test@vulnflow.dev",
        "IncorrectPassword2026!",
    )

    assert first_response.status_code == 401

    count_before = db_session.scalar(
        select(func.count()).select_from(LoginRateLimit)
    )

    blocked_response = login(
        client,
        "second-ip-test@vulnflow.dev",
        "IncorrectPassword2026!",
    )

    assert blocked_response.status_code == 429

    count_after = db_session.scalar(
        select(func.count()).select_from(LoginRateLimit)
    )

    assert count_after == count_before

def test_account_limit_is_isolated_by_ip(db_session):
    email = "isolation-test@vulnflow.dev"
    attacker_ip = "198.51.100.10"
    legitimate_ip = "198.51.100.20"

    for _ in range(settings.login_account_max_attempts):
        result = consume_login_attempt(
            db_session,
            email,
            attacker_ip,
        )
        assert result == 0

    blocked = consume_login_attempt(
        db_session,
        email,
        attacker_ip,
    )
    assert blocked > 0

    allowed = consume_login_attempt(
        db_session,
        email,
        legitimate_ip,
    )
    assert allowed == 0


def test_successful_login_resets_only_its_ip(db_session):
    email = "reset-isolation@vulnflow.dev"
    first_ip = "198.51.100.30"
    second_ip = "198.51.100.40"

    for _ in range(4):
        assert consume_login_attempt(
            db_session, email, first_ip
        ) == 0

        assert consume_login_attempt(
            db_session, email, second_ip
        ) == 0

    reset_account_login_attempts(
        db_session,
        email,
        first_ip,
    )

    assert consume_login_attempt(
        db_session, email, first_ip
    ) == 0

    assert consume_login_attempt(
        db_session, email, second_ip
    ) == 0

    assert consume_login_attempt(
        db_session, email, second_ip
    ) > 0


def test_inactive_user_cannot_login(client, db_session):
    from sqlalchemy import select
    from app.models.user import User

    email = "inactive-login-test@vulnflow.dev"
    create_user(client, email)

    user = db_session.scalar(
        select(User).where(User.email == email)
    )

    assert user is not None

    user.is_active = False
    db_session.commit()

    response = login(client, email, PASSWORD)

    assert response.status_code == 401
    assert response.json() == {
        "detail": "Invalid email or password"
    }
    assert "access_token" not in response.json()
