
import os
import sys
from pathlib import Path

import pytest
from alembic import command
from alembic.config import Config
from fastapi.testclient import TestClient
from sqlalchemy import text
from sqlalchemy.engine import make_url
from sqlalchemy.orm import Session

if "app.db.database" in sys.modules:
    raise RuntimeError(
        "Database engine was imported before test configuration"
    )

from app.core.config import settings

test_password = os.environ.get("VULNFLOW_TEST_DB_PASSWORD")

if not test_password:
    raise RuntimeError(
        "VULNFLOW_TEST_DB_PASSWORD is not configured"
    )

original_url = make_url(settings.database_url)

if original_url.get_backend_name() != "postgresql":
    raise RuntimeError("PostgreSQL is required for tests")

test_url = original_url.set(
    host="127.0.0.1",
    port=5433,
    database="vulnflow_test",
    username="vulnflow_test",
    password=test_password,
    query={},
)

if (
    test_url.host != "127.0.0.1"
    or test_url.port != 5433
    or test_url.database != "vulnflow_test"
    or test_url.username != "vulnflow_test"
):
    raise RuntimeError("Unsafe test database configuration")

settings.database_url = test_url.render_as_string(
    hide_password=False
)

os.environ["DATABASE_URL"] = settings.database_url

from app.db.database import engine, get_db
from app.main import app


@pytest.fixture(scope="session")
def prepared_test_db():
    engine_url = engine.url

    if (
        engine_url.host != "127.0.0.1"
        or engine_url.port != 5433
        or engine_url.database != "vulnflow_test"
        or engine_url.username != "vulnflow_test"
    ):
        raise RuntimeError(
            "Tests cannot run against the main database"
        )

    with engine.connect() as connection:
        database_name, database_user = connection.execute(
            text("SELECT current_database(), current_user")
        ).one()

        if (
            database_name != "vulnflow_test"
            or database_user != "vulnflow_test"
        ):
            raise RuntimeError(
                "Connected to an unexpected database"
            )

    backend_dir = Path(__file__).resolve().parents[1]

    alembic_config = Config(
        str(backend_dir / "alembic.ini")
    )

    command.upgrade(alembic_config, "head")

    return engine


@pytest.fixture
def db_session(prepared_test_db):
    with prepared_test_db.connect() as connection:
        transaction = connection.begin()

        session = Session(
            bind=connection,
            autoflush=False,
            expire_on_commit=False,
            join_transaction_mode="create_savepoint",
        )

        try:
            yield session
        finally:
            session.close()

            if transaction.is_active:
                transaction.rollback()
            else:
                raise RuntimeError(
                    "Test transaction was unexpectedly closed"
                )


@pytest.fixture
def client(db_session):
    def override_get_db():
        yield db_session

    app.dependency_overrides[get_db] = override_get_db

    try:
        with TestClient(app) as test_client:
            yield test_client
    finally:
        app.dependency_overrides.pop(get_db, None)
