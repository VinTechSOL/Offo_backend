"""add merchant_order_id and phonepe_order_id to payment_attempts

Revision ID: 6711500e1b0a
Revises: e5f5ad0a706b
Create Date: 2026-08-05 18:12:05.282832

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '6711500e1b0a'
down_revision: Union[str, Sequence[str], None] = 'e5f5ad0a706b'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column(
        "payment_attempts",
        sa.Column(
            "merchant_order_id",
            sa.String(length=100),
            nullable=True,
        ),
        schema="payments",
    )

    op.add_column(
        "payment_attempts",
        sa.Column(
            "phonepe_order_id",
            sa.String(length=100),
            nullable=True,
        ),
        schema="payments",
    )

    op.create_unique_constraint(
        "uq_payment_attempts_merchant_order_id",
        "payment_attempts",
        ["merchant_order_id"],
        schema="payments",
    )

    op.create_unique_constraint(
        "uq_payment_attempts_phonepe_order_id",
        "payment_attempts",
        ["phonepe_order_id"],
        schema="payments",
    )


def downgrade() -> None:
    op.drop_constraint(
        "uq_payment_attempts_phonepe_order_id",
        "payment_attempts",
        schema="payments",
        type_="unique",
    )

    op.drop_constraint(
        "uq_payment_attempts_merchant_order_id",
        "payment_attempts",
        schema="payments",
        type_="unique",
    )

    op.drop_column(
        "payment_attempts",
        "phonepe_order_id",
        schema="payments",
    )

    op.drop_column(
        "payment_attempts",
        "merchant_order_id",
        schema="payments",
    )