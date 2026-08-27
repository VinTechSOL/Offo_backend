"""add refund_order_id & amount to payment attempts table

Revision ID: 17ee1e089af1
Revises: 76c264796daf
Create Date: 2026-08-27 10:12:00.983886

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '17ee1e089af1'
down_revision: Union[str, Sequence[str], None] = '76c264796daf'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:

    # ============================================================
    # 1. ADD AMOUNT
    # ============================================================

    op.add_column(
        "payment_attempts",
        sa.Column(
            "amount",
            sa.Numeric(
                precision=10,
                scale=2,
            ),
            nullable=True,
        ),
        schema="payments",
    )

    # ============================================================
    # 2. BACKFILL EXISTING PAYMENT ATTEMPTS
    #
    # Existing attempts are associated with a PaymentIntent.
    # Copy the PaymentIntent amount into the attempt.
    #
    # This is safe for the existing single-payment attempts.
    # ============================================================

    op.execute(
        """
        UPDATE payments.payment_attempts pa
        SET amount = pi.amount
        FROM payments.payment_intents pi
        WHERE pa.intent_id = pi.intent_id
          AND pa.amount IS NULL
        """
    )

    # ============================================================
    # 3. MAKE AMOUNT REQUIRED
    # ============================================================

    op.alter_column(
        "payment_attempts",
        "amount",
        existing_type=sa.Numeric(
            precision=10,
            scale=2,
        ),
        nullable=False,
        schema="payments",
    )

    # ============================================================
    # 4. ADD REFUND ORDER ID
    # ============================================================

    op.add_column(
        "payment_attempts",
        sa.Column(
            "refund_order_id",
            sa.BigInteger(),
            nullable=True,
        ),
        schema="payments",
    )

    # ============================================================
    # 5. FOREIGN KEY
    # ============================================================

    op.create_foreign_key(
        "fk_payment_attempts_refund_order_id",
        "payment_attempts",
        "orders",
        ["refund_order_id"],
        ["order_id"],
        source_schema="payments",
        referent_schema="orders",
        ondelete="SET NULL",
    )


def downgrade() -> None:

    # ============================================================
    # 1. DROP FOREIGN KEY
    # ============================================================

    op.drop_constraint(
        "fk_payment_attempts_refund_order_id",
        "payment_attempts",
        schema="payments",
        type_="foreignkey",
    )

    # ============================================================
    # 2. DROP REFUND ORDER ID
    # ============================================================

    op.drop_column(
        "payment_attempts",
        "refund_order_id",
        schema="payments",
    )

    # ============================================================
    # 3. DROP AMOUNT
    # ============================================================

    op.drop_column(
        "payment_attempts",
        "amount",
        schema="payments",
    )