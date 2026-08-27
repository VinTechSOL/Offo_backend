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

    order_item_id: Mapped[int | None] = mapped_column(
        BigInteger,
        ForeignKey(
            "orders.order_items.order_item_id",
            ondelete="SET NULL",
        ),
        nullable=True,
        index=True,
    )

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

    status: Mapped[str] = mapped_column(
        String(30),
        nullable=False,
        default=TicketStatus.OPEN,
        index=True,
    )

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


# =========================================================
# TICKET MESSAGES
# =========================================================

class TicketMessage(Base):
    __tablename__ = "ticket_messages"
    __table_args__ = {"schema": "support"}

    message_id: Mapped[int] = mapped_column(
        BigInteger,
        primary_key=True,
    )

    ticket_id: Mapped[int] = mapped_column(
        BigInteger,
        ForeignKey(
            "support.tickets.ticket_id",
            ondelete="CASCADE",
        ),
        nullable=False,
        index=True,
    )

    # USER / ADMIN
    sender_type: Mapped[str] = mapped_column(
        String(20),
        nullable=False,
    )

    # user_id or staff_id depending on sender_type
    sender_id: Mapped[int] = mapped_column(
        Integer,
        nullable=False,
    )

    message: Mapped[str] = mapped_column(
        Text,
        nullable=False,
    )

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        default=lambda: datetime.now(timezone.utc),
    )


# =========================================================
# FEEDBACK
# =========================================================

class Feedback(Base):
    __tablename__ = "feedback"
    __table_args__ = {"schema": "support"}

    feedback_id: Mapped[int] = mapped_column(
        BigInteger,
        primary_key=True,
    )

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

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        default=lambda: datetime.now(timezone.utc),
    )