from fastapi import HTTPException
from sqlalchemy.orm import Session

from app.modules.orders.repository import OrderRepository
from app.modules.payments.repository import PaymentRepository

from app.modules.orders.constants import OrderStatus
from app.modules.orders.models import PaymentEvent
from app.modules.payments.models import (
    PaymentIntent,
    PaymentAttempt,
)
from app.modules.vendor.models import CafeBranch
from datetime import timedelta
from app.core.time_utils import now_utc
from decimal import Decimal



def normalize_user_status(status: str) -> str:
    if status == OrderStatus.PICKED_UP:
        return OrderStatus.COMPLETED

    return status

LIVE_WINDOW_MINUTES=60

def get_order_classification(order) -> str | None:
    """
    Classifies an order for the user's active-orders UI.

    ONGOING:
        - Instant order that is currently active
        - Scheduled order within the live 60-minute window

    SCHEDULED:
        - Scheduled order more than 60 minutes away

    None:
        - Completed / cancelled / rejected orders
    """

    status = normalize_user_status(order.order_status)

    active_statuses = {
        OrderStatus.CREATED,
        OrderStatus.PREPARING,
        OrderStatus.READY,
    }

    if status not in active_statuses:
        return None

    # ------------------------------------------------------------
    # INSTANT
    # ------------------------------------------------------------

    if order.order_type == "INSTANT":
        return "ONGOING"

    # ------------------------------------------------------------
    # SCHEDULED
    # ------------------------------------------------------------

    if order.order_type == "SCHEDULED":

        if not order.scheduled_time:
            return "ONGOING"

        now = now_utc()

        live_from = (
            order.scheduled_time
            - timedelta(minutes=LIVE_WINDOW_MINUTES)
        )

        if now >= live_from:
            return "ONGOING"

        return "SCHEDULED"

    return None


def build_order_bill(order, items):
    """
    Build the bill from the persisted order data.

    Order total is authoritative.
    Subtotal is calculated from order items.
    Convenience fee is the remaining amount.
    """

    subtotal = sum(
        (
            Decimal(str(item.price_at_time))
            * item.quantity
            for item in items
        ),
        Decimal("0.00"),
    )

    total = Decimal(str(order.total_amount))

    convenience_fee = total - subtotal

    return {
        "subtotal": float(subtotal),
        "convenience_fee": float(convenience_fee),
        "total": float(total),
    }

class UserOrderService:

    # ============================================================
    # ORDER LIST
    # ============================================================

    @staticmethod
    def list_orders(
        db: Session,
        user_id: int,
    ):

        orders = OrderRepository.get_orders_for_user(
            db,
            user_id,
        )

        response = []

        for o, cafe in orders:

            items = OrderRepository.get_order_items(
                db,
                o.order_id,
            )

            response.append({
                "order_id": o.order_id,
                "user_id": o.user_id,
                "branch_id": o.branch_id,

                "cafe_id": cafe.cafe_id,
                "cafe_name": cafe.branch_name,

                "order_type": o.order_type,
                "order_status": normalize_user_status(
                    o.order_status
                ),
                "payment_status": o.payment_status,
                "classification": get_order_classification(o),
                "scheduled_time": o.scheduled_time,
                "created_at": o.created_at,
                "updated_at": o.updated_at,

                "total_amount": float(
                    o.total_amount
                ),

                "items": [
                    {
                        "item_id": i.item_id,
                        "name": i.name,
                        "quantity": i.quantity,
                        "price_at_time": float(
                            i.price_at_time
                        ),
                    }
                    for i in items
                ],
            })

        return response

    # ============================================================
    # ORDER DETAIL
    # ============================================================

    @staticmethod
    def get_order(
        db: Session,
        user_id: int,
        order_id: int,
    ):

        # --------------------------------------------------------
        # Order
        # --------------------------------------------------------

        Order = OrderRepository.get_user_order_with_cafe(
            db,
            user_id,
            order_id,
        )

        if not Order:
            raise HTTPException(
                status_code=404,
                detail="Order not found",
            )

        # --------------------------------------------------------
        # Branch / Cafe
        # --------------------------------------------------------

        order, cafe = Order

        # --------------------------------------------------------
        # Items
        # --------------------------------------------------------

        items = OrderRepository.get_order_items(
            db,
            order.order_id,
        )

        # --------------------------------------------------------
        # Bill
        # --------------------------------------------------------

        bill = build_order_bill(
            order,
            items,
        )

        # --------------------------------------------------------
        # GEt payment information
        # --------------------------------------------------------

        intent = PaymentRepository.get_intent_by_order(
                db,
                order.order_id,
            )

        payment_attempt = None

        if intent:

            payment_attempt = (
                PaymentRepository.get_latest_payment_attempt(
                    db,
                    intent.intent_id,
                )
            )

        payment = {
            "status": order.payment_status,

            "intent_status": (
                intent.status
                if intent
                else None
            ),

            "gateway": (
                payment_attempt.gateway
                if payment_attempt
                else None
            ),

            "transaction_id": (
                payment_attempt.gateway_transaction_id
                if payment_attempt
               else None
           ),
        }

        # ============================================================
        # 5. GET ORDER STATUS TIMELINE
        # ============================================================

        timeline = (
            OrderRepository.get_order_timeline(
                db,
                order.order_id,
            )
        )

        # --------------------------------------------------------
        # Response
        # --------------------------------------------------------

        return {
            "order_id": order.order_id,

            "order_type": order.order_type,
            "classification": get_order_classification(order),
            "order_status": normalize_user_status(
                order.order_status
            ),
            "payment_status": order.payment_status,
            "total_amount": float(order.total_amount),
            "scheduled_time": order.scheduled_time,
            "created_at": order.created_at,
            "updated_at": order.updated_at,

            "cafe_id": order.cafe_id,
            "cafe_name": cafe.branch_name if cafe else None,
            "branch_id": order.branch_id,

            "bill": bill,
            "payment": payment,
            "items": [
                {
                    "item_id": item.item_id,
                    "name": item.name,
                    "quantity": item.quantity,
                    "price_at_time": float(
                        item.price_at_time
                    ),
                    "image_url": item.image_url,
                }
                for item in items
            ],

            "timeline": [
                {
                    "status": event.status,
                    "changed_by": event.changed_by,
                    "changed_by_id": event.changed_by_id,
                    "created_at": event.created_at,
                }
                for event in timeline
            ],

        }