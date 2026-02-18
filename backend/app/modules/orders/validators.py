from fastapi import HTTPException
from datetime import datetime, timezone, timedelta
from app.modules.orders.constants import OrderStatus
from app.modules.orders.state_machine import VALID_TRANSITIONS
from app.core.time_utils import now_utc



def validate_transition(current: OrderStatus, next_: OrderStatus):
    allowed = VALID_TRANSITIONS.get(current, set())
    if next_ not in allowed:
        raise HTTPException(
            status_code=400,
            detail=f"Invalid transition {current} → {next_}"
        )


def validate_scheduled_visibility(order):
    if order.order_type != "SCHEDULED":
        return

    if not order.scheduled_time:
        return

    now = now_utc()

    # Visible 60 minutes before scheduled time
    if order.scheduled_time > now + timedelta(minutes=60):
        raise HTTPException(
            status_code=400,
            detail="Scheduled order not yet available"
        )
