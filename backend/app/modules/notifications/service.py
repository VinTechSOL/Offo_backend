from app.modules.notifications.constants import (
    NotificationRecipient,
    NotificationChannel,
    NotificationPriority,
    NotificationEvent,
)
from app.modules.notifications.models import Notification
from app.modules.notifications.repository import NotificationRepository 
from sqlalchemy.orm import Session


class NotificationService:

    @staticmethod
    def trigger(
        db: Session,
        *,
        event: NotificationEvent,
        recipient_type: NotificationRecipient,
        recipient_id: int,
        title: str,
        message: str,
        priority: NotificationPriority,
        order_id: int | None = None,
    ):
        print(
            f"🔔 [NOTIFICATION TRIGGER] "
            f"event={event} recipient={recipient_type}({recipient_id}) "
            f"order_id={order_id}"
        )

        channel = NotificationChannel.IN_APP

        if priority == NotificationPriority.HIGH and event in {
            NotificationEvent.ORDER_REJECTED,
            NotificationEvent.ORDER_EXPIRED,
        }:
            channel = NotificationChannel.SMS

        notification = Notification(
            recipient_type=recipient_type,
            recipient_id=recipient_id,
            event_type=event.value,  # 🔥 IMPORTANT
            title=title,
            message=message,
            priority=priority.value,
            channel=channel.value,
            related_order_id=order_id,
        )

        db.add(notification)
        db.commit()
        db.refresh(notification)

        print(
            f"📨 [NOTIFICATION SAVED] "
            f"id={notification.id} recipient_id={recipient_id}"
        )

        return notification

