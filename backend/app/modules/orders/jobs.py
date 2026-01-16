# app/modules/orders/jobs.py

from datetime import datetime, timedelta, timezone
from sqlalchemy import inspect

from app.core.database import SessionLocal
from app.modules.orders.models import Order
from app.modules.orders.constants import OrderStatus
from app.modules.notifications.service import NotificationService
from app.modules.notifications.constants import (
    NotificationEvent,
    NotificationRecipient,
    NotificationPriority,
)

# ---------------------------------
# Helper: check column exists safely
# ---------------------------------
def column_exists(model, column_name: str) -> bool:
    return column_name in inspect(model).columns


# ---------------------------------
# Job 1: Scheduled order visibility
# ---------------------------------
def scheduled_order_visibility_job():
    db = SessionLocal()
    try:
        now = datetime.now(timezone.utc)
        window = now + timedelta(minutes=60)

        orders = db.query(Order).filter(
            Order.order_type == "SCHEDULED",
            Order.order_status == OrderStatus.CREATED,
            Order.scheduled_time <= window,
        ).all()

        print(f"👀 Visibility job ran — {len(orders)} orders")
    except Exception as e:
        print("❌ Visibility job error:", e)
    finally:
        db.close()


# ---------------------------------
# Job 2: Reminder job (SAFE)
# ---------------------------------
def scheduled_order_reminder_job():
    db = SessionLocal()
    try:
        if not column_exists(Order, "reminder_sent"):
            print("⚠️ reminder_sent column missing — skipping reminder job")
            return

        now = datetime.now(timezone.utc)
        window = now + timedelta(minutes=30)

        orders = db.query(Order).filter(
            Order.order_type == "SCHEDULED",
            Order.order_status == OrderStatus.CREATED,
            Order.scheduled_time <= window,
            Order.reminder_sent.is_(False),
        ).all()

        for order in orders:
            NotificationService.trigger(
                db=db,
                event=NotificationEvent.ORDER_PLACED,
                recipient_type=NotificationRecipient.STAFF,
                recipient_id=order.branch_id,
                title="Scheduled order reminder",
                message=f"Order #{order.order_id} scheduled soon",
                priority=NotificationPriority.MEDIUM,
                order_id=order.order_id,
            )
            order.reminder_sent = True

        db.commit()
        print(f"🔔 Reminder job ran — {len(orders)} notifications sent")
    except Exception as e:
        print("❌ Reminder job error:", e)
        db.rollback()
    finally:
        db.close()


# ---------------------------------
# Job 3: Expiry job
# ---------------------------------
def scheduled_order_expiry_job():
    db = SessionLocal()
    try:
        now = datetime.now(timezone.utc)

        expired = db.query(Order).filter(
            Order.order_type == "SCHEDULED",
            Order.order_status == OrderStatus.CREATED,
            Order.scheduled_time < now - timedelta(minutes=5),
        ).all()

        for order in expired:
            order.order_status = OrderStatus.EXPIRED

        db.commit()
        print(f"⏰ Expiry job ran — {len(expired)} orders expired")
    except Exception as e:
        print("❌ Expiry job error:", e)
        db.rollback()
    finally:
        db.close()
