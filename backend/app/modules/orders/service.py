from sqlalchemy.orm import Session
from app.modules.cart.repository import CartRepository
from app.modules.vendor.models import CafeBranch
from app.modules.orders.repository import OrderRepository
from app.modules.orders.constants import OrderStatus
from app.modules.orders.models import Order
from app.modules.orders.validators import (validate_transition,validate_scheduled_visibility,)
from app.modules.staff.access_control import validate_branch_access
from app.modules.orders.priority import OrderPriority,calculate_priority
from app.modules.notifications.service import NotificationService
from app.modules.notifications.constants import (
    NotificationEvent,
    NotificationRecipient,
    NotificationPriority,
)
from datetime import timedelta,datetime,timezone
from datetime import datetime
from fastapi import HTTPException
from app.core.time_utils import ist_to_utc,now_utc


def build_scheduled_datetime(scheduled_date, scheduled_time):
    
    if not scheduled_date or not scheduled_time:
        return None

    time_obj = datetime.strptime(scheduled_time, "%I:%M %p").time()
    dt = datetime.combine(scheduled_date, time_obj)

    return ist_to_utc(dt)


class OrderService:

    @staticmethod
    def place_order(db: Session, user_id: int, data):
        print(f"🛒 [ORDER] User {user_id} placing order")
        cart = CartRepository.get_active_cart(db, user_id)

        if not cart:
            print("* [ORDER] No active cart")
            raise HTTPException(status_code=400, detail="No active cart")

        cart_items = CartRepository.get_cart_items(db, cart.cart_id)

        if not cart_items:
            raise HTTPException(status_code=400, detail="Cart is empty")
        
        for item in cart_items:
            branch_item = CartRepository.get_branch_item(
               db, cart.branch_id, item.item_id
            )
            if not branch_item:
               raise HTTPException(400, "Item unavailable")

        subtotal = sum(
            item.price_at_time * item.quantity
            for item in cart_items
        ) 
        convenience_fee = 6

        total_amount = subtotal + convenience_fee

        scheduled_dt = build_scheduled_datetime(
            data.scheduled_date,
            data.scheduled_time
        )

        branch = db.get(CafeBranch, cart.branch_id)

        if not branch:
            raise HTTPException(400, "Invalid branch")

        order = Order(
            user_id=user_id,
            cafe_id=branch.cafe_id,     # TODO: replace with real cafe_id
            branch_id=cart.branch_id,
            order_type=data.order_type,
            scheduled_time=scheduled_dt,
            total_amount=total_amount,
            order_status=OrderStatus.CREATED,   # ✅ always CREATED
            payment_status="PENDING",
            repeat_weekly=data.repeat_weekly,
            repeat_remaining=3 if data.repeat_weekly else 0,
        )

        OrderRepository.create_order(db, order)
        OrderRepository.add_order_items(db, order.order_id, cart_items)
        OrderRepository.add_status_log(
            db,
            order_id=order.order_id,
            status=OrderStatus.CREATED,
            changed_by="USER",
            changed_by_id=user_id,
        )


        CartRepository.mark_cart_checked_out(db, cart)

        
        db.commit()
        db.refresh(order)

        print(
            f"##[ORDER CREATED] order_id={order.order_id} "
            f"branch_id={order.branch_id} type={order.order_type}"
        )

        NotificationService.trigger(
            db=db,
            event=NotificationEvent.ORDER_PLACED,
            recipient_type=NotificationRecipient.STAFF,
            recipient_id=order.branch_id,
            title="New Order Placed",
            message=f"Order #{order.order_id} received",
            priority=NotificationPriority.MEDIUM,
            order_id=order.order_id,
        )

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
        order_status=OrderStatus.CREATED,   # ✅ FIXED
        payment_status="PENDING",
        repeat_weekly=True,
        repeat_remaining=order.repeat_remaining - 1,
       )

       db.add(new_order)


class VendorOrderService:

    @staticmethod
    def accept_order(db: Session, order_id: int, staff):
        order = db.get(Order, order_id)

        if not order:
            raise HTTPException(404, "Order not found")

        # Role-based branch validation
        validate_branch_access(staff, order.branch_id)

        # Scheduled visibility rule
        validate_scheduled_visibility(order)

        # Strict state transition
        validate_transition(
            OrderStatus(order.order_status),
            OrderStatus.PREPARING,
        )

        if calculate_priority(order) == OrderPriority.EXPIRED:
            raise HTTPException(400, "Order expired")

        order.order_status = OrderStatus.PREPARING
        order.updated_at = now_utc()

        OrderRepository.add_status_log(
            db,
            order_id=order.order_id,
            status=OrderStatus.PREPARING,
            changed_by="STAFF",
            changed_by_id=staff.staff_id,
        )

        db.commit()
        db.refresh(order)

    
        # TRIGGER NOTIFICATION 
        NotificationService.trigger(
            db,
            event=NotificationEvent.ORDER_PLACED,
            recipient_type=NotificationRecipient.STAFF,
            recipient_id=order.branch_id,   # branch-level notification
            title="New Order Placed",
            message=f"New order #{order.order_id} received",
            priority=NotificationPriority.MEDIUM,
            order_id=order.order_id,
        )

        return {
            "order_id": order.order_id,
            "status": order.order_status,
        }

    @staticmethod
    def reject_order(db: Session, order_id: int, staff):
        order = db.get(Order, order_id)

        if not order:
            raise HTTPException(404, "Order not found")

        validate_branch_access(staff, order.branch_id)
        validate_scheduled_visibility(order)

        validate_transition(
            OrderStatus(order.order_status),
            OrderStatus.REJECTED,
        )

        order.order_status = OrderStatus.REJECTED
        order.updated_at = now_utc()

        db.commit()
        db.refresh(order)

        return {
            "order_id": order.order_id,
            "status": order.order_status,
        }

    @staticmethod
    def move_order(
        db: Session,
        order_id: int,
        staff,
        next_status: OrderStatus,
    ):
        order = db.get(Order, order_id)

        if not order:
            raise HTTPException(404, "Order not found")

        validate_branch_access(staff, order.branch_id)
        validate_scheduled_visibility(order)
        current = OrderStatus(order.order_status)

        validate_transition(
            current,next_status,
        )

        order.order_status = next_status
        order.updated_at = now_utc()

        OrderRepository.add_status_log(
            db,
            order_id=order.order_id,
            status=next_status,
            changed_by="STAFF",
            changed_by_id=staff.staff_id,
        )


        

        db.commit()
        db.refresh(order)

        return {
            "order_id": order.order_id,
            "status": order.order_status,
        }