from sqlalchemy.orm import Mapped, mapped_column
from sqlalchemy import String, Boolean, DateTime, Integer,Enum as SQLEnum,ForeignKey
from datetime import datetime, timezone
import enum
from app.core.database import Base

class NotificationRecipient(str, enum.Enum):
    STAFF = "STAFF"
    USER = "USER"

class Notification(Base):
    __tablename__ = "notifications"
    __table_args__ = {"schema": "core"}

    id: Mapped[int] = mapped_column(Integer, primary_key=True)

    recipient_type: Mapped[NotificationRecipient] = mapped_column(
        SQLEnum(NotificationRecipient, name="notification_recipient"),
        nullable=False,
    )
    
    recipient_id: Mapped[int] = mapped_column(Integer, nullable=False)

    event_type: Mapped[str] = mapped_column(String(50))
    title: Mapped[str] = mapped_column(String(255))
    message: Mapped[str] = mapped_column(String(500))

    priority: Mapped[str] = mapped_column(String(10))
    channel: Mapped[str] = mapped_column(String(10))

    related_order_id: Mapped[int | None]

    is_read: Mapped[bool] = mapped_column(Boolean, default=False)

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(timezone.utc),
    )
