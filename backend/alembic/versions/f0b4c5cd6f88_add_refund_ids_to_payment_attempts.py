"""add refund ids to payment attempts

Revision ID: f0b4c5cd6f88
Revises: 614f2a1093cd
Create Date: 2026-08-11 12:59:55.990620

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'f0b4c5cd6f88'
down_revision: Union[str, Sequence[str], None] = '614f2a1093cd'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column(
        "payment_attempts",
        sa.Column(
            "merchant_refund_id",
            sa.String(length=100),
            nullable=True,
        ),
        schema="payments",
    )

    op.add_column(
        "payment_attempts",
        sa.Column(
            "gateway_refund_id",
            sa.String(length=100),
            nullable=True,
        ),
        schema="payments",
    )

    op.create_unique_constraint(
        "uq_payment_attempts_merchant_refund_id",
        "payment_attempts",
        ["merchant_refund_id"],
        schema="payments",
    )

    op.create_unique_constraint(
        "uq_payment_attempts_gateway_refund_id",
        "payment_attempts",
        ["gateway_refund_id"],
        schema="payments",
    )


def downgrade() -> None:
    op.drop_constraint(
        "uq_payment_attempts_gateway_refund_id",
        "payment_attempts",
        schema="payments",
        type_="unique",
    )

    op.drop_constraint(
        "uq_payment_attempts_merchant_refund_id",
        "payment_attempts",
        schema="payments",
        type_="unique",
    )

    op.drop_column(
        "payment_attempts",
        "gateway_refund_id",
        schema="payments",
    )

    op.drop_column(
        "payment_attempts",
        "merchant_refund_id",
        schema="payments",
    )