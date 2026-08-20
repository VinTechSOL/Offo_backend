"""add payment events and payment status default order table

Revision ID: 614f2a1093cd
Revises: 6711500e1b0a
Create Date: 2026-08-10 23:07:36.409385

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '614f2a1093cd'
down_revision: Union[str, Sequence[str], None] = '6711500e1b0a'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # ---------------------------------------------------------
    # 1. Add default PENDING to orders.orders.payment_status
    # ---------------------------------------------------------

    op.alter_column(
        "orders",
        "payment_status",
        schema="orders",
        existing_type=sa.String(length=30),
        existing_nullable=False,
        server_default=sa.text("'PENDING'"),
    )

    # ---------------------------------------------------------
    # 2. Create orders.payment_events
    # ---------------------------------------------------------

    op.create_table(
        "payment_events",
        sa.Column(
            "id",
            sa.BigInteger(),
            primary_key=True,
            nullable=False,
        ),
        sa.Column(
            "order_id",
            sa.BigInteger(),
            nullable=False,
        ),
        sa.Column(
            "event_type",
            sa.String(length=40),
            nullable=False,
        ),
        sa.Column(
            "payment_status",
            sa.String(length=30),
            nullable=False,
        ),
        sa.Column(
            "amount",
            sa.Numeric(10, 2),
            nullable=True,
        ),
        sa.Column(
            "provider_reference",
            sa.String(length=255),
            nullable=True,
        ),
        sa.Column(
            "provider_transaction_id",
            sa.String(length=255),
            nullable=True,
        ),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.text("CURRENT_TIMESTAMP"),
        ),
        sa.ForeignKeyConstraint(
            ["order_id"],
            ["orders.orders.order_id"],
            ondelete="CASCADE",
        ),
        schema="orders",
    )

    # ---------------------------------------------------------
    # 3. Index payment_events.order_id
    # ---------------------------------------------------------

    op.create_index(
        "ix_orders_payment_events_order_id",
        "payment_events",
        ["order_id"],
        unique=False,
        schema="orders",
    )


def downgrade() -> None:
    # Remove index
    op.drop_index(
        "ix_orders_payment_events_order_id",
        table_name="payment_events",
        schema="orders",
    )

    # Remove payment_events table
    op.drop_table(
        "payment_events",
        schema="orders",
    )

    # Remove PENDING default from orders.orders.payment_status
    op.alter_column(
        "orders",
        "payment_status",
        schema="orders",
        existing_type=sa.String(length=30),
        existing_nullable=False,
        server_default=None,
    )
