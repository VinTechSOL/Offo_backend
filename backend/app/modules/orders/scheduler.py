from sqlalchemy.orm import Session
from datetime import timedelta

from app.core.database import SessionLocal
from app.core.time_utils import now_utc

from app.modules.orders.models import Order
from app.modules.orders.constants import (
    OrderStatus,
    PaymentStatus,
)

from app.modules.orders.repository import OrderRepository
from app.modules.orders.payment_service import (
    OrderPaymentService,
)


INSTANT_EXPIRY_MINUTES = 15
SCHEDULED_GRACE_MINUTES = 5


def auto_cancel_runner():

    db: Session = SessionLocal()

    try:
        now = now_utc()

        # -----------------------------------------
        # INSTANT
        # -----------------------------------------

        instant_expiry_time = (
            now - timedelta(
                minutes=INSTANT_EXPIRY_MINUTES
            )
        )

        instant_orders = (
            db.query(Order)
            .filter(
                Order.order_type == "INSTANT",
                Order.order_status == OrderStatus.CREATED,
                Order.created_at < instant_expiry_time,
            )
            .with_for_update()
            .all()
        )

        # -----------------------------------------
        # SCHEDULED
        # -----------------------------------------

        scheduled_expiry_time = (
            now - timedelta(
                minutes=SCHEDULED_GRACE_MINUTES
            )
        )

        scheduled_orders = (
            db.query(Order)
            .filter(
                Order.order_type == "SCHEDULED",
                Order.order_status == OrderStatus.CREATED,
                Order.scheduled_time < scheduled_expiry_time,
            )
            .with_for_update()
            .all()
        )

        expired_orders = (
            instant_orders +
            scheduled_orders
        )

        cancelled_count = 0
        refund_count = 0

        for order in expired_orders:

            # -------------------------------------
            # Cancel order
            # -------------------------------------

            order.order_status = OrderStatus.CANCELLED
            order.updated_at = now

            OrderRepository.add_status_log(
                db,
                order_id=order.order_id,
                status=OrderStatus.CANCELLED,
                changed_by="SYSTEM",
                changed_by_id=None,
            )

            cancelled_count += 1

            # -------------------------------------
            # Paid orders require refund
            # -------------------------------------

            if order.payment_status == PaymentStatus.PAID:

                changed = (
                    OrderPaymentService
                    .mark_refund_pending_in_transaction(
                        db=db,
                        order=order,
                    )
                )

                if changed:
                    refund_count += 1

        db.commit()

        print(
            "⏰ Auto-cancel job — "
            f"cancelled={cancelled_count}, "
            f"refund_pending={refund_count}"
        )

    except Exception as e:

        db.rollback()

        print(
            "❌ Auto-cancel job error:",
            e
        )

    finally:
        db.close()