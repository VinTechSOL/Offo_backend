"""add vendor ticket models

Revision ID: 6edffa5a9741
Revises: 9f62024bd03f
Create Date: 2026-08-29 17:54:35.202751

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '6edffa5a9741'
down_revision: Union[str, Sequence[str], None] = '9f62024bd03f'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:

    # =====================================================
    # VENDOR TICKETS
    # =====================================================

    op.create_table(
        "vendor_tickets",

        sa.Column(
            "vendor_ticket_id",
            sa.BigInteger(),
            primary_key=True,
            nullable=False,
        ),

        sa.Column(
            "vendor_staff_id",
            sa.Integer(),
            nullable=False,
        ),

        sa.Column(
            "affected_order_ids",
            sa.Text(),
            nullable=True,
        ),

        sa.Column(
            "category",
            sa.String(length=100),
            nullable=False,
        ),

        sa.Column(
            "severity",
            sa.String(length=20),
            nullable=False,
        ),

        sa.Column(
            "subject",
            sa.String(length=255),
            nullable=False,
        ),

        sa.Column(
            "description",
            sa.Text(),
            nullable=False,
        ),

        sa.Column(
            "image_url",
            sa.String(length=500),
            nullable=True,
        ),

        sa.Column(
            "status",
            sa.String(length=30),
            nullable=False,
            server_default="open",
        ),

        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.func.now(),
        ),

        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.func.now(),
        ),

        sa.ForeignKeyConstraint(
            ["vendor_staff_id"],
            ["core.staff.staff_id"],
            ondelete="CASCADE",
        ),

        schema="support",
    )

    # =====================================================
    # VENDOR TICKET INDEXES
    # =====================================================

    op.create_index(
        "ix_support_vendor_tickets_vendor_staff_id",
        "vendor_tickets",
        ["vendor_staff_id"],
        unique=False,
        schema="support",
    )

    op.create_index(
        "ix_support_vendor_tickets_status",
        "vendor_tickets",
        ["status"],
        unique=False,
        schema="support",
    )

    # =====================================================
    # VENDOR TICKET MESSAGES
    # =====================================================

    op.create_table(
        "vendor_ticket_messages",

        sa.Column(
            "message_id",
            sa.BigInteger(),
            primary_key=True,
            nullable=False,
        ),

        sa.Column(
            "vendor_ticket_id",
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
            server_default=sa.func.now(),
        ),

        sa.ForeignKeyConstraint(
            ["vendor_ticket_id"],
            ["support.vendor_tickets.vendor_ticket_id"],
            ondelete="CASCADE",
        ),

        schema="support",
    )

    # =====================================================
    # VENDOR MESSAGE INDEX
    # =====================================================

    op.create_index(
        "ix_support_vendor_ticket_messages_vendor_ticket_id",
        "vendor_ticket_messages",
        ["vendor_ticket_id"],
        unique=False,
        schema="support",
    )


def downgrade() -> None:

    # =====================================================
    # DROP VENDOR MESSAGE INDEX
    # =====================================================

    op.drop_index(
        "ix_support_vendor_ticket_messages_vendor_ticket_id",
        table_name="vendor_ticket_messages",
        schema="support",
    )

    # =====================================================
    # DROP VENDOR TICKET MESSAGES
    # =====================================================

    op.drop_table(
        "vendor_ticket_messages",
        schema="support",
    )

    # =====================================================
    # DROP VENDOR TICKET INDEXES
    # =====================================================

    op.drop_index(
        "ix_support_vendor_tickets_status",
        table_name="vendor_tickets",
        schema="support",
    )

    op.drop_index(
        "ix_support_vendor_tickets_vendor_staff_id",
        table_name="vendor_tickets",
        schema="support",
    )

    # =====================================================
    # DROP VENDOR TICKETS
    # =====================================================

    op.drop_table(
        "vendor_tickets",
        schema="support",
    )