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


# =========================================================
# USER SUPPORT TICKETS
# =========================================================
# Existing User -> Admin support system.
# DO NOT CHANGE THE EXISTING REQUIRED FIELDS.
# =========================================================

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
# USER TICKET MESSAGES
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
# VENDOR SUPPORT TICKETS
# =========================================================
# Vendor -> Admin support system.
#
# This is intentionally separate from Ticket.
# Existing customer support constraints remain untouched.
# =========================================================

class VendorTicket(Base):
    __tablename__ = "vendor_tickets"
    __table_args__ = {"schema": "support"}

    vendor_ticket_id: Mapped[int] = mapped_column(
        BigInteger,
        primary_key=True,
    )

    # Staff account that created the ticket.
    vendor_staff_id: Mapped[int] = mapped_column(
        Integer,
        nullable=False,
        index=True,
    )

    # Optional because a vendor ticket may not be related
    # to a specific order.
    #
    # Example:
    # - App bug
    # - Menu issue
    # - Settlement issue
    # - General operations
    affected_order_ids: Mapped[str | None] = mapped_column(
        Text,
        nullable=True,
    )

    category: Mapped[str] = mapped_column(
        String(100),
        nullable=False,
    )

    severity: Mapped[str] = mapped_column(
        String(20),
        nullable=False,
    )

    subject: Mapped[str] = mapped_column(
        String(255),
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
# VENDOR TICKET MESSAGES
# =========================================================
# Vendor <-> Admin conversation.
# =========================================================

class VendorTicketMessage(Base):
    __tablename__ = "vendor_ticket_messages"
    __table_args__ = {"schema": "support"}

    message_id: Mapped[int] = mapped_column(
        BigInteger,
        primary_key=True,
    )

    vendor_ticket_id: Mapped[int] = mapped_column(
        BigInteger,
        ForeignKey(
            "support.vendor_tickets.vendor_ticket_id",
            ondelete="CASCADE",
        ),
        nullable=False,
        index=True,
    )

    # VENDOR / ADMIN
    sender_type: Mapped[str] = mapped_column(
        String(20),
        nullable=False,
    )

    # vendor_staff_id or staff_id depending on sender_type
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