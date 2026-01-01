from datetime import datetime, timedelta, timezone
from sqlalchemy.orm import Session
from sqlalchemy import select

from app.core.database import SessionLocal
from app.modules.orders.models import Order
from app.modules.orders.constants import OrderStatus
from app.modules.notifications.service import NotificationService


def run_executor():
    db: Session = SessionLocal()

    try:
        now = datetime.now(timezone.utc)
        promote_time = now + timedelta(minutes=45)

        # 1️⃣ Promote scheduled → incoming
        scheduled_orders = db.execute(
            select(Order)
            .where(
                Order.order_type == "SCHEDULED",
                Order.order_status == OrderStatus.SCHEDULED,
                Order.scheduled_time <= promote_time,
                Order.scheduled_time > now,
            )
        ).scalars().all()

        for order in scheduled_orders:
            order.order_status = OrderStatus.INCOMING
            NotificationService.notify_vendor_incoming(
                db,
                order.order_id,
                order.branch_id,
            )

        # 2️⃣ Expire missed orders
        expired_orders = db.execute(
            select(Order)
            .where(
                Order.order_type == "SCHEDULED",
                Order.order_status == OrderStatus.INCOMING,
                Order.scheduled_time <= now,
            )
        ).scalars().all()

        for order in expired_orders:
            order.order_status = OrderStatus.EXPIRED
            NotificationService.notify_order_expired(
                db,
                order.order_id,
                order.user_id,
            )

        db.commit()

    except Exception as e:
        db.rollback()
        print("Scheduler error:", e)

    finally:
        db.close()
