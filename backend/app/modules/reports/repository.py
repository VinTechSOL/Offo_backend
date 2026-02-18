from sqlalchemy.orm import Session
from sqlalchemy import func
from app.modules.orders.models import Order, OrderItem
from app.modules.menu.models import MenuItem, MenuCategory
from app.modules.users.models import User
from app.modules.orders.constants import OrderStatus


class ReportsRepository:

    @staticmethod
    def get_overview(db: Session, branch_id: int):

        total_revenue = db.query(
            func.coalesce(func.sum(Order.total_amount), 0)
        ).filter(
            Order.branch_id == branch_id,
            Order.order_status == OrderStatus.PICKED_UP
        ).scalar()

        total_orders = db.query(func.count(Order.order_id)).filter(
            Order.branch_id == branch_id
        ).scalar()

        avg_order_value = total_revenue / total_orders if total_orders else 0

        status_counts = db.query(
            Order.order_status,
            func.count(Order.order_id)
        ).filter(
            Order.branch_id == branch_id
        ).group_by(Order.order_status).all()

        status_distribution = {
            status: count for status, count in status_counts
        }

        return {
            "total_revenue": float(total_revenue),
            "total_orders": total_orders,
            "average_order_value": float(avg_order_value),
            "status_distribution": status_distribution,
        }

    @staticmethod
    def get_menu_performance(db: Session, branch_id: int):

        rows = db.query(
            OrderItem.item_id,
            func.sum(OrderItem.quantity).label("total_quantity"),
            func.sum(OrderItem.quantity * OrderItem.price_at_time).label("total_revenue"),
            MenuItem.item_name,
            MenuItem.image_url,
            MenuCategory.category_name
        ).join(
            Order, Order.order_id == OrderItem.order_id
        ).join(
            MenuItem, MenuItem.item_id == OrderItem.item_id
        ).join(
            MenuCategory, MenuCategory.category_id == MenuItem.item_id, isouter=True
        ).filter(
            Order.branch_id == branch_id,
            Order.order_status == OrderStatus.PICKED_UP
        ).group_by(
            OrderItem.item_id,
            MenuItem.item_name,
            MenuItem.image_url,
            MenuCategory.category_name
        ).order_by(
            func.sum(OrderItem.quantity).desc()
        ).all()

        return [
            {
                "item_id": r.item_id,
                "name": r.item_name,
                "image_url": r.image_url,
                "category": r.category_name,
                "total_quantity_sold": int(r.total_quantity),
                "total_revenue_generated": float(r.total_revenue),
            }
            for r in rows
        ]

    @staticmethod
    def get_customer_insights(db: Session, branch_id: int):

        rows = db.query(
            User.user_id,
            User.first_name,
            User.last_name,
            User.mobile_number,
            func.count(Order.order_id).label("total_orders")
        ).join(
            Order, Order.user_id == User.user_id
        ).filter(
            Order.branch_id == branch_id
        ).group_by(
            User.user_id
        ).order_by(
            func.count(Order.order_id).desc()
        ).all()

        return [
            {
                "user_id": r.user_id,
                "name": f"{r.first_name or ''} {r.last_name or ''}".strip(),
                "phone": r.mobile_number,
                "total_orders": r.total_orders,
            }
            for r in rows
        ]
