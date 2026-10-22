
import hashlib
import hmac
from datetime import datetime, timedelta, timezone
from math import ceil

from sqlalchemy import case, delete
from sqlalchemy.dialects.postgresql import insert
from sqlalchemy.orm import Session

from app.core.config import settings
from app.models.login_rate_limit import LoginRateLimit


def _key_hash(kind: str, value: str) -> str:
    message = f"vulnflow:login:{kind}:{value}".encode()

    return hmac.new(
        settings.jwt_secret_key.encode(),
        message,
        hashlib.sha256,
    ).hexdigest()


def _account_ip_key(email: str, ip_address: str) -> str:
    return _key_hash(
        "account_ip",
        f"{email}\x00{ip_address}",
    )


def _consume_counter(
    db: Session,
    key_hash: str,
    now: datetime,
    window: timedelta,
    max_attempts: int,
) -> int:
    table = LoginRateLimit.__table__
    expired = table.c.window_started_at <= now - window

    statement = insert(table).values(
        key_hash=key_hash,
        attempts=1,
        window_started_at=now,
    )

    statement = statement.on_conflict_do_update(
        index_elements=[table.c.key_hash],
        set_={
            "attempts": case(
                (expired, 1),
                else_=table.c.attempts + 1,
            ),
            "window_started_at": case(
                (expired, now),
                else_=table.c.window_started_at,
            ),
        },
    ).returning(
        table.c.attempts,
        table.c.window_started_at,
    )

    attempts, started_at = db.execute(statement).one()

    if attempts <= max_attempts:
        return 0

    remaining = (
        started_at + window - now
    ).total_seconds()

    return max(1, ceil(remaining))


def consume_login_attempt(
    db: Session,
    email: str,
    ip_address: str,
) -> int:
    now = datetime.now(timezone.utc)
    window = timedelta(
        minutes=settings.login_window_minutes
    )

    ip_retry_after = _consume_counter(
        db,
        _key_hash("ip", ip_address),
        now,
        window,
        settings.login_ip_max_attempts,
    )

    if ip_retry_after > 0:
        db.commit()
        return ip_retry_after

    account_retry_after = _consume_counter(
        db,
        _account_ip_key(email, ip_address),
        now,
        window,
        settings.login_account_max_attempts,
    )

    db.commit()

    return account_retry_after


def reset_account_login_attempts(
    db: Session,
    email: str,
    ip_address: str,
) -> None:
    db.execute(
        delete(LoginRateLimit).where(
            LoginRateLimit.key_hash
            == _account_ip_key(email, ip_address)
        )
    )

    db.commit()


def cleanup_expired_login_attempts(
    db: Session,
) -> int:
    cutoff = datetime.now(timezone.utc) - timedelta(
        minutes=settings.login_window_minutes * 2
    )

    result = db.execute(
        delete(LoginRateLimit).where(
            LoginRateLimit.window_started_at < cutoff
        )
    )

    db.commit()

    return result.rowcount


def consume_registration_attempt(
    db: Session,
    ip_address: str,
) -> int:
    now = datetime.now(timezone.utc)

    window = timedelta(
        minutes=settings.registration_window_minutes
    )

    retry_after = _consume_counter(
        db,
        _key_hash("registration_ip", ip_address),
        now,
        window,
        settings.registration_ip_max_attempts,
    )

    db.commit()

    return retry_after
