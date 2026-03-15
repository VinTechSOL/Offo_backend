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

LIVE_WINDOW_MINUTES = 60
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
                MenuItem.image_url.label("image_url"),
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
        """
        Shows scheduled orders that are
        more than 60 minutes away.
        """
        now = now_utc()
        visibility_until = now + timedelta(minutes=LIVE_WINDOW_MINUTES)

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
                Order.scheduled_time > visibility_until,
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

                "items":[
                    {
                        "item_id": i.item_id,
                        "name": i.name,
                        "quantity": i.quantity,
                        "price_at_time": float(i.price_at_time),
                        "image_url": i.image_url,
                    }
                    for i in OrderRepository.get_order_items(db,o.order_id)
                ]
            }
            for o, first, last, campus, building in rows
            
        ]
    

    @staticmethod
    def get_all_today_orders(db: Session, branch_id: int):

        now = now_utc()

        # Start of today (UTC)
        start_of_day = datetime(
            year=now.year,
            month=now.month,
            day=now.day,
            tzinfo=now.tzinfo
        )

        end_of_day = start_of_day + timedelta(days=1)

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
                Order.created_at >= start_of_day,
                Order.created_at < end_of_day,
            )
           .order_by(Order.created_at.desc())
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
                "created_at": o.created_at,
                "items": [
                    {
                        "item_id": i.item_id,
                        "name": i.name,
                        "quantity": i.quantity,
                        "price_at_time": float(i.price_at_time),
                        "image_url": i.image_url,
                    }
                    for i in OrderRepository.get_order_items(db, o.order_id)
                ],
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
        """
        Live screen shows:
        - All INSTANT orders (CREATED, PREPARING, READY)
        - SCHEDULED orders within next 60 minutes
        """

        now = now_utc()
        visibility_until = now + timedelta(minutes=LIVE_WINDOW_MINUTES)

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
                    OrderStatus.READY
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
            items = OrderRepository.get_order_items(db,order.order_id)

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
                "items":[
                    {
                        "item_id": i.item_id,
                        "name": i.name,
                        "quantity": i.quantity,
                        "price_at_time": float(i.price_at_time),
                        "image_url": i.image_url,
                    }
                    for i in items
                ]
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

    
    @staticmethod
    def get_order_alert_status(db: Session, branch_id: int):

        incoming_orders = (
            db.query(Order)
            .filter(
                Order.branch_id == branch_id,
                Order.order_status == OrderStatus.CREATED,
            )
            .order_by(Order.created_at.desc())
            .all()
        )

        if not incoming_orders:
            return {
                "latest_order_id": None,
                "latest_high_priority_id": None,
                "total_active_orders": 0,
            }

        latest_order_id = incoming_orders[0].order_id

        latest_high_priority_id = None

        for order in incoming_orders:
            if calculate_priority(order) == "HIGH":
                latest_high_priority_id = order.order_id
                break

        return {
            "latest_order_id": latest_order_id,
            "latest_high_priority_id": latest_high_priority_id,
            "total_active_orders": len(incoming_orders),
        }
    

    @staticmethod
    def get_users_by_branches(db: Session, branch_ids: list[int]):

        rows = (
            db.query(
               User.user_id,
               User.first_name,
               User.last_name,
               User.mobile_number,
               Order.branch_id,
               func.count(Order.order_id).label("total_orders"),
               func.sum(Order.total_amount).label("total_spent"),
               func.max(Order.created_at).label("last_order"),
            )
           .join(Order, Order.user_id == User.user_id)
           .filter(Order.branch_id.in_(branch_ids))
           .group_by(
               User.user_id,
               User.first_name,
               User.last_name,
               User.mobile_number,
               Order.branch_id,
            )
            .all()
        )

        results = []

        for r in rows:

            status = "Active"

            if r.total_orders == 0:
               status = "No Orders"
            elif r.last_order:
               delta = datetime.now(timezone.utc) - r.last_order
               if delta.days > 30:
                 status = "Inactive"

            results.append({
                "id": r.user_id,
                "branchId": r.branch_id,
                "firstName": r.first_name,
                "lastName": r.last_name,
                "mobile": r.mobile_number,
                "totalOrders": r.total_orders,
                "totalSpent": float(r.total_spent or 0),
                "lastOrder": r.last_order,
                "status": status,
            })

        return results



    
    