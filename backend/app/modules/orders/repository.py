from sqlalchemy.orm import Session
from sqlalchemy import select, or_, and_,func
from datetime import datetime, timedelta, timezone,date

from app.modules.orders.models import Order, OrderItem,OrderStatusLog
from app.modules.orders.constants import OrderStatus


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
        stmt = (
            select(Order)
            .where(Order.user_id == user_id)
            .order_by(Order.created_at.desc())
        )
        return db.execute(stmt).scalars().all()

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
        stmt = select(OrderItem).where(OrderItem.order_id == order_id)
        return db.execute(stmt).scalars().all()
    
    @staticmethod
    def get_active_orders_for_user(db, user_id: int):
        active_statuses = [
            OrderStatus.CREATED,
            OrderStatus.ACCEPTED,
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
        """
        Incoming orders = orders vendor can act on
        - Status must be CREATED
        - Instant orders → always visible
        - Scheduled orders → visible only within 60 minutes window
        """
        now = datetime.now(timezone.utc)
        scheduled_window = now + timedelta(minutes=60)

        stmt = (
            select(Order)
            .where(
                Order.branch_id == branch_id,
                Order.order_status == OrderStatus.CREATED,
                or_(
                    # Instant orders
                    Order.order_type == "INSTANT",

                    # Scheduled orders in visibility window
                    and_(
                        Order.order_type == "SCHEDULED",
                        Order.scheduled_time <= scheduled_window,
                    ),
                ),
            )
            .order_by(Order.created_at.asc())
        )

        return db.execute(stmt).scalars().all()

    # -----------------------
    # Single Order
    # -----------------------

    @staticmethod
    def get_order(db: Session, order_id: int):
        return db.get(Order, order_id)

    @staticmethod
    def update_status(db: Session, order: Order, status: OrderStatus):
        order.order_status = status
        order.updated_at = datetime.now(timezone.utc)
        db.commit()
        db.refresh(order)
        return order
    

    @staticmethod
    def get_scheduled_orders_for_date(
        db: Session,
        branch_id: int,
        target_date
    ):
        stmt = select(Order).where(
            Order.branch_id == branch_id,
            Order.order_type == "SCHEDULED",
            Order.order_status == OrderStatus.CREATED,
            func.date(Order.scheduled_time) == target_date
        )
        return db.execute(stmt).scalars().all()
    
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
        grace_limit = datetime.now(timezone.utc) - timedelta(minutes=5)

        stmt = select(Order).where(
            Order.order_type == "SCHEDULED",
            Order.order_status == OrderStatus.CREATED,
            Order.scheduled_time < grace_limit
        )

        return db.execute(stmt).scalars().all()

    @staticmethod
    def expire_orders(db: Session, orders):
        now = datetime.now(timezone.utc)

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
        now = datetime.now(timezone.utc)
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
    def get_live_orders(db, branch_id: int, window_minutes: int = 60):
        """
        Live orders = orders vendor should act on NOW
        """
        now = datetime.now(timezone.utc)
        visibility_until = now + timedelta(minutes=window_minutes)

        stmt = select(Order).where(
            Order.branch_id == branch_id,
            Order.order_status == OrderStatus.CREATED,
            or_(
                Order.order_type == "INSTANT",
                and_(
                    Order.order_type == "SCHEDULED",
                    Order.scheduled_time <= visibility_until
                )
            )
        ).order_by(
            Order.scheduled_time.asc().nullsfirst(),
            Order.created_at.asc()
        )

        return db.execute(stmt).scalars().all()

    
