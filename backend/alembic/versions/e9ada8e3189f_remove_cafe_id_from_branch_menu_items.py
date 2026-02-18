""" remove cafe_id from branch_menu_items

Revision ID: e9ada8e3189f
Revises: aebde77b96f2
Create Date: 2026-02-14 20:07:28.127663

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy import BigInteger


# revision identifiers, used by Alembic.
revision: str = 'e9ada8e3189f'
down_revision: Union[str, Sequence[str], None] = 'aebde77b96f2'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.drop_column(
        "branch_menu_items",
        "cafe_id",
        schema="catalog"
    )


def downgrade() -> None:
    op.add_column(
        "branch_menu_items",
        sa.Column("cafe_id",
                  sa,BigInteger(),nullable=False),
                  schema="catalog"
    )
