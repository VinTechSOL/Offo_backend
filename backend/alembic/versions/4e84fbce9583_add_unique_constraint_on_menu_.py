"""add unique constraint on menu_categories category_name

Revision ID: 4e84fbce9583
Revises: c29902ef3f63
Create Date: 2026-02-03 11:19:09.713080

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '4e84fbce9583'
down_revision: Union[str, Sequence[str], None] = 'c29902ef3f63'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade():
    op.create_unique_constraint(
        "uq_menu_category_branch_name",
        "menu_categories",
        ["branch_id", "category_name"],
        schema="catalog",
    )


def downgrade():
    op.drop_constraint(
        "uq_menu_category_branch_name",
        "menu_categories",
        schema="catalog",
        type_="unique",
    )
