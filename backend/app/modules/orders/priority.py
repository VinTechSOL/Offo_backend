from datetime import datetime, timedelta, timezone

VISIBLE_BEFORE_MINUTES = 60
GRACE_MINUTES = 5


class OrderPriority:
    HIGH = "HIGH"
    NORMAL = "NORMAL"
    LOW = "LOW"
    EXPIRED = "EXPIRED"


def calculate_priority(order):
    """
    Runtime-only priority logic.
    NO DB state changes here.
    """

    if order.order_type != "SCHEDULED":
        return OrderPriority.HIGH  # instant orders always top

    if not order.scheduled_time:
        return OrderPriority.NORMAL

    now = datetime.now(timezone.utc)

    minutes_diff = (order.scheduled_time - now).total_seconds() / 60

    if minutes_diff < -GRACE_MINUTES:
        return OrderPriority.EXPIRED

    if -GRACE_MINUTES <= minutes_diff <= VISIBLE_BEFORE_MINUTES:
        return OrderPriority.HIGH

    return OrderPriority.LOW
