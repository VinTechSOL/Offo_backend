"""add unique constraint branch item

Revision ID: f9f2f3d127ac
Revises: 4e84fbce9583
Create Date: 2026-02-14 14:37:23.557403

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'f9f2f3d127ac'
down_revision: Union[str, Sequence[str], None] = '4e84fbce9583'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_unique_constraint(
        "uq_branch_item",
        "branch_menu_items",
        ["branch_id","item_id"],
        schema="catalog",
    )
    


def downgrade() -> None:
    op.drop_constraint(
        "uq_branch_item",
        "branch_menu_items",
        schema="catalog",
        type_="unique",
    )
