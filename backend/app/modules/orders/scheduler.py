from sqlalchemy.orm import Session
from datetime import timedelta
from app.modules.orders.repository import OrderRepository
from app.modules.orders.constants import OrderStatus
from app.core.database import SessionLocal
from app.core.time_utils import now_utc


# CONFIG
INSTANT_EXPIRY_MINUTES = 15
SCHEDULED_GRACE_MINUTES = 5


def auto_cancel_runner():
    db: Session = SessionLocal()

    try:
        now = now_utc()

        # --------------------------------------
        # 1️⃣ Cancel INSTANT orders not accepted
        # --------------------------------------
        instant_expiry_time = now - timedelta(minutes=INSTANT_EXPIRY_MINUTES)

        db.query(OrderRepository.OrderModel).filter(
            OrderRepository.OrderModel.order_type == "INSTANT",
            OrderRepository.OrderModel.order_status == OrderStatus.CREATED,
            OrderRepository.OrderModel.created_at < instant_expiry_time
        ).update(
            {
                "order_status": OrderStatus.CANCELLED,
                "updated_at": now
            },
            synchronize_session=False
        )

        # --------------------------------------
        # 2️⃣ Cancel SCHEDULED unaccepted orders
        # --------------------------------------
        scheduled_expiry_time = now - timedelta(minutes=SCHEDULED_GRACE_MINUTES)

        db.query(OrderRepository.OrderModel).filter(
            OrderRepository.OrderModel.order_type == "SCHEDULED",
            OrderRepository.OrderModel.order_status == OrderStatus.CREATED,
            OrderRepository.OrderModel.scheduled_time < scheduled_expiry_time
        ).update(
            {
                "order_status": OrderStatus.CANCELLED,
                "updated_at": now
            },
            synchronize_session=False
        )

        db.commit()

    finally:
        db.close()