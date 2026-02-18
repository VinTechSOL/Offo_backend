from fastapi import HTTPException
from sqlalchemy.orm import Session
from app.modules.orders.repository import OrderRepository
from app.modules.orders.constants import OrderStatus


def normalize_user_status(status: str) -> str:
    if status == OrderStatus.PICKED_UP:
        return OrderStatus.COMPLETED
    return status

class UserOrderService:


    @staticmethod
    def list_orders(db: Session, user_id: int):
        orders = OrderRepository.get_orders_for_user(db, user_id)
        
        response = []

        for o,cafe in orders:
            items = OrderRepository.get_order_items(db, o.order_id)

            response.append({
                "order_id": o.order_id,
                "user_id": o.user_id,
                "branch_id": o.branch_id,
            
                "cafe_id": cafe.cafe_id,
                "cafe_name": cafe.branch_name,
                

                "order_type": o.order_type,
                "order_status": normalize_user_status(o.order_status) ,
                "payment_status": o.payment_status,

                "scheduled_time": o.scheduled_time,
                "created_at": o.created_at,
                "updated_at": o.updated_at,

                "total_amount": float(o.total_amount),

                "items": [
                    {
                        "item_id": i.item_id,
                        "name": i.name,
                        "quantity": i.quantity,
                        "price_at_time": float(i.price_at_time),
                    }
                    for i in items
                ],

            })

        return response
    

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
            "status": normalize_user_status(order.order_status),
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
