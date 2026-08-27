""" add refresh sessions

Revision ID: a313bc8bfcf1
Revises: 4367c61a8aaa
Create Date: 2026-08-24 21:44:01.217081

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'a313bc8bfcf1'
down_revision: Union[str, Sequence[str], None] = '4367c61a8aaa'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "refresh_sessions",
        sa.Column(
            "session_id",
            sa.BigInteger(),
            primary_key=True,
            nullable=False,
        ),
        sa.Column(
            "user_id",
            sa.BigInteger(),
            nullable=False,
        ),
        sa.Column(
            "token_hash",
            sa.String(length=64),
            nullable=False,
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
            "last_used_at",
            sa.DateTime(timezone=True),
            nullable=True,
        ),
        sa.Column(
            "revoked_at",
            sa.DateTime(timezone=True),
            nullable=True,
        ),
        sa.ForeignKeyConstraint(
            ["user_id"],
            ["core.users.user_id"],
            ondelete="CASCADE",
        ),
        schema="core",
    )

    op.create_index(
        "ix_core_refresh_sessions_user_id",
        "refresh_sessions",
        ["user_id"],
        unique=False,
        schema="core",
    )

    op.create_index(
        "ix_core_refresh_sessions_token_hash",
        "refresh_sessions",
        ["token_hash"],
        unique=True,
        schema="core",
    )

    op.create_index(
        "ix_core_refresh_sessions_expires_at",
        "refresh_sessions",
        ["expires_at"],
        unique=False,
        schema="core",
    )

    op.create_index(
        "ix_core_refresh_sessions_revoked_at",
        "refresh_sessions",
        ["revoked_at"],
        unique=False,
        schema="core",
    )


def downgrade() -> None:
    op.drop_index(
        "ix_core_refresh_sessions_revoked_at",
        table_name="refresh_sessions",
        schema="core",
    )

    op.drop_index(
        "ix_core_refresh_sessions_expires_at",
        table_name="refresh_sessions",
        schema="core",
    )

    op.drop_index(
        "ix_core_refresh_sessions_token_hash",
        table_name="refresh_sessions",
        schema="core",
    )

    op.drop_index(
        "ix_core_refresh_sessions_user_id",
        table_name="refresh_sessions",
        schema="core",
    )

    op.drop_table(
        "refresh_sessions",
        schema="core",
    )