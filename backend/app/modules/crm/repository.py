from sqlalchemy.orm import Session
from sqlalchemy import func
from app.modules.users.models import User
from app.modules.orders.models import Order


class CrmRepository:

    @staticmethod
    def get_customers_with_order_stats(db: Session, branch_id: int):

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
