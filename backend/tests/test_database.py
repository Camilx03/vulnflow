
from sqlalchemy import text


def test_database_migrations(prepared_test_db):
    with prepared_test_db.connect() as connection:
        result = connection.execute(
            text(
                "SELECT tablename "
                "FROM pg_tables "
                "WHERE schemaname = 'public'"
            )
        )

        existing_tables = set(result.scalars().all())

    required_tables = {
        "users",
        "assets",
        "vulnerabilities",
        "comments",
        "audit_logs",
    }

    assert required_tables.issubset(existing_tables)
