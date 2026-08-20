"""add support tickets and feedback

Revision ID: 4367c61a8aaa
Revises: f0b4c5cd6f88
Create Date: 2026-08-20 12:01:32.573694

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '4367c61a8aaa'
down_revision: Union[str, Sequence[str], None] = 'f0b4c5cd6f88'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # Create support schema
    op.execute("CREATE SCHEMA IF NOT EXISTS support")

    # -------------------------
    # Tickets
    # -------------------------
    op.create_table(
        "tickets",
        sa.Column(
            "ticket_id",
            sa.BigInteger(),
            primary_key=True,
            nullable=False,
        ),
        sa.Column(
            "user_id",
            sa.Integer(),
            nullable=False,
        ),
        sa.Column(
            "order_id",
            sa.BigInteger(),
            nullable=False,
        ),
        sa.Column(
            "order_item_id",
            sa.BigInteger(),
            nullable=True,
        ),
        sa.Column(
            "issue_type",
            sa.String(length=50),
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
            ["order_id"],
            ["orders.orders.order_id"],
            ondelete="CASCADE",
        ),
        sa.ForeignKeyConstraint(
            ["order_item_id"],
            ["orders.order_items.order_item_id"],
            ondelete="SET NULL",
        ),
        schema="support",
    )

    # Ticket indexes
    op.create_index(
        "ix_support_tickets_user_id",
        "tickets",
        ["user_id"],
        schema="support",
    )

    op.create_index(
        "ix_support_tickets_order_id",
        "tickets",
        ["order_id"],
        schema="support",
    )

    op.create_index(
        "ix_support_tickets_order_item_id",
        "tickets",
        ["order_item_id"],
        schema="support",
    )

    op.create_index(
        "ix_support_tickets_status",
        "tickets",
        ["status"],
        schema="support",
    )

    # -------------------------
    # Feedback
    # -------------------------
    op.create_table(
        "feedback",
        sa.Column(
            "feedback_id",
            sa.BigInteger(),
            primary_key=True,
            nullable=False,
        ),
        sa.Column(
            "user_id",
            sa.Integer(),
            nullable=False,
        ),
        sa.Column(
            "order_id",
            sa.BigInteger(),
            nullable=False,
        ),
        sa.Column(
            "food_rating",
            sa.Integer(),
            nullable=False,
        ),
        sa.Column(
            "app_rating",
            sa.Integer(),
            nullable=False,
        ),
        sa.Column(
            "comments",
            sa.Text(),
            nullable=True,
        ),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.func.now(),
        ),
        sa.ForeignKeyConstraint(
            ["order_id"],
            ["orders.orders.order_id"],
            ondelete="CASCADE",
        ),
        schema="support",
    )

    # Feedback indexes
    op.create_index(
        "ix_support_feedback_user_id",
        "feedback",
        ["user_id"],
        schema="support",
    )

    op.create_index(
        "ix_support_feedback_order_id",
        "feedback",
        ["order_id"],
        schema="support",
    )


def downgrade() -> None:
    # Feedback
    op.drop_index(
        "ix_support_feedback_order_id",
        table_name="feedback",
        schema="support",
    )

    op.drop_index(
        "ix_support_feedback_user_id",
        table_name="feedback",
        schema="support",
    )

    op.drop_table(
        "feedback",
        schema="support",
    )

    # Tickets
    op.drop_index(
        "ix_support_tickets_status",
        table_name="tickets",
        schema="support",
    )

    op.drop_index(
        "ix_support_tickets_order_item_id",
        table_name="tickets",
        schema="support",
    )

    op.drop_index(
        "ix_support_tickets_order_id",
        table_name="tickets",
        schema="support",
    )

    op.drop_index(
        "ix_support_tickets_user_id",
        table_name="tickets",
        schema="support",
    )

    op.drop_table(
        "tickets",
        schema="support",
    )

    # Drop schema
    op.execute("DROP SCHEMA IF EXISTS support")