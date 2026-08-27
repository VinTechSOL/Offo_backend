"""added ticket message

Revision ID: ca821b3ad1c0
Revises: a313bc8bfcf1
Create Date: 2026-08-26 09:41:53.253084

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'ca821b3ad1c0'
down_revision: Union[str, Sequence[str], None] = 'a313bc8bfcf1'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "ticket_messages",
        sa.Column(
            "message_id",
            sa.BigInteger(),
            primary_key=True,
            nullable=False,
        ),
        sa.Column(
            "ticket_id",
            sa.BigInteger(),
            nullable=False,
        ),
        sa.Column(
            "sender_type",
            sa.String(length=20),
            nullable=False,
        ),
        sa.Column(
            "sender_id",
            sa.Integer(),
            nullable=False,
        ),
        sa.Column(
            "message",
            sa.Text(),
            nullable=False,
        ),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.text("CURRENT_TIMESTAMP"),
        ),
        sa.ForeignKeyConstraint(
            ["ticket_id"],
            ["support.tickets.ticket_id"],
            ondelete="CASCADE",
        ),
        schema="support",
    )

    op.create_index(
        "ix_support_ticket_messages_ticket_id",
        "ticket_messages",
        ["ticket_id"],
        unique=False,
        schema="support",
    )


def downgrade() -> None:
    op.drop_index(
        "ix_support_ticket_messages_ticket_id",
        table_name="ticket_messages",
        schema="support",
    )

    op.drop_table(
        "ticket_messages",
        schema="support",
    )