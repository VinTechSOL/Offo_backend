from sqlalchemy.orm import Session,joinedload
from sqlalchemy import select, or_, and_,func
from datetime import datetime, timedelta, timezone,date
from app.modules.menu.models import MenuItem
from app.modules.orders.models import Order, OrderItem,OrderStatusLog
from app.modules.orders.constants import OrderStatus
from app.modules.vendor.models import CafeBranch as Cafe
from app.modules.users.models import User
from app.modules.locations.models import Campus,Building
from app.modules.orders.priority import calculate_priority,OrderPriority
from app.core.time_utils import now_utc,to_ist


class OrderRepository:

    # -----------------------
    # Order Creation
    # -----------------------

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

    # user Orders (user View)
    # -----------------------
    
    @staticmethod
    def get_orders_for_user(db: Session, user_id: int):
        return (
            db.query(Order,Cafe)
            .join(Cafe, Cafe.cafe_id == Order.cafe_id)
            .filter(Order.user_id == user_id)
            .order_by(Order.created_at.desc())
            .all()
        )

    @staticmethod
    def get_user_order_by_id(db: Session, user_id: int, order_id: int):
        stmt = (
            select(Order)
            .where(
                Order.order_id == order_id,
                Order.user_id == user_id
            )
        )
        return db.execute(stmt).scalar_one_or_none()

    
    @staticmethod
    def get_order_items(db: Session, order_id: int):
        return (
            db.query(
                OrderItem.item_id,
                OrderItem.quantity,
                OrderItem.price_at_time,
                MenuItem.item_name.label("name"),
            )
            .join(MenuItem, MenuItem.item_id == OrderItem.item_id)
            .filter(OrderItem.order_id == order_id)
            .all()
        ) 
    
    @staticmethod
    def get_active_orders_for_user(db, user_id: int):
        active_statuses = [
            OrderStatus.CREATED,
            OrderStatus.PREPARING,
            OrderStatus.READY,
        ]

        stmt = (
            select(Order)
            .where(
                Order.user_id == user_id,
                Order.order_status.in_(active_statuses)
            )
            .order_by(Order.created_at.desc())
        )

        return db.execute(stmt).scalars().all()



    # Incoming Orders (Vendor View)
    # -----------------------

    @staticmethod
    def get_incoming_orders_for_branch(db: Session, branch_id: int):
        now = now_utc()
        scheduled_window = now + timedelta(minutes=60)

        rows = (
            db.query(
                Order,
                User.first_name,
                User.last_name,
                Campus.campus_name,
                Building.building_name,
            )
            .join(User, User.user_id == Order.user_id)
            .join(Cafe, Cafe.branch_id == Order.branch_id)
            .join(Campus, Campus.campus_id == Cafe.campus_id)
            .join(Building, Building.building_id == Cafe.building_id)
            .filter(
                Order.branch_id == branch_id,
                Order.order_status == OrderStatus.CREATED,
                or_(
                   Order.order_type == "INSTANT",
                   and_(
                       Order.order_type == "SCHEDULED",
                       Order.scheduled_time <= scheduled_window,
                    ),
                ),
            )
            .order_by(Order.created_at.asc())
            .all()
        )

        results = []

        for o, first, last, campus, building in rows:
            if calculate_priority(o) == OrderPriority.EXPIRED:
                continue

            results.append({
               "order_id": o.order_id,
               "user_name": f"{first} {last}",
               "campus_name": campus,
               "building_name": building,
               "order_status": o.order_status,
               "payment_status": o.payment_status,
               "total_amount": float(o.total_amount),
               "scheduled_time": o.scheduled_time,
               "created_at": o.created_at,
            })

        return results



    # -----------------------
    # Single Order
    # -----------------------

    @staticmethod
    def get_order(db: Session, order_id: int):
        return db.get(Order, order_id)

    @staticmethod
    def update_status(db: Session, order: Order, status: OrderStatus):
        order.order_status = status
        order.updated_at = now_utc()
        db.commit()
        db.refresh(order)
        return order
    

    @staticmethod
    def get_all_scheduled_orders(db: Session, branch_id: int):

        now = now_utc()

        rows = (
            db.query(
                Order,
                User.first_name,
                User.last_name,
                Campus.campus_name,
                Building.building_name,
            )
            .join(User, User.user_id == Order.user_id)
            .join(Cafe, Cafe.branch_id == Order.branch_id)
            .join(Campus, Campus.campus_id == Cafe.campus_id)
            .join(Building, Building.building_id == Cafe.building_id)
            .filter(
                Order.branch_id == branch_id,
                Order.order_type == "SCHEDULED",
                Order.order_status == OrderStatus.CREATED,
                Order.scheduled_time > now,
            )
            .order_by(Order.scheduled_time.asc())
            .all()
        )

        return [
            {
                "order_id": o.order_id,
                "user_name": f"{first} {last}",
                "campus_name": campus,
                "building_name": building,
                "order_status": o.order_status,
                "payment_status": o.payment_status,
                "total_amount": float(o.total_amount),
                "scheduled_time": o.scheduled_time,
                "priority":calculate_priority(o),
                "created_at": o.created_at,
            }
            for o, first, last, campus, building in rows
        ]


    

    @staticmethod
    def get_scheduled_orders_for_date(db, branch_id: int, target_date: date):
        rows = (
            db.query(
                Order,
                User.first_name,
                User.last_name,
                Campus.campus_name,
                Building.building_name,
            )
            .join(User, User.user_id == Order.user_id)
            .join(Cafe, Cafe.branch_id == Order.branch_id)
            .join(Campus, Campus.campus_id == Cafe.campus_id)
            .join(Building, Building.building_id == Cafe.building_id)
            .filter(
                Order.branch_id == branch_id,
                Order.order_type == "SCHEDULED",
                Order.order_status == OrderStatus.CREATED,
                func.date(Order.scheduled_time) == target_date,
            )
            .order_by(Order.scheduled_time.asc())
            .all()
        )

        return [
            {
                "order_id": o.order_id,
                "user_name": f"{first} {last}",
                "campus_name": campus,
                "building_name": building,
                "order_status": o.order_status,
                "payment_status": o.payment_status,
                "total_amount": float(o.total_amount),
                "scheduled_time": o.scheduled_time,
            }
            for o, first, last, campus, building in rows
        ]

    
    
    @staticmethod
    def add_status_log(
        db,
        *,
        order_id: int,
        status: str,
        changed_by: str,
        changed_by_id: int | None = None,
    ):
        log = OrderStatusLog(
            order_id=order_id,
            status=status,
            changed_by=changed_by,
            changed_by_id=changed_by_id,
        )
        db.add(log)

    @staticmethod
    def get_order_timeline(db:Session,order_id: int):
        return (
            db.query(OrderStatusLog)
            .filter(OrderStatusLog.order_id == order_id)
            .order_by(OrderStatusLog.created_at.asc())
            .all()
        )
    
    # Scheduler helpers
    # -----------------------------

    @staticmethod
    def fetch_orders_to_expire(db: Session):
        grace_limit = now_utc() - timedelta(minutes=5)

        stmt = select(Order).where(
            Order.order_type == "SCHEDULED",
            Order.order_status == OrderStatus.CREATED,
            Order.scheduled_time < grace_limit
        )

        return db.execute(stmt).scalars().all()
    
    

    @staticmethod
    def expire_orders(db: Session, orders):
        now = now_utc()

        for order in orders:
            order.order_status = OrderStatus.CANCELLED
            order.updated_at = now

        db.commit()

    @staticmethod
    def mark_visible_for_vendor(db, window_minutes: int):
        # NOTHING TO UPDATE IN DB
        # Visibility is computed dynamically
        pass

    @staticmethod
    def expire_unaccepted_scheduled_orders(db, grace_minutes: int):
        now = now_utc()
        expiry_time = now - timedelta(minutes=grace_minutes)

        db.query(Order).filter(
            Order.order_type == "SCHEDULED",
            Order.order_status == OrderStatus.CREATED,
            Order.scheduled_time < expiry_time
        ).update(
            {
                "order_status": OrderStatus.EXPIRED,
                "updated_at": now
            },
            synchronize_session=False
        )


    @staticmethod
    def get_live_orders(db: Session, branch_id: int, window_minutes: int = 60):
        now = now_utc()
        visibility_until = now + timedelta(minutes=window_minutes)

        rows = (
            db.query(
                Order,
                User.first_name,
                User.last_name,
                Campus.campus_name,
                Building.building_name,
            )
            .join(User, User.user_id == Order.user_id)
            .join(Cafe, Cafe.branch_id == Order.branch_id)
            .join(Campus, Campus.campus_id == Cafe.campus_id)
            .join(Building, Building.building_id == Cafe.building_id)
            .filter(
                Order.branch_id == branch_id,
                Order.order_status.in_([
                    OrderStatus.CREATED,
                    OrderStatus.PREPARING,
                    OrderStatus.READY,
                    OrderStatus.PICKED_UP,
                ]),
                or_(
                    Order.order_type == "INSTANT",
                    and_(
                        Order.order_type == "SCHEDULED",
                        Order.scheduled_time <= visibility_until,
                    ),
                ),

            )
            .order_by(
                Order.created_at.asc(),
            )
           .all()
        )

        results = []

        for order, first, last, campus, building in rows:


            if calculate_priority(order) == OrderPriority.EXPIRED:
                continue

            results.append({
                "order_id": order.order_id,
                "user_name": f"{first} {last}",
                "campus_name": campus,
                "building_name": building,
                "status": order.order_status,
                "order_type": order.order_type,
                "scheduled_time": order.scheduled_time,
                "created_at": order.created_at,
                "total_amount": float(order.total_amount),
                "payment_status": order.payment_status,
                "priority": calculate_priority(order),
            })

        return results

    
    

    @staticmethod
    def get_order_history_for_branch(db: Session, branch_id: int):
        return (
            db.query(Order)
            .filter(
                Order.branch_id == branch_id,
                Order.order_status.in_([
                    OrderStatus.COMPLETED,
                    OrderStatus.CANCELLED,
                    OrderStatus.REJECTED,
                ])
            )
            .order_by(Order.updated_at.desc())
            .all()
        )



    
    