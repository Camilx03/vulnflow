
from alembic import op
import sqlalchemy as sa


revision = "e2f49a7c1b36"
down_revision = "dbc3a252c2dc"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "login_rate_limits",
        sa.Column(
            "key_hash",
            sa.String(length=64),
            primary_key=True,
        ),
        sa.Column(
            "attempts",
            sa.Integer(),
            nullable=False,
        ),
        sa.Column(
            "window_started_at",
            sa.DateTime(timezone=True),
            nullable=False,
        ),
    )

    op.create_index(
        "ix_login_rate_limits_window_started_at",
        "login_rate_limits",
        ["window_started_at"],
    )


def downgrade() -> None:
    op.drop_index(
        "ix_login_rate_limits_window_started_at",
        table_name="login_rate_limits",
    )

    op.drop_table("login_rate_limits")
