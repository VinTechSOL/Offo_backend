from sqlalchemy.orm import Session
from app.modules.cart.repository import CartRepository
from app.modules.orders.repository import OrderRepository
from app.modules.orders.constants import OrderStatus
from app.modules.orders.models import Order
from datetime import timedelta
from datetime import datetime
from fastapi import HTTPException

def build_scheduled_datetime(scheduled_date, scheduled_time):
    if not scheduled_date or not scheduled_time:
        return None

    time_obj = datetime.strptime(scheduled_time, "%I:%M %p").time()
    return datetime.combine(scheduled_date, time_obj)


class OrderService:

    @staticmethod
    def place_order(db: Session, user_id: int, data):
        cart = CartRepository.get_active_cart(db, user_id)

        if not cart:
            raise ValueError("No active cart")

        cart_items = CartRepository.get_cart_items(db, cart.cart_id)

        if not cart_items:
            raise ValueError("Cart is empty")

        total_amount = sum(
            item.price_at_time * item.quantity for item in cart_items
        )

        order_status = "CREATED" if data.order_type == "INSTANT" else "SCHEDULED"

        order = Order(
            user_id=user_id,
            cafe_id=cart.branch_id,   # later replace with real cafe lookup
            branch_id=cart.branch_id,
            order_type=data.order_type,
            scheduled_time = build_scheduled_datetime(
                data.scheduled_date,
                data.scheduled_time
            ),
            total_amount=total_amount,
            order_status=order_status,
            payment_status="PENDING",
            repeat_weekly=data.repeat_weekly,
            repeat_remaining=3 if data.repeat_weekly else 0
        )

        OrderRepository.create_order(db, order)
        OrderRepository.add_order_items(db, order.order_id, cart_items)

        CartRepository.mark_cart_checked_out(db, cart)

        db.commit()
        return order
    


    @staticmethod
    def handle_repeat_weekly(db: Session, order: Order):
        if not order.repeat_weekly or not order.repeat_remaining:
            return

        if order.repeat_remaining <= 0:
            return

        new_order = Order(
            user_id=order.user_id,
            cafe_id=order.cafe_id,
            branch_id=order.branch_id,
            order_type="SCHEDULED",
            scheduled_time=order.scheduled_time + timedelta(days=7),
            total_amount=order.total_amount,
            order_status="SCHEDULED",
            payment_status="PENDING",
            repeat_weekly=True,
            repeat_remaining=order.repeat_remaining - 1,
        )

        db.add(new_order)


class VendorOrderService:

    @staticmethod
    def accept_order(db: Session, order_id: int, branch_id: int):
        order = OrderRepository.get_order(db, order_id)

        if not order or order.branch_id != branch_id:
            raise HTTPException(404, "Order not found")

        if order.order_status != OrderStatus.INCOMING:
            raise HTTPException(400, "Order not ready to accept")

        return OrderRepository.update_status(
            db, order, OrderStatus.ACCEPTED
        )

    @staticmethod
    def reject_order(db: Session, order_id: int, branch_id: int):
        order = OrderRepository.get_order(db, order_id)

        if not order or order.branch_id != branch_id:
            raise HTTPException(404, "Order not found")

        if order.order_status != OrderStatus.INCOMING:
            raise HTTPException(400, "Order not ready to reject")

        return OrderRepository.update_status(
            db, order, OrderStatus.REJECTED
        )

    @staticmethod
    def move_order(db: Session, order_id: int, branch_id: int, next_status: str):
        order = OrderRepository.get_order(db, order_id)

        if not order or order.branch_id != branch_id:
            raise HTTPException(404, "Order not found")

        valid_transitions = {
            OrderStatus.ACCEPTED: OrderStatus.PREPARING,
            OrderStatus.PREPARING: OrderStatus.READY,
            OrderStatus.READY: OrderStatus.PICKED_UP,
            OrderStatus.PICKED_UP: OrderStatus.COMPLETED,
        }

        if order.order_status not in valid_transitions:
            raise HTTPException(400, "Invalid order state")

        if valid_transitions[order.order_status] != next_status:
            raise HTTPException(400, "Invalid transition")

        return OrderRepository.update_status(db, order, next_status)
