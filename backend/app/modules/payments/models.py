from datetime import datetime, timezone

from sqlalchemy import (
    BigInteger,
    String,
    Numeric,
    DateTime,
    ForeignKey,
    Integer,
    JSON,
)
from sqlalchemy.orm import (
    Mapped,
    mapped_column,
    relationship,
)

from app.core.database import Base


class PaymentIntent(Base):
    __tablename__ = "payment_intents"
    __table_args__ = {"schema": "payments"}

    intent_id: Mapped[int] = mapped_column(
        BigInteger,
        primary_key=True,
    )

    # Primary / anchor order for this payment intent.
    #
    # For an instant order:
    #     PaymentIntent → one Order
    #
    # For scheduled checkout:
    #     PaymentIntent → first Order
    #     PaymentIntentOrder → all Orders
    order_id: Mapped[int] = mapped_column(
        BigInteger,
        ForeignKey(
            "orders.orders.order_id",
            ondelete="CASCADE",
        ),
        unique=True,
        nullable=False,
    )

    amount: Mapped[float] = mapped_column(
        Numeric(10, 2),
        nullable=False,
    )

    platform_fee: Mapped[float] = mapped_column(
        Numeric(10, 2),
        nullable=False,
        default=0,
    )

    gst: Mapped[float] = mapped_column(
        Numeric(10, 2),
        nullable=False,
        default=0,
    )

    checkout_fee: Mapped[float] = mapped_column(
        Numeric(10, 2),
        nullable=False,
        default=0,
    )

    currency: Mapped[str] = mapped_column(
        String(10),
        default="INR",
    )

    status: Mapped[str] = mapped_column(
        String(20),
        nullable=False,
    )

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(timezone.utc),
    )

    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(timezone.utc),
    )

    # Original payment attempts
    attempts = relationship(
        "PaymentAttempt",
        back_populates="intent",
        lazy="selectin",
    )

    # Orders included in this payment intent
    payment_orders = relationship(
        "PaymentIntentOrder",
        back_populates="intent",
        cascade="all, delete-orphan",
        lazy="selectin",
    )


class PaymentIntentOrder(Base):
    """
    Associates one PaymentIntent with one or more Orders.

    Example:

        PaymentIntent 5001
            ├── Order 101
            ├── Order 102
            └── Order 103

    This allows multiple scheduled orders to be paid
    through one PhonePe transaction.
    """

    __tablename__ = "payment_intent_orders"
    __table_args__ = {"schema": "payments"}

    id: Mapped[int] = mapped_column(
        BigInteger,
        primary_key=True,
    )

    intent_id: Mapped[int] = mapped_column(
        BigInteger,
        ForeignKey(
            "payments.payment_intents.intent_id",
            ondelete="CASCADE",
        ),
        nullable=False,
    )

    order_id: Mapped[int] = mapped_column(
        BigInteger,
        ForeignKey(
            "orders.orders.order_id",
            ondelete="CASCADE",
        ),
        nullable=False,
        unique=True,
    )

    intent = relationship(
        "PaymentIntent",
        back_populates="payment_orders",
    )


class PaymentAttempt(Base):
    __tablename__ = "payment_attempts"
    __table_args__ = {"schema": "payments"}

    attempt_id: Mapped[int] = mapped_column(
        BigInteger,
        primary_key=True,
    )

    intent_id: Mapped[int] = mapped_column(
        BigInteger,
        ForeignKey(
            "payments.payment_intents.intent_id",
            ondelete="CASCADE",
        ),
        nullable=False,
    )

    parent_payment_id: Mapped[int | None] = mapped_column(
        BigInteger,
        ForeignKey(
            "payments.payment_attempts.attempt_id",
        ),
        nullable=True,
    )

    # ------------------------------------------------------------
    # Order associated with this refund attempt
    #
    # NULL for normal payment attempts.
    #
    # Example:
    #
    # Original payment:
    #     refund_order_id = NULL
    #
    # Refund for Order 102:
    #     refund_order_id = 102
    # ------------------------------------------------------------

    refund_order_id: Mapped[int | None] = mapped_column(
        BigInteger,
        ForeignKey(
            "orders.orders.order_id",
            ondelete="SET NULL",
        ),
        nullable=True,
    )

    gateway: Mapped[str] = mapped_column(
        String(20),
        nullable=False,
    )

    # ------------------------------------------------------------
    # Amount represented by THIS attempt.
    #
    # Normal payment:
    #     ₹954
    #
    # Refund:
    #     ₹318
    # ------------------------------------------------------------

    amount: Mapped[float] = mapped_column(
        Numeric(10, 2),
        nullable=False,
    )

    # OFFO merchant order ID sent to PhonePe
    merchant_order_id: Mapped[str | None] = mapped_column(
        String(100),
        unique=True,
    )

    # PhonePe generated order ID
    phonepe_order_id: Mapped[str | None] = mapped_column(
        String(100),
        unique=True,
    )

    gateway_transaction_id: Mapped[str | None] = mapped_column(
        String(100),
        unique=True,
    )

    merchant_refund_id: Mapped[str | None] = mapped_column(
        String(100),
        unique=True,
    )

    gateway_refund_id: Mapped[str | None] = mapped_column(
        String(100),
        unique=True,
    )

    attempt_number: Mapped[int] = mapped_column(
        Integer,
        nullable=False,
    )

    status: Mapped[str] = mapped_column(
        String(20),
        nullable=False,
    )

    request_payload: Mapped[dict | None] = mapped_column(
        JSON,
    )

    response_payload: Mapped[dict | None] = mapped_column(
        JSON,
    )

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(timezone.utc),
    )

    completed_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True),
    )

    intent = relationship(
        "PaymentIntent",
        back_populates="attempts",
    )



