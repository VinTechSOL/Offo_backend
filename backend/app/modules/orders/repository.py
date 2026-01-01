from sqlalchemy.orm import Session
from app.modules.orders.models import Order, OrderItem
from sqlalchemy import text,select,update
from datetime import datetime, timedelta
from app.modules.orders.constants import OrderStatus

class OrderRepository:

    @staticmethod
    def create_order(db: Session, order: Order):
        db.add(order)
        db.flush()
        return order

    @staticmethod
    def add_order_items(db: Session, order_id: int, cart_items: list):
        for item in cart_items:
            db.add(
                OrderItem(
                    order_id=order_id,
                    item_id=item.item_id,
                    quantity=item.quantity,
                    price_at_time=item.price_at_time
                )
            )

    
    @staticmethod
    def fetch_scheduled_to_promote(db: Session):
        return db.execute(
            text("""
                SELECT order_id
                FROM orders.orders
                WHERE order_status = 'SCHEDULED'
                  AND scheduled_time <= NOW() + INTERVAL '45 minutes'
                  AND scheduled_time > NOW()
                FOR UPDATE SKIP LOCKED
            """)
        ).scalars().all()

    @staticmethod
    def promote_to_incoming(db: Session, order_ids: list[int]):
        if not order_ids:
            return
        db.execute(
            text("""
                UPDATE orders.orders
                SET order_status = 'INCOMING',
                    updated_at = NOW()
                WHERE order_id = ANY(:ids)
            """),
            {"ids": order_ids}
        )

    @staticmethod
    def fetch_orders_to_expire(db: Session):
        return db.execute(
            text("""
                SELECT order_id
                FROM orders.orders
                WHERE order_status = 'INCOMING'
                  AND scheduled_time <= NOW()
                FOR UPDATE SKIP LOCKED
            """)
        ).scalars().all()

    @staticmethod
    def expire_orders(db: Session, order_ids: list[int]):
        if not order_ids:
            return
        db.execute(
            text("""
                UPDATE orders.orders
                SET order_status = 'EXPIRED',
                    updated_at = NOW()
                WHERE order_id = ANY(:ids)
            """),
            {"ids": order_ids}
        )

    
    @staticmethod
    def get_incoming_orders_for_branch(db: Session, branch_id: int):
        return db.execute(
            select(Order)
            .where(
                Order.branch_id == branch_id,
                Order.order_status == OrderStatus.INCOMING
            )
            .order_by(Order.created_at)
        ).scalars().all()

    @staticmethod
    def get_order(db: Session, order_id: int):
        return db.get(Order, order_id)

    @staticmethod
    def update_status(db: Session, order: Order, status: str):
        order.order_status = status
        db.commit()
        db.refresh(order)
        return order
