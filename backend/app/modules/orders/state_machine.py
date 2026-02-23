from app.modules.orders.constants import OrderStatus

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
    OrderStatus.PICKED_UP: {
        OrderStatus.COMPLETED,
    },

    OrderStatus.REJECTED: set(),
    OrderStatus.CANCELLED: set(),
    OrderStatus.COMPLETED: set(),
}
