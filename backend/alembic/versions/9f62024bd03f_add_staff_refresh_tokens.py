"""add staff refresh tokens

Revision ID: 9f62024bd03f
Revises: 3acd8efafc66
Create Date: 2026-08-28 16:55:21.430138

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '9f62024bd03f'
down_revision: Union[str, Sequence[str], None] = '3acd8efafc66'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "staff_refresh_tokens",
        sa.Column(
            "id",
            sa.BigInteger(),
            primary_key=True,
            autoincrement=True,
        ),
        sa.Column(
            "staff_id",
            sa.BigInteger(),
            sa.ForeignKey(
                "core.staff.staff_id",
                ondelete="CASCADE",
            ),
            nullable=False,
        ),
        sa.Column(
            "token_hash",
            sa.String(128),
            nullable=False,
            unique=True,
        ),
        sa.Column(
            "expires_at",
            sa.DateTime(timezone=True),
            nullable=False,
        ),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.func.now(),
        ),
        sa.Column(
            "revoked_at",
            sa.DateTime(timezone=True),
            nullable=True,
        ),
        schema="core",
    )

    op.create_index(
        "ix_staff_refresh_tokens_staff_id",
        "staff_refresh_tokens",
        ["staff_id"],
        schema="core",
    )

    op.create_index(
        "ix_staff_refresh_tokens_expires_at",
        "staff_refresh_tokens",
        ["expires_at"],
        schema="core",
    )


def downgrade() -> None:
    op.drop_index(
        "ix_staff_refresh_tokens_expires_at",
        table_name="staff_refresh_tokens",
        schema="core",
    )

    op.drop_index(
        "ix_staff_refresh_tokens_staff_id",
        table_name="staff_refresh_tokens",
        schema="core",
    )

    op.drop_table(
        "staff_refresh_tokens",
        schema="core",
    )