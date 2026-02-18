"""add index on branch_menu_items.branch_id

Revision ID: aebde77b96f2
Revises: f9f2f3d127ac
Create Date: 2026-02-14 14:47:50.077844

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'aebde77b96f2'
down_revision: Union[str, Sequence[str], None] = 'f9f2f3d127ac'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    
    op.create_index('ix_branch_menu_items_branch_id', 'branch_menu_items', ['branch_id'], unique=False, schema='catalog')
    
    


def downgrade() -> None:
    
    op.drop_index('ix_branch_menu_items_branch_id', table_name='branch_menu_items', schema='catalog')
    
