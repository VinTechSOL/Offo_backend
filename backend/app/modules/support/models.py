from datetime import datetime, timezone

from sqlalchemy import (
    BigInteger,
    Integer,
    String,
    Text,
    DateTime,
    ForeignKey,
)
from sqlalchemy.orm import Mapped, mapped_column

from app.core.database import Base

from app.modules.support.constants import (
    TicketStatus,
    TicketIssueType,
)


class Ticket(Base):
    __tablename__ = "tickets"
    __table_args__ = {"schema": "support"}

    ticket_id: Mapped[int] = mapped_column(
        BigInteger,
        primary_key=True,
    )

    # -------------------------
    # Ownership
    # -------------------------

    user_id: Mapped[int] = mapped_column(
        Integer,
        nullable=False,
        index=True,
    )

    order_id: Mapped[int] = mapped_column(
        BigInteger,
        ForeignKey(
            "orders.orders.order_id",
            ondelete="CASCADE",
        ),
        nullable=False,
        index=True,
    )

    # -------------------------
    # Optional ordered item
    # -------------------------

    order_item_id: Mapped[int | None] = mapped_column(
        BigInteger,
        ForeignKey(
            "orders.order_items.order_item_id",
            ondelete="SET NULL",
        ),
        nullable=True,
        index=True,
    )

    # -------------------------
    # Issue
    # -------------------------

    issue_type: Mapped[str] = mapped_column(
        String(50),
        nullable=False,
    )

    description: Mapped[str] = mapped_column(
        Text,
        nullable=False,
    )

    image_url: Mapped[str | None] = mapped_column(
        String(500),
        nullable=True,
    )

    # -------------------------
    # Status
    # -------------------------

    status: Mapped[str] = mapped_column(
        String(30),
        nullable=False,
        default=TicketStatus.OPEN,
        index=True,
    )

    # -------------------------
    # Timestamps
    # -------------------------

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        default=lambda: datetime.now(timezone.utc),
    )

    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        default=lambda: datetime.now(timezone.utc),
        onupdate=lambda: datetime.now(timezone.utc),
    )


class Feedback(Base):
    __tablename__ = "feedback"
    __table_args__ = {"schema": "support"}

    feedback_id: Mapped[int] = mapped_column(
        BigInteger,
        primary_key=True,
    )

    # -------------------------
    # Ownership
    # -------------------------

    user_id: Mapped[int] = mapped_column(
        Integer,
        nullable=False,
        index=True,
    )

    order_id: Mapped[int] = mapped_column(
        BigInteger,
        ForeignKey(
            "orders.orders.order_id",
            ondelete="CASCADE",
        ),
        nullable=False,
        index=True,
    )

    # -------------------------
    # Ratings
    # -------------------------

    food_rating: Mapped[int] = mapped_column(
        Integer,
        nullable=False,
    )

    app_rating: Mapped[int] = mapped_column(
        Integer,
        nullable=False,
    )

    comments: Mapped[str | None] = mapped_column(
        Text,
        nullable=True,
    )

    # -------------------------
    # Timestamp
    # -------------------------

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        default=lambda: datetime.now(timezone.utc),
    )