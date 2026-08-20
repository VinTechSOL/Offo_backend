from datetime import timedelta

from sqlalchemy.orm import Session

from app.core.database import SessionLocal
from app.core.time_utils import now_utc
from app.modules.orders.models import Order
from app.modules.orders.constants import OrderStatus

from app.modules.notifications.service import NotificationService
from app.modules.notifications.constants import (
    NotificationEvent,
    NotificationRecipient,
    NotificationPriority,
)


REMINDER_WINDOW_MINUTES = 30


def scheduled_order_reminder_job():
    """
    Notify staff about scheduled orders approaching
    their scheduled time.

    Reminder is sent only once.
    """

    db: Session = SessionLocal()

    try:
        now = now_utc()
        window = now + timedelta(minutes=REMINDER_WINDOW_MINUTES)

        orders = (
            db.query(Order)
            .filter(
                Order.order_type == "SCHEDULED",
                Order.order_status == OrderStatus.CREATED,
                Order.payment_status == "PAID",
                Order.scheduled_time <= window,
                Order.scheduled_time > now,
                Order.reminder_sent.is_(False),
            )
            .all()
        )

        for order in orders:

            NotificationService.trigger(
                db=db,
                event=NotificationEvent.ORDER_PLACED,
                recipient_type=NotificationRecipient.STAFF,
                recipient_id=order.branch_id,
                title="Scheduled order reminder",
                message=(
                    f"Order #{order.order_id} "
                    f"is scheduled within 30 minutes"
                ),
                priority=NotificationPriority.MEDIUM,
                order_id=order.order_id,
            )

            order.reminder_sent = True

        db.commit()

        print(
            f"🔔 Scheduled reminder job ran — "
            f"{len(orders)} notifications sent"
        )

    except Exception:
        db.rollback()
        raise

    finally:
        db.close()