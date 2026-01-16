from app.modules.orders.constants import OrderStatus

VALID_TRANSITIONS = {
    OrderStatus.CREATED: {
        OrderStatus.ACCEPTED,
        OrderStatus.REJECTED,
    },
    OrderStatus.ACCEPTED: {
        OrderStatus.PREPARING,
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
}
