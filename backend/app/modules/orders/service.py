from sqlalchemy.orm import Session
from app.modules.cart.repository import CartRepository
from app.modules.vendor.models import CafeBranch
from app.modules.orders.repository import OrderRepository
from app.modules.orders.constants import OrderStatus, PaymentStatus
from app.modules.orders.models import Order
from app.modules.orders.validators import (validate_transition,validate_scheduled_visibility,validate_user_cancellation)
from app.modules.staff.access_control import validate_branch_access
from app.modules.orders.payment_service import OrderPaymentService
from app.modules.orders.priority import OrderPriority,calculate_priority
from app.modules.notifications.service import NotificationService
from app.modules.notifications.constants import (
    NotificationEvent,
    NotificationRecipient,
    NotificationPriority,
)
from datetime import timedelta,datetime,timezone
from fastapi import HTTPException
from app.core.time_utils import now_utc,IST
from datetime import timezone


def build_scheduled_datetime(
    scheduled_date,
    scheduled_time,
):
    if not scheduled_date or not scheduled_time:
        raise HTTPException(
            status_code=400,
            detail="Scheduled date and time are required",
        )

    try:
        time_obj = datetime.strptime(
            scheduled_time,
            "%I:%M %p",
        ).time()

    except ValueError:
        raise HTTPException(
            status_code=400,
            detail="Invalid scheduled time format. Use HH:MM AM/PM",
        )

    naive_dt = datetime.combine(
        scheduled_date,
        time_obj,
    )

    ist_dt = IST.localize(naive_dt)

    scheduled_utc = ist_dt.astimezone(timezone.utc)

    if scheduled_utc <= now_utc():
        raise HTTPException(
            status_code=400,
            detail="Scheduled time must be in the future",
        )

    return scheduled_utc


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
                payment_status=PaymentStatus.PENDING,
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
                    payment_status=PaymentStatus.PENDING,
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
                            payment_status=PaymentStatus.PENDING,
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
        # 6 Return Proper Model(s)
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
        payment_status=PaymentStatus.PENDING,
        repeat_weekly=True,
        repeat_remaining=order.repeat_remaining - 1,
       )

       db.add(new_order)

    @staticmethod  
    def cancel_order_by_user(
        db: Session,
        order_id: int,
        user_id: int,
    ):
        """
        Cancel an order initiated by the customer.

        Rules:

            CREATED
                → cancellation allowed

            PREPARING+
                → cancellation rejected

        If the order has already been paid:

            CREATED + PAID
                → CANCELLED
                → REFUND_PENDING

        If payment has not completed:

            CREATED + PENDING/FAILED
                → CANCELLED
                → no refund
        """

        order = db.get(Order, order_id)

        if not order:
            raise HTTPException(
                status_code=404,
                detail="Order not found",
            )

        # --------------------------------------------------------
        # Ownership
        # --------------------------------------------------------

        if order.user_id != user_id:
            raise HTTPException(
                status_code=403,
                detail="Not allowed",
            )

        # --------------------------------------------------------
        # Cancellation eligibility
        # --------------------------------------------------------

        validate_user_cancellation(order)

        current_status = OrderStatus(order.order_status)

        # --------------------------------------------------------
        # State transition
        # --------------------------------------------------------

        validate_transition(
            current_status,
            OrderStatus.CANCELLED,
        )

        # --------------------------------------------------------
        # Cancel order
        # --------------------------------------------------------

        order.order_status = OrderStatus.CANCELLED
        order.updated_at = now_utc()

        OrderRepository.add_status_log(
            db,
            order_id=order.order_id,
            status=OrderStatus.CANCELLED,
            changed_by="USER",
            changed_by_id=user_id,
        )

        # --------------------------------------------------------
        # Paid order → refund pending
        # --------------------------------------------------------

        refund_pending = False

        if order.payment_status == PaymentStatus.PAID:

            refund_pending = (
                OrderPaymentService
                .mark_refund_pending_in_transaction(
                    db=db,
                order=order,
                )
            )

        # --------------------------------------------------------
        # Commit entire cancellation transaction
        # --------------------------------------------------------

        db.commit()
        db.refresh(order)

        return {
            "order_id": order.order_id,
            "order_status": order.order_status,
            "payment_status": order.payment_status,
            "refund_pending": refund_pending,
        }

    


#vendor order service 

class VendorOrderService:

    # ============================================================
    # ACCEPT ORDER
    # CREATED → PREPARING
    # ============================================================

    @staticmethod
    def accept_order(
        db: Session,
        order_id: int,
        staff,
    ):
        order = db.get(Order, order_id)

        if not order:
            raise HTTPException(
                status_code=404,
                detail="Order not found",
            )

        # --------------------------------------------------------
        # Branch access
        # --------------------------------------------------------

        validate_branch_access(
            staff,
            order.branch_id,
        )

        # --------------------------------------------------------
        # Payment must be completed
        # --------------------------------------------------------

        if order.payment_status != PaymentStatus.PAID:
            raise HTTPException(
                status_code=400,
                detail="Order payment is not completed",
            )

        # --------------------------------------------------------
        # Scheduled order visibility
        # --------------------------------------------------------

        validate_scheduled_visibility(order)

        # --------------------------------------------------------
        # CREATED → PREPARING
        # --------------------------------------------------------

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

        # --------------------------------------------------------
        # Notify user
        # --------------------------------------------------------

        NotificationService.trigger(
            db=db,
            event=NotificationEvent.ORDER_ACCEPTED,
            recipient_type=NotificationRecipient.USER,
            recipient_id=order.user_id,
            title="Order Accepted 👨‍🍳",
            message=(
                f"Order "
                f"{OrderRepository.build_display_order_id(order)} "
                f"is being prepared."
            ),
            priority=NotificationPriority.MEDIUM,
            order_id=order.order_id,
        )

        db.commit()

        return {
            "order_id": order.order_id,
            "status": order.order_status,
        }

    # ============================================================
    # REJECT ORDER
    # CREATED → REJECTED
    # ============================================================

    @staticmethod
    def reject_order(
        db: Session,
        order_id: int,
        staff,
    ):

        """
        Reject a CREATED + PAID order.

        Flow:

            CREATED + PAID
                ↓
            REJECTED + REFUND_PENDING
                ↓
            Refund processor
                ↓
            PhonePe refund

        The PhonePe gateway is NOT called here.
        """
        order = db.get(Order, order_id)

        if not order:
            raise HTTPException(
                status_code=404,
                detail="Order not found",
            )

        # --------------------------------------------------------
        # Branch access
        # --------------------------------------------------------

        validate_branch_access(
            staff,
            order.branch_id,
        )

        # --------------------------------------------------------
        # Payment must be completed
        # --------------------------------------------------------

        if order.payment_status != PaymentStatus.PAID:
            raise HTTPException(
                status_code=400,
                detail="Only paid orders can be rejected",
            )

        # --------------------------------------------------------
        # Scheduled visibility
        # --------------------------------------------------------

        validate_scheduled_visibility(order)

        # --------------------------------------------------------
        # CREATED → REJECTED
        # --------------------------------------------------------
        current_status = OrderStatus(order.order_status)

        validate_transition(
            current_status,
            OrderStatus.REJECTED,
        )

        order.order_status = OrderStatus.REJECTED
        order.updated_at = now_utc()

        OrderRepository.add_status_log(
            db,
            order_id=order.order_id,
            status=OrderStatus.REJECTED,
            changed_by="STAFF",
            changed_by_id=staff.staff_id,
        )

        # --------------------------------------------------------
        # Paid rejected order → refund pending
        # --------------------------------------------------------

        refund_pending = (
            OrderPaymentService.mark_refund_pending_in_transaction(
                db=db,
                order=order,
            )
        )

        # --------------------------------------------------------
        # IMPORTANT:
        #
        # Order rejection + REFUND_PENDING are committed together.
        # --------------------------------------------------------

        db.commit()
        db.refresh(order)

        # --------------------------------------------------------
        # Notify user
        # --------------------------------------------------------

        NotificationService.trigger(
            db=db,
            event=NotificationEvent.ORDER_REJECTED,
            recipient_type=NotificationRecipient.USER,
            recipient_id=order.user_id,
            title="Order Rejected",
            message=(
                f"Order "
                f"{OrderRepository.build_display_order_id(order)} "
                f"was rejected."
            ),
            priority=NotificationPriority.HIGH,
            order_id=order.order_id,
        )

        db.commit()

        return {
            "order_id": order.order_id,
            "status": order.order_status,
            "payment_status": order.payment_status,
            "refund_pending": refund_pending,
        }

    # ============================================================
    # MOVE ORDER
    #
    # PREPARING → READY
    # READY → PICKED_UP → COMPLETED
    # ============================================================

    @staticmethod
    def move_order(
        db: Session,
        order_id: int,
        staff,
        next_status: OrderStatus,
    ):
        order = db.get(Order, order_id)

        if not order:
            raise HTTPException(
                status_code=404,
                detail="Order not found",
            )

        # --------------------------------------------------------
        # Branch access
        # --------------------------------------------------------

        validate_branch_access(
            staff,
            order.branch_id,
        )

        # --------------------------------------------------------
        # Payment check
        # --------------------------------------------------------

        if order.payment_status != PaymentStatus.PAID:
            raise HTTPException(
                status_code=400,
                detail="Order payment is not completed",
            )

        # --------------------------------------------------------
        # Scheduled visibility
        # --------------------------------------------------------

        validate_scheduled_visibility(order)

        current_status = OrderStatus(order.order_status)

        # --------------------------------------------------------
        # IMPORTANT:
        #
        # Vendor's move endpoint is NOT allowed to:
        #
        # CREATED → READY
        # CREATED → PICKED_UP
        # PREPARING → PICKED_UP
        # READY → COMPLETED
        #
        # The state machine prevents this.
        # --------------------------------------------------------

        validate_transition(
            current_status,
            next_status,
        )

        # ========================================================
        # PREPARING → READY
        # ========================================================

        if next_status == OrderStatus.READY:

            order.order_status = OrderStatus.READY
            order.updated_at = now_utc()

            OrderRepository.add_status_log(
                db,
                order_id=order.order_id,
                status=OrderStatus.READY,
                changed_by="STAFF",
                changed_by_id=staff.staff_id,
            )

            db.commit()
            db.refresh(order)

            NotificationService.trigger(
                db=db,
                event=NotificationEvent.ORDER_READY,
                recipient_type=NotificationRecipient.USER,
                recipient_id=order.user_id,
                title="Your Order is Ready 🎉",
                message=(
                    f"Order "
                    f"{OrderRepository.build_display_order_id(order)} "
                    f"is ready for pickup."
                ),
                priority=NotificationPriority.HIGH,
                order_id=order.order_id,
            )

            db.commit()

            return {
                "order_id": order.order_id,
                "status": order.order_status,
            }

        # ========================================================
        # READY → PICKED_UP → COMPLETED
        # ========================================================

        if next_status == OrderStatus.PICKED_UP:

            # ----------------------------------------------------
            # Timeline event: PICKED_UP
            # ----------------------------------------------------

            OrderRepository.add_status_log(
                db,
                order_id=order.order_id,
                status=OrderStatus.PICKED_UP,
                changed_by="STAFF",
                changed_by_id=staff.staff_id,
            )

            # ----------------------------------------------------
            # Actual database state becomes COMPLETED immediately
            # ----------------------------------------------------

            order.order_status = OrderStatus.COMPLETED
            order.updated_at = now_utc()

            # ----------------------------------------------------
            # Timeline event: COMPLETED
            # ----------------------------------------------------

            OrderRepository.add_status_log(
                db,
                order_id=order.order_id,
                status=OrderStatus.COMPLETED,
                changed_by="SYSTEM",
                changed_by_id=None,
            )

            db.commit()
            db.refresh(order)

            # ----------------------------------------------------
            # Notify user
            # ----------------------------------------------------

            NotificationService.trigger(
                db=db,
                event=NotificationEvent.ORDER_COMPLETED,
                recipient_type=NotificationRecipient.USER,
                recipient_id=order.user_id,
                title="Order Completed 🎉",
                message=(
                    f"Order "
                    f"{OrderRepository.build_display_order_id(order)} "
                    f"has been picked up and completed."
                ),
                priority=NotificationPriority.MEDIUM,
                order_id=order.order_id,
            )

            db.commit()

            return {
                "order_id": order.order_id,
                "status": order.order_status,
            }

        # --------------------------------------------------------
        # Defensive fallback
        # --------------------------------------------------------

        raise HTTPException(
            status_code=400,
            detail=(
                f"Unsupported vendor transition: "
                f"{current_status.value} → {next_status.value}"
            ),
        )