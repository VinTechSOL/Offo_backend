"""add cafe branch timings

Revision ID: c29902ef3f63
Revises: 1a4775510f4b
Create Date: 2026-01-29 18:49:49.527698

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'c29902ef3f63'
down_revision: Union[str, Sequence[str], None] = '1a4775510f4b'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""

    # 1. Add columns as nullable
    op.add_column(
        "cafe_branch",
        sa.Column("opens_at", sa.Time(), nullable=True),
        schema="core",
    )
    op.add_column(
        "cafe_branch",
        sa.Column("closes_at", sa.Time(), nullable=True),
        schema="core",
    )

    # 2. Backfill existing rows
    op.execute("""
        UPDATE core.cafe_branch
        SET opens_at = '00:00:00'
        WHERE opens_at IS NULL
    """)

    op.execute("""
        UPDATE core.cafe_branch
        SET closes_at = '23:59:59'
        WHERE closes_at IS NULL
    """)

    # 3. Enforce NOT NULL after data is safe
    op.alter_column(
        "cafe_branch",
        "opens_at",
        nullable=False,
        schema="core",
    )
    op.alter_column(
        "cafe_branch",
        "closes_at",
        nullable=False,
        schema="core",
    )




def downgrade() -> None:
    """Downgrade schema."""
    pass
