"""add platform+ gst

Revision ID: 70b8a871636c
Revises: 17ee1e089af1
Create Date: 2026-08-27 17:16:18.059586

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '70b8a871636c'
down_revision: Union[str, Sequence[str], None] = '17ee1e089af1'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column(
        "payment_intents",
        sa.Column(
            "platform_fee",
            sa.Numeric(10, 2),
            nullable=False,
            server_default="0",
        ),
        schema="payments",
    )

    op.add_column(
        "payment_intents",
        sa.Column(
            "gst",
            sa.Numeric(10, 2),
            nullable=False,
            server_default="0",
        ),
        schema="payments",
    )

    op.add_column(
        "payment_intents",
        sa.Column(
            "checkout_fee",
            sa.Numeric(10, 2),
            nullable=False,
            server_default="0",
        ),
        schema="payments",
    )


def downgrade() -> None:
    op.drop_column(
        "payment_intents",
        "checkout_fee",
        schema="payments",
    )

    op.drop_column(
        "payment_intents",
        "gst",
        schema="payments",
    )

    op.drop_column(
        "payment_intents",
        "platform_fee",
        schema="payments",
    )