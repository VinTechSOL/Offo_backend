from sqlalchemy.orm import Mapped, mapped_column, relationship
from sqlalchemy import BigInteger, String, Numeric, DateTime, ForeignKey,Integer,JSON
from datetime import datetime, timezone

from app.core.database import Base


class PaymentIntent(Base):
    __tablename__ = "payment_intents"
    __table_args__ = {"schema": "payments"}

    intent_id: Mapped[int] = mapped_column(BigInteger, primary_key=True)
    order_id: Mapped[int] = mapped_column(
        BigInteger,
        ForeignKey("orders.orders.order_id", ondelete="CASCADE"),
        unique=True,
        nullable=False,
    )

    amount: Mapped[float] = mapped_column(Numeric(10, 2), nullable=False)
    currency: Mapped[str] = mapped_column(String(10), default="INR")
    status: Mapped[str] = mapped_column(String(20), nullable=False)

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(timezone.utc),
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(timezone.utc),
    )

    attempts = relationship(
        "PaymentAttempt",
        back_populates="intent",
        lazy="selectin",
    )




class PaymentAttempt(Base):
    __tablename__ = "payment_attempts"
    __table_args__ = {"schema": "payments"}

    attempt_id: Mapped[int] = mapped_column(BigInteger, primary_key=True)

    intent_id: Mapped[int] = mapped_column(
        BigInteger,
        ForeignKey("payments.payment_intents.intent_id", ondelete="CASCADE"),
        nullable=False,
    )

    parent_payment_id: Mapped[int | None] = mapped_column(
    BigInteger,
    ForeignKey("payments.payment_attempts.attempt_id"),
    nullable=True,
    )

    gateway: Mapped[str] = mapped_column(String(20), nullable=False)
    # OFFO merchant order id sent to PhonePe
    merchant_order_id: Mapped[str | None] = mapped_column(
        String(100),
        unique=True,
    )

    # PhonePe generated order id
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
    

    attempt_number: Mapped[int] = mapped_column(Integer, nullable=False)
    status: Mapped[str] = mapped_column(String(20), nullable=False)

    request_payload: Mapped[dict | None] = mapped_column(JSON)
    response_payload: Mapped[dict | None] = mapped_column(JSON)

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(timezone.utc),
    )
    completed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))

    intent = relationship("PaymentIntent", back_populates="attempts")
