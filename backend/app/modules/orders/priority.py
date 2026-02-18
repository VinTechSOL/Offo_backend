from datetime import datetime, timedelta, timezone
from app.core.time_utils import now_utc



class OrderPriority:
    HIGH = "HIGH"
    NORMAL = "NORMAL"
    LOW = "LOW"
    EXPIRED = "EXPIRED"


def calculate_priority(order):
    now = now_utc()

    # ---------------------------
    # INSTANT ORDERS
    # ---------------------------
    if order.order_type == "INSTANT":
        if not order.created_at:
            return OrderPriority.NORMAL

        minutes_since_created = (
            now - order.created_at
        ).total_seconds() / 60

        if minutes_since_created > 20:
            return OrderPriority.EXPIRED

        return OrderPriority.NORMAL


    # ---------------------------
    # SCHEDULED ORDERS
    # ---------------------------
    if order.order_type == "SCHEDULED":

        if not order.scheduled_time:
            return OrderPriority.NORMAL

        minutes_diff = (
            order.scheduled_time - now
        ).total_seconds() / 60

        # Expire 5 mins after scheduled time
        if minutes_diff < -5:
            return OrderPriority.EXPIRED

        # Within 60 mins window
        if 0 <= minutes_diff <= 60:
            return OrderPriority.HIGH

        return OrderPriority.LOW

    return OrderPriority.NORMAL
