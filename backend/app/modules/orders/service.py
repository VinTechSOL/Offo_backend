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
from app.core.time_utils import ist_to_utc,now_utc,IST
from datetime import timezone

def build_scheduled_datetime(scheduled_date, scheduled_time):
    if not scheduled_date or not scheduled_time:
        return None

    time_obj = datetime.strptime(scheduled_time, "%I:%M %p").time()

    # Combine as naive
    naive_dt = datetime.combine(scheduled_date, time_obj)

    # Localize to IST
    ist_dt = IST.localize(naive_dt)

    # Convert to UTC
    return ist_dt.astimezone(timezone.utc)


class OrderService:

    @staticmethod
    def place_order(db: Session, user_id: int, data):

        # -------------------------
        # 1️⃣ Validate Cart
        # -------------------------

        cart = CartRepository.get_active_cart(db, user_id)
        if not cart:
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

        # -------------------------
        # 2️⃣ Calculate Total
        # -------------------------

        subtotal = sum(
            item.price_at_time * item.quantity
            for item in cart_items
        )
        convenience_fee = 6
        total_amount = subtotal + convenience_fee

        branch = db.get(CafeBranch, cart.branch_id)
        if not branch:
            raise HTTPException(400, "Invalid branch")

        created_orders: list[Order] = []

        # -------------------------
        # 3️⃣ INSTANT ORDER
        # -------------------------

        if data.order_type == "INSTANT":

            order = Order(
                user_id=user_id,
                cafe_id=branch.cafe_id,
                branch_id=cart.branch_id,
                order_type="INSTANT",
                scheduled_time=None,
                total_amount=total_amount,
                order_status=OrderStatus.CREATED,
                payment_status="PENDING",
            )

            db.add(order)
            db.flush()

            OrderRepository.add_order_items(db, order.order_id, cart_items)

            OrderRepository.add_status_log(
                db,
                order_id=order.order_id,
                status=OrderStatus.CREATED,
                changed_by="USER",
                changed_by_id=user_id,
            )

            created_orders.append(order)

        # -------------------------
        # 4️⃣ SCHEDULED ORDER
        # -------------------------

        elif data.order_type == "SCHEDULED":

            if not data.schedules:
                raise HTTPException(
                    400,
                    "Schedules required for scheduled order"
                )

            for schedule in data.schedules:

                scheduled_dt = build_scheduled_datetime(
                    schedule.scheduled_date,
                    schedule.scheduled_time
                )

                order = Order(
                    user_id=user_id,
                    cafe_id=branch.cafe_id,
                    branch_id=cart.branch_id,
                    order_type="SCHEDULED",
                    scheduled_time=scheduled_dt,
                    total_amount=total_amount,
                    order_status=OrderStatus.CREATED,
                    payment_status="PENDING",
                )

                db.add(order)
                db.flush()

                OrderRepository.add_order_items(
                    db, order.order_id, cart_items
                )

                OrderRepository.add_status_log(
                    db,
                    order_id=order.order_id,
                    status=OrderStatus.CREATED,
                    changed_by="USER",
                    changed_by_id=user_id,
                )

                created_orders.append(order)

                # 🔁 Repeat Weekly
                if data.repeat_weekly:
                    for i in range(1, 4):
                        weekly_dt = scheduled_dt + timedelta(days=7 * i)

                        weekly_order = Order(
                            user_id=user_id,
                            cafe_id=branch.cafe_id,
                            branch_id=cart.branch_id,
                            order_type="SCHEDULED",
                            scheduled_time=weekly_dt,
                            total_amount=total_amount,
                            order_status=OrderStatus.CREATED,
                            payment_status="PENDING",
                        )

                        db.add(weekly_order)
                        db.flush()

                        OrderRepository.add_order_items(
                            db,
                            weekly_order.order_id,
                            cart_items
                        )

                        OrderRepository.add_status_log(
                            db,
                            order_id=weekly_order.order_id,
                            status=OrderStatus.CREATED,
                            changed_by="USER",
                            changed_by_id=user_id,
                        )

                        created_orders.append(weekly_order)

        else:
            raise HTTPException(400, "Invalid order type")

        # -------------------------
        # 5️⃣ Mark Cart Checked Out
        # -------------------------

        CartRepository.mark_cart_checked_out(db, cart)

        db.commit()

        for order in created_orders:
            db.refresh(order)

        # -------------------------
        # 6️⃣ Notify Vendor
        # -------------------------

        for order in created_orders:
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

        # -------------------------
        # 7️⃣ Return Proper Model(s)
        # -------------------------

        if len(created_orders) == 1:
            return created_orders[0]

        return created_orders


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

    @staticmethod
    def cancel_order_by_user(db: Session, order_id: int, user_id: int):

        order = db.get(Order, order_id)

        if not order:
          raise HTTPException(404, "Order not found")
        
        if order.user_id != user_id:
          raise HTTPException(403, "Not allowed")
        
        # Only cancel if still CREATED
        validate_transition(
          OrderStatus(order.order_status),
          OrderStatus.CANCELLED,
        )

        order.order_status = OrderStatus.CANCELLED
        order.updated_at = now_utc()

        OrderRepository.add_status_log(
           db,
           order_id=order.order_id,
           status=OrderStatus.CANCELLED,
           changed_by="USER",
           changed_by_id=user_id,
        )

        db.commit()
        db.refresh(order)

        return {
          "order_id": order.order_id,
          "status": order.order_status,
        }




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

        NotificationService.trigger(
            db=db,
            event=NotificationEvent.ORDER_REJECTED,
            recipient_type=NotificationRecipient.USER,
            recipient_id=order.user_id,
            title="Order Rejected",
            message=f"Order #{order.order_id} was rejected",
            priority=NotificationPriority.HIGH,
            order_id=order.order_id,
        )

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

        # -------------------------
        # USER NOTIFICATIONS
        # -------------------------

        if next_status == OrderStatus.READY:
            NotificationService.trigger(
                db=db,
                event=NotificationEvent.ORDER_READY,
                recipient_type=NotificationRecipient.USER,
                recipient_id=order.user_id,
                title="Your Order is Ready 🎉",
                message=f"Order #{order.order_id} is ready for pickup.",
                priority=NotificationPriority.HIGH,
                order_id=order.order_id,
            )

        elif next_status == OrderStatus.PREPARING:
            NotificationService.trigger(
                db=db,
                event=NotificationEvent.ORDER_ACCEPTED,
                recipient_type=NotificationRecipient.USER,
                recipient_id=order.user_id,
                title="Order Accepted 👨‍🍳",
                message=f"Order #{order.order_id} is being prepared.",
                priority=NotificationPriority.MEDIUM,
                order_id=order.order_id,
            )

        return {
            "order_id": order.order_id,
            "status": order.order_status,
        }