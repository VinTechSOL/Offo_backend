from fastapi import HTTPException
from sqlalchemy.orm import Session
from app.modules.orders.repository import OrderRepository

class UserOrderService:

    @staticmethod
    def list_orders(db: Session, user_id: int):
        orders = OrderRepository.get_orders_for_user(db, user_id)

        return [
            {
                "order_id": o.order_id,
                "order_type": o.order_type,
                "scheduled_time": o.scheduled_time,
                "status": o.order_status,
                "total_amount": o.total_amount,
                "created_at": o.created_at,
            }
            for o in orders
        ]

    @staticmethod
    def get_order(db: Session, user_id: int, order_id: int):
        order = OrderRepository.get_user_order_by_id(db, user_id, order_id)

        if not order:
            raise HTTPException(404, "Order not found")

        items = OrderRepository.get_order_items(db, order.order_id)

        return {
            "order_id": order.order_id,
            "order_type": order.order_type,
            "scheduled_time": order.scheduled_time,
            "status": order.order_status,
            "total_amount": order.total_amount,
            "items": [
                {
                    "item_id": i.item_id,
                    "quantity": i.quantity,
                    "price": i.price_at_time,
                }
                for i in items
            ],
            "created_at": order.created_at,
        }
