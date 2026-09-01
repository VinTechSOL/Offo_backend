from sqlalchemy.orm import Session
from sqlalchemy import func
from datetime import datetime

from app.modules.orders.models import Order, OrderItem
from app.modules.menu.models import MenuItem, MenuCategory, BranchMenuItem
from app.modules.users.models import User
from app.modules.orders.constants import OrderStatus


class ReportsRepository:

    @staticmethod
    def apply_date_filter(
        query,
        start_date=None,
        end_date=None,
    ):

        if start_date:
            query = query.filter(
                Order.created_at >= start_date
            )

        if end_date:
            query = query.filter(
                Order.created_at <= end_date
            )

        return query

    @staticmethod
    def get_overview(
        db: Session,
        branch_id: int,
        start_date=None,
        end_date=None,
    ):

        revenue_query = db.query(
            func.coalesce(func.sum(Order.total_amount), 0)
        ).filter(
            Order.branch_id == branch_id,
            Order.order_status == OrderStatus.COMPLETED
        )

        revenue_query = ReportsRepository.apply_date_filter(
            revenue_query,
            start_date,
            end_date
        )

        total_revenue = revenue_query.scalar()

        orders_query = db.query(Order).filter(
            Order.branch_id == branch_id
        )

        orders_query = ReportsRepository.apply_date_filter(
            orders_query,
            start_date,
            end_date
        )

        total_orders = orders_query.count()

        instant_orders = orders_query.filter(
            Order.order_type == "INSTANT"
        ).count()

        scheduled_orders = orders_query.filter(
            Order.order_type == "SCHEDULED"
        ).count()

        avg_order_value = (
            total_revenue / total_orders
            if total_orders else 0
        )

        status_counts_query = db.query(
            Order.order_status,
            func.count(Order.order_id)
        ).filter(
            Order.branch_id == branch_id
        )

        status_counts_query = ReportsRepository.apply_date_filter(
            status_counts_query,
            start_date,
            end_date
        )

        status_counts = status_counts_query.group_by(
            Order.order_status
        ).all()

        status_distribution = {
            status: count
            for status, count in status_counts
        }

        return {
            "total_revenue": float(total_revenue),
            "total_orders": total_orders,
            "instant_orders": instant_orders,
            "scheduled_orders": scheduled_orders,
            "average_order_value": float(avg_order_value),
            "status_distribution": status_distribution,
        }

    @staticmethod
    def get_menu_performance(
        db: Session,
        branch_id: int,
        start_date=None,
        end_date=None,
    ):

        query = db.query(
            OrderItem.item_id,

            func.sum(OrderItem.quantity).label(
                "total_quantity"
            ),

            func.sum(
                OrderItem.quantity * OrderItem.price_at_time
            ).label(
                "total_revenue"
            ),

            MenuItem.item_name,

            MenuItem.image_url,

            MenuCategory.category_name

        ).join(
            Order,
            Order.order_id == OrderItem.order_id

        ).join(
            MenuItem,
            MenuItem.item_id == OrderItem.item_id
        
        ).join(
            BranchMenuItem,
            BranchMenuItem.item_id == MenuItem.item_id,
            isouter=True

        ).join(
            MenuCategory,
            MenuCategory.category_id == BranchMenuItem.category_id,
            isouter=True

        ).filter(
            Order.branch_id == branch_id,
            BranchMenuItem.branch_id == branch_id,
            Order.order_status == OrderStatus.COMPLETED
        )

        query = ReportsRepository.apply_date_filter(
            query,
            start_date,
            end_date
        )

        rows = query.group_by(
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

                "category": (
                    r.category_name
                    if r.category_name
                    else "Uncategorized"
                ),
                "total_quantity_sold": int(
                    r.total_quantity
                ),

                "total_revenue_generated": float(
                    r.total_revenue
                ),
            }
            for r in rows
        ]

    @staticmethod
    def get_customer_insights(
        db: Session,
        branch_id: int,
        start_date=None,
        end_date=None,
    ):

        query = db.query(
            User.user_id,

            User.first_name,

            User.last_name,

            User.mobile_number,

            func.count(Order.order_id).label(
                "total_orders"
            )

        ).join(
            Order,
            Order.user_id == User.user_id

        ).filter(
            Order.branch_id == branch_id
        )

        query = ReportsRepository.apply_date_filter(
            query,
            start_date,
            end_date
        )

        rows = query.group_by(
            User.user_id,

            User.first_name,

            User.last_name,

            User.mobile_number

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