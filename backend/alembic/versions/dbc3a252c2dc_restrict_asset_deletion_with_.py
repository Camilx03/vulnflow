"""restrict asset deletion with vulnerabilities

Revision ID: dbc3a252c2dc
Revises: 5583375b09bb
Create Date: 2026-10-20 23:52:07.170178

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'dbc3a252c2dc'
down_revision: Union[str, Sequence[str], None] = '5583375b09bb'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.drop_constraint(
        "vulnerabilities_asset_id_fkey",
        "vulnerabilities",
        type_="foreignkey",
    )

    op.create_foreign_key(
        "vulnerabilities_asset_id_fkey",
        "vulnerabilities",
        "assets",
        ["asset_id"],
        ["id"],
        ondelete="RESTRICT",
    )


def downgrade() -> None:
    op.drop_constraint(
        "vulnerabilities_asset_id_fkey",
        "vulnerabilities",
        type_="foreignkey",
    )

    op.create_foreign_key(
        "vulnerabilities_asset_id_fkey",
        "vulnerabilities",
        "assets",
        ["asset_id"],
        ["id"],
        ondelete="CASCADE",
    )