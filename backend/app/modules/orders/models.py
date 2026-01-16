from sqlalchemy.orm import Mapped, mapped_column
from sqlalchemy import (
    BigInteger, Integer, Numeric, String,
    DateTime, ForeignKey,Boolean,Column
)
from datetime import datetime, timezone
from app.core.database import Base


class Order(Base):
    __tablename__ = "orders"
    __table_args__ = {"schema": "orders"}

    order_id: Mapped[int] = mapped_column(BigInteger, primary_key=True)

    user_id: Mapped[int] = mapped_column(Integer, nullable=False)
    cafe_id: Mapped[int] = mapped_column(Integer, nullable=False)
    branch_id: Mapped[int] = mapped_column(Integer, nullable=False)

    order_type: Mapped[str] = mapped_column(String(20), nullable=False)
    scheduled_time: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))

    total_amount: Mapped[float] = mapped_column(Numeric(10, 2), nullable=False)
    order_status: Mapped[str] = mapped_column(String(30), nullable=False)
    payment_status: Mapped[str] = mapped_column(String(30), nullable=False)

    repeat_weekly: Mapped[bool] = mapped_column(default=False)
    repeat_remaining: Mapped[int | None] = mapped_column(nullable=True)

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(timezone.utc)
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(timezone.utc),
        onupdate=lambda: datetime.now(timezone.utc)
    )
    reminder_sent = Column(Boolean, default=False, nullable=False)


class OrderItem(Base):
    __tablename__ = "order_items"
    __table_args__ = {"schema": "orders"}

    order_item_id: Mapped[int] = mapped_column(BigInteger, primary_key=True)
    order_id: Mapped[int] = mapped_column(
        BigInteger,
        ForeignKey("orders.orders.order_id", ondelete="CASCADE"),
        nullable=False
    )

    item_id: Mapped[int] = mapped_column(Integer, nullable=False)
    quantity: Mapped[int] = mapped_column(Integer, nullable=False)
    price_at_time: Mapped[float] = mapped_column(Numeric(10, 2), nullable=False)


class OrderStatusLog(Base):
    __tablename__ = "order_status_logs"
    __table_args__ = {"schema": "orders"}

    id: Mapped[int] = mapped_column(Integer, primary_key=True)

    order_id: Mapped[int] = mapped_column(
        ForeignKey("orders.orders.order_id", ondelete="CASCADE"),
        nullable=False
    )

    status: Mapped[str] = mapped_column(String(30), nullable=False)

    changed_by: Mapped[str] = mapped_column(String(20), nullable=False)
    changed_by_id: Mapped[int | None] = mapped_column(Integer)

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(timezone.utc),
    )