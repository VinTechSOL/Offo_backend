from sqlalchemy.orm import Session
from datetime import datetime, timedelta, timezone
from app.modules.orders.repository import OrderRepository
from app.core.database import SessionLocal

VISIBILITY_WINDOW_MINUTES = 60
GRACE_PERIOD_MINUTES = 5


def scheduled_order_visibility_runner():
    db: Session = SessionLocal()
    try:
        now = datetime.now(timezone.utc)

        # Orders that SHOULD be visible to vendor now
        OrderRepository.mark_visible_for_vendor(
            db,
            window_minutes=VISIBILITY_WINDOW_MINUTES
        )

        # Expire scheduled orders that crossed grace period
        OrderRepository.expire_unaccepted_scheduled_orders(
            db,
            grace_minutes=GRACE_PERIOD_MINUTES
        )

        db.commit()
    finally:
        db.close()
