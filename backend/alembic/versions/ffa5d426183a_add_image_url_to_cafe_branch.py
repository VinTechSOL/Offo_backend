""" add image_url to cafe_branch

Revision ID: ffa5d426183a
Revises: e9ada8e3189f
Create Date: 2026-02-20 16:57:58.339625

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'ffa5d426183a'
down_revision: Union[str, Sequence[str], None] = 'e9ada8e3189f'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None

def upgrade():
    op.add_column(
        "cafe_branch",
        sa.Column("image_url", sa.Text(), nullable=True),
        schema="core",
    )

def downgrade():
    op.drop_column("cafe_branch", "image_url", schema="core")
