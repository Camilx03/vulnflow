
import uuid
from concurrent.futures import ThreadPoolExecutor
from threading import Barrier

import pytest

from fastapi.testclient import TestClient
from sqlalchemy import delete, select
from sqlalchemy.orm import Session

from app.core.security import create_access_token, hash_password
from app.db.database import get_db
from app.main import app
from app.models.audit_log import AuditLog
from app.models.user import User, UserRole


@pytest.mark.parametrize(
    "changes",
    [
        {"role": "viewer"},
        {"is_active": False},
    ],
)
def test_concurrent_admin_removals(prepared_test_db, changes):
    engine = prepared_test_db

    admin_a_id = uuid.uuid4()
    admin_b_id = uuid.uuid4()
    admin_ids = [admin_a_id, admin_b_id]

    with Session(engine) as db:
        admins = [
            User(
                id=admin_id,
                email=f"concurrent-{admin_id.hex}@vulnflow.dev",
                password_hash=hash_password(
                    "ConcurrencyTestPassword2026!"
                ),
                full_name=f"Concurrent Admin {index}",
                role=UserRole.ADMIN,
                is_active=True,
            )
            for index, admin_id in enumerate(admin_ids)
        ]

        db.add_all(admins)
        db.commit()

    barrier = Barrier(2)

    def independent_db():
        with Session(
            engine,
            autoflush=False,
            expire_on_commit=False,
        ) as db:
            barrier.wait(timeout=10)
            yield db

    previous_overrides = app.dependency_overrides.copy()
    app.dependency_overrides[get_db] = independent_db

    try:
        def downgrade(client, actor_id, target_id):
            token = create_access_token(
                user_id=str(actor_id),
                role=UserRole.ADMIN.value,
            )

            return client.patch(
                f"/api/v1/users/{target_id}",
                headers={
                    "Authorization": f"Bearer {token}"
                },
                json=changes,
            )

        with TestClient(app) as client:
            with ThreadPoolExecutor(max_workers=2) as executor:
                first = executor.submit(
                    downgrade,
                    client,
                    admin_a_id,
                    admin_b_id,
                )

                second = executor.submit(
                    downgrade,
                    client,
                    admin_b_id,
                    admin_a_id,
                )

                responses = [
                    first.result(timeout=20),
                    second.result(timeout=20),
                ]

        statuses = sorted(
            response.status_code for response in responses
        )

        assert statuses == [200, 403]

        with Session(engine) as db:
            admins = db.scalars(
                select(User).where(User.id.in_(admin_ids))
            ).all()

            active_admins = [
                user
                for user in admins
                if user.role == UserRole.ADMIN
                and user.is_active
            ]

            assert len(admins) == 2
            assert len(active_admins) == 1

            audit_logs = db.scalars(
                select(AuditLog).where(
                    AuditLog.user_id.in_(admin_ids),
                    AuditLog.entity_type == "user",
                    AuditLog.action == "UPDATE",
                )
            ).all()

            assert len(audit_logs) == 1

    finally:
        app.dependency_overrides.clear()
        app.dependency_overrides.update(previous_overrides)

        with Session(engine) as db:
            db.execute(
                delete(AuditLog).where(
                    AuditLog.user_id.in_(admin_ids)
                )
            )

            db.execute(
                delete(User).where(
                    User.id.in_(admin_ids)
                )
            )

            db.commit()
