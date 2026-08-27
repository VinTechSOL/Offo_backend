"""add refund allocation to payment intent orders

Revision ID: 3acd8efafc66
Revises: 70b8a871636c
Create Date: 2026-08-27 22:35:58.666714

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '3acd8efafc66'
down_revision: Union[str, Sequence[str], None] = '70b8a871636c'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:

    op.add_column(
        "payment_intent_orders",
        sa.Column(
            "order_amount",
            sa.Numeric(10, 2),
            nullable=False,
            server_default="0",
        ),
        schema="payments",
    )

    op.add_column(
        "payment_intent_orders",
        sa.Column(
            "checkout_fee_share",
            sa.Numeric(10, 2),
            nullable=False,
            server_default="0",
        ),
        schema="payments",
    )

    # Remove the temporary defaults after existing rows
    # have been populated.
    op.alter_column(
        "payment_intent_orders",
        "order_amount",
        server_default=None,
        schema="payments",
    )

    op.alter_column(
        "payment_intent_orders",
        "checkout_fee_share",
        server_default=None,
        schema="payments",
    )


def downgrade() -> None:

    op.drop_column(
        "payment_intent_orders",
        "checkout_fee_share",
        schema="payments",
    )

    op.drop_column(
        "payment_intent_orders",
        "order_amount",
        schema="payments",
    )