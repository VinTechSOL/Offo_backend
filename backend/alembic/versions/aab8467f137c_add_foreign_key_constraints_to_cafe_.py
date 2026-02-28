"""add foreign key constraints to cafe_branch

Revision ID: aab8467f137c
Revises: ffa5d426183a
Create Date: 2026-02-24 16:46:12.332731

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'aab8467f137c'
down_revision: Union[str, Sequence[str], None] = 'ffa5d426183a'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_foreign_key(
        "fk_cafe_branch_cafe_id",
        "cafe_branch",
        "cafeteria",
        ["cafe_id"],
        ["cafe_id"],
        source_schema="core",
        referent_schema="core",
        ondelete="CASCADE",
    )



def downgrade() -> None:
    op.drop_constraint("fk_cafe_branch_building_id", "cafe_branch", schema="core", type_="foreignkey")
