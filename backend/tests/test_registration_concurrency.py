
from concurrent.futures import ThreadPoolExecutor
from threading import Barrier
from uuid import uuid4

from fastapi import HTTPException
from sqlalchemy import delete, func, select
from sqlalchemy.orm import Session
from starlette.requests import Request

from app.api.v1 import auth as auth_module
from app.models.login_rate_limit import LoginRateLimit
from app.models.user import User
from app.schemas.user import UserCreate
from app.services.login_rate_limit import _key_hash


def test_concurrent_registration_same_email(
    prepared_test_db,
    monkeypatch,
):
    email = f"concurrent-{uuid4().hex}@vulnflow.dev"
    ip_address = "127.0.0.1"
    barrier = Barrier(2, timeout=10)

    original_hash_password = auth_module.hash_password

    def synchronized_hash_password(password):
        barrier.wait()
        return original_hash_password(password)

    monkeypatch.setattr(
        auth_module,
        "hash_password",
        synchronized_hash_password,
    )

    def attempt_registration():
        user_data = UserCreate(
            email=email,
            password="StrongConcurrencyTest2026!",
            full_name="Concurrency Test",
        )

        request = Request(
            {
                "type": "http",
                "client": (ip_address, 9000),
                "headers": [],
            }
        )

        with Session(prepared_test_db) as db:
            try:
                auth_module.register_user(
                    user_data=user_data,
                    request=request,
                    db=db,
                )
                return 201
            except HTTPException as exc:
                return exc.status_code

    try:
        with ThreadPoolExecutor(max_workers=2) as executor:
            results = list(
                executor.map(
                    lambda _: attempt_registration(),
                    range(2),
                )
            )

        assert sorted(results) == [201, 409]

        with Session(prepared_test_db) as db:
            user_count = db.scalar(
                select(func.count())
                .select_from(User)
                .where(User.email == email)
            )

            assert user_count == 1

    finally:
        with Session(prepared_test_db) as db:
            db.execute(
                delete(User).where(User.email == email)
            )

            db.execute(
                delete(LoginRateLimit).where(
                    LoginRateLimit.key_hash
                    == _key_hash("registration_ip", ip_address)
                )
            )

            db.commit()
