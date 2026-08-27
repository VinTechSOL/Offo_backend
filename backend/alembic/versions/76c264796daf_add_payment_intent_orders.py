"""add payment intent orders

Revision ID: 76c264796daf
Revises: ca821b3ad1c0
Create Date: 2026-08-26 12:56:54.609096

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '76c264796daf'
down_revision: Union[str, Sequence[str], None] = 'ca821b3ad1c0'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # ============================================================
    # PAYMENT INTENT ORDERS
    # ============================================================
    #
    # Allows one PaymentIntent to be associated with multiple
    # orders.
    #
    # Example:
    #
    # PaymentIntent 100
    #     ├── Order 101
    #     ├── Order 102
    #     └── Order 103
    #
    # ============================================================

    op.create_table(
        "payment_intent_orders",

        sa.Column(
            "id",
            sa.BigInteger(),
            nullable=False,
        ),

        sa.Column(
            "intent_id",
            sa.BigInteger(),
            nullable=False,
        ),

        sa.Column(
            "order_id",
            sa.BigInteger(),
            nullable=False,
        ),

        sa.ForeignKeyConstraint(
            ["intent_id"],
            ["payments.payment_intents.intent_id"],
            ondelete="CASCADE",
        ),

        sa.ForeignKeyConstraint(
            ["order_id"],
            ["orders.orders.order_id"],
            ondelete="CASCADE",
        ),

        sa.PrimaryKeyConstraint("id"),

        sa.UniqueConstraint(
            "order_id",
            name="uq_payment_intent_orders_order_id",
        ),

        schema="payments",
    )


def downgrade() -> None:
    op.drop_table(
        "payment_intent_orders",
        schema="payments",
    )