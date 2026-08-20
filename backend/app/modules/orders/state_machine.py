from app.modules.orders.constants import OrderStatus


# ============================================================
# NORMAL VENDOR ORDER FLOW
# ============================================================

VALID_TRANSITIONS = {
    OrderStatus.CREATED: {
        OrderStatus.PREPARING,
        OrderStatus.REJECTED,
        OrderStatus.CANCELLED,
    },

    OrderStatus.PREPARING: {
        OrderStatus.READY,
    },

    OrderStatus.READY: {
        OrderStatus.PICKED_UP,
    },

    # PICKED_UP is immediately converted to COMPLETED
    # by VendorOrderService.move_order().
    OrderStatus.PICKED_UP: {
        OrderStatus.COMPLETED,
    },

    OrderStatus.REJECTED: set(),
    OrderStatus.CANCELLED: set(),
    OrderStatus.COMPLETED: set(),
}


def can_transition(
    current: OrderStatus,
    next_status: OrderStatus,
) -> bool:
    """
    Return True when the requested order transition is valid.
    """

    allowed = VALID_TRANSITIONS.get(current, set())

    return next_status in allowed