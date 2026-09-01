from sqlalchemy.orm import Session
from sqlalchemy import func
from app.modules.users.models import User
from app.modules.orders.models import Order, OrderItem
from app.modules.menu.models import MenuItem, BranchMenuItem


class CrmRepository:

    @staticmethod
    def get_customers_with_order_stats(db: Session, branch_id: int):
        rows = (
            db.query(
                User.user_id,
                User.first_name,
                User.last_name,
                User.mobile_number,
                func.count(Order.order_id).label("total_orders"),
            )
            .join(Order, Order.user_id == User.user_id)
            .filter(Order.branch_id == branch_id)
            .group_by(User.user_id)
            .order_by(func.count(Order.order_id).desc())
            .all()
        )

        return [
            {
                "id": str(r.user_id),
                "user_id": r.user_id,
                "name": f"{r.first_name or ''} {r.last_name or ''}".strip(),
                "phone": r.mobile_number,
                "totalOrders": r.total_orders,
            }
            for r in rows
        ]

    @staticmethod
    def get_customer_order_history(db: Session, branch_id: int, customer_id: int):
        # 1. Fetch all orders for this customer in this branch
        orders = (
            db.query(Order, User)
            .join(User, User.user_id == Order.user_id)
            .filter(
                Order.branch_id == branch_id,
                Order.user_id == customer_id,
            )
            .order_by(Order.created_at.desc())
            .all()
        )

        if not orders:
            return []

        order_ids = [order_tuple[0].order_id for order_tuple in orders]

        # 2. Fetch order items joining BranchMenuItem and MenuItem
        items_query = (
            db.query(
                OrderItem.order_id,
                OrderItem.item_id,
                OrderItem.quantity,
                OrderItem.price_at_time,
                MenuItem.item_name,
                MenuItem.image_url,
            )
            .outerjoin(
                BranchMenuItem,
                (BranchMenuItem.item_id == OrderItem.item_id)
                & (BranchMenuItem.branch_id == branch_id),
            )
            .outerjoin(MenuItem, MenuItem.item_id == OrderItem.item_id)
            .filter(OrderItem.order_id.in_(order_ids))
            .all()
        )

        # 3. Group items by order_id
        items_by_order: dict[int, list] = {}
        for item in items_query:
            items_by_order.setdefault(item.order_id, []).append({
                "item_id": item.item_id,
                "name": item.item_name or f"Item #{item.item_id}",
                "quantity": item.quantity,
                "price_at_time": float(item.price_at_time),
                "image_url": item.image_url or "",
            })

        # 4. Format the response to match the frontend normalizeOrder contract
        result = []
        for order, user in orders:
            result.append({
                "order_id": order.order_id,
                "display_order_id": getattr(order, "display_order_id", f"#{order.order_id}"),
                "order_type": order.order_type,
                "user_name": f"{user.first_name or ''} {user.last_name or ''}".strip(),
                "campus_name": getattr(user, "campus_name", "") or "",
                "building_name": getattr(user, "building_name", "") or "",
                "order_status": order.order_status,
                "created_at": order.created_at.isoformat() if order.created_at else None,
                "scheduled_time": order.scheduled_time.isoformat() if order.scheduled_time else None,
                "total_amount": float(order.total_amount),
                "payment_status": order.payment_status,
                "priority": getattr(order, "priority", None),
                "items": items_by_order.get(order.order_id, []),
            })

        return result