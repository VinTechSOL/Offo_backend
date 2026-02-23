from fastapi import HTTPException
from datetime import timedelta
from app.modules.orders.constants import OrderStatus
from app.modules.orders.state_machine import VALID_TRANSITIONS
from app.core.time_utils import now_utc


# ---------------------------------------------------
# State Machine Validation
# ---------------------------------------------------

def validate_transition(current: OrderStatus, next_: OrderStatus):
    allowed = VALID_TRANSITIONS.get(current, set())

    if next_ not in allowed:
        raise HTTPException(
            status_code=400,
            detail=f"Invalid transition {current} → {next_}"
        )


# ---------------------------------------------------
# Scheduled Order Visibility Rule
# ---------------------------------------------------

def validate_scheduled_visibility(order, visibility_window_minutes: int = 60):
    """
    Scheduled orders should only be actionable
    within X minutes before scheduled_time.
    """

    if order.order_type != "SCHEDULED":
        return

    if not order.scheduled_time:
        return

    now = now_utc()

    visible_from = order.scheduled_time - timedelta(minutes=visibility_window_minutes)

    if now < visible_from:
        raise HTTPException(
            status_code=400,
            detail="Scheduled order not yet available for action"
        )