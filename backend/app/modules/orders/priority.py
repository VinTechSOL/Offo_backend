from app.core.time_utils import now_utc


class OrderPriority:
    HIGH = "HIGH"
    NORMAL = "NORMAL"
    LOW = "LOW"


# Visibility window must match live query window
LIVE_WINDOW_MINUTES = 60


def calculate_priority(order):
    """
    Priority is purely for UI urgency.
    It NEVER changes status.
    It NEVER hides orders.
    """

    now = now_utc()

    # --------------------------------------------------
    # INSTANT ORDERS
    # --------------------------------------------------
    if order.order_type == "INSTANT":

        if not order.created_at:
            return OrderPriority.NORMAL

        minutes_since_created = (
            now - order.created_at
        ).total_seconds() / 60

        # >10 minutes waiting → HIGH
        if minutes_since_created >= 10:
            return OrderPriority.HIGH

        # 5–10 minutes → NORMAL
        if minutes_since_created >= 5:
            return OrderPriority.NORMAL

        # <5 minutes → LOW
        return OrderPriority.LOW

    # --------------------------------------------------
    # SCHEDULED ORDERS
    # --------------------------------------------------
    if order.order_type == "SCHEDULED":

        if not order.scheduled_time:
            return OrderPriority.NORMAL

        minutes_to_scheduled = (
            order.scheduled_time - now
        ).total_seconds() / 60

        # Inside live window (<= 60 mins) → HIGH
        if 0 <= minutes_to_scheduled <= LIVE_WINDOW_MINUTES:
            return OrderPriority.HIGH

        # Within next 2 hours → NORMAL
        if LIVE_WINDOW_MINUTES < minutes_to_scheduled <= 120:
            return OrderPriority.NORMAL

        # More than 2 hours away → LOW
        return OrderPriority.LOW

    return OrderPriority.NORMAL