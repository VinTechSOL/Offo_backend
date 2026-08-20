from datetime import timedelta

from fastapi import HTTPException

from app.modules.orders.constants import OrderStatus
from app.modules.orders.state_machine import VALID_TRANSITIONS
from app.core.time_utils import now_utc


# ============================================================
# STATE MACHINE
# ============================================================

def validate_transition(
    current: OrderStatus,
    next_: OrderStatus,
):
    """
    Validate a normal order-state transition.
    """

    allowed = VALID_TRANSITIONS.get(current, set())

    if next_ not in allowed:
        raise HTTPException(
            status_code=400,
            detail=(
                f"Invalid transition "
                f"{current.value} → {next_.value}"
            ),
        )


# ============================================================
# SCHEDULED ORDER VISIBILITY
# ============================================================

def validate_scheduled_visibility(
    order,
    visibility_window_minutes: int = 60,
):
    """
    Scheduled orders become actionable only inside
    the vendor visibility window.

    Example:

        scheduled time = 1:00 PM
        visibility = 60 minutes

        vendor can act from 12:00 PM onward.
    """

    if order.order_type != "SCHEDULED":
        return

    if not order.scheduled_time:
        return

    now = now_utc()

    visible_from = (
        order.scheduled_time
        - timedelta(minutes=visibility_window_minutes)
    )

    if now < visible_from:
        raise HTTPException(
            status_code=400,
            detail="Scheduled order not yet available for action",
        )


# ============================================================
# USER CANCELLATION
# ============================================================

def validate_user_cancellation(order):
    """
    User cancellation is allowed only while the order
    is still CREATED.

    Once preparation starts, the customer cannot cancel.
    """

    current = OrderStatus(order.order_status)

    if current != OrderStatus.CREATED:
        raise HTTPException(
            status_code=400,
            detail=(
                "Order can only be cancelled "
                "before preparation starts"
            ),
        )


# ============================================================
# REFUND ELIGIBILITY
# ============================================================

def user_cancel_refund_eligible(order) -> bool:
    """
    Determine whether a user cancellation qualifies
    for a refund.

    Current MVP rule:

        CREATED + PAID
            → refund eligible

        PREPARING or later
            → no refund
    """

    current = OrderStatus(order.order_status)

    return current == OrderStatus.CREATED