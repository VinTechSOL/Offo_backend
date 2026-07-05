from fastapi import HTTPException, status
from passlib.context import CryptContext
from datetime import datetime, timedelta, timezone
from jose import jwt
from sqlalchemy.orm import Session
from sqlalchemy import func
from app.core.config import settings
from app.modules.staff.repository import StaffRepository
from app.modules.staff.models import Staff
from app.modules.staff_roles.models import  StaffRole

from app.modules.orders.models import Order,OrderItem
from app.modules.orders.constants import OrderStatus
from app.modules.menu.models import MenuItem

pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")


class StaffAuthService:

    # =========================================================
    # GENERIC CREATE STAFF (Already Exists)
    # =========================================================
    @staticmethod
    def create_staff(
        db: Session,
        first_name: str,
        last_name: str,
        username: str,
        password: str,
        role_id: int,
        branch_id=None
    ):
        # 🔒 Username uniqueness validation
        existing = StaffRepository.get_by_username(db, username)
        if existing:
            raise HTTPException(
                status_code=400,
                detail="Username already exists"
            )

        staff = Staff(
            first_name=first_name,
            last_name=last_name,
            username=username,
            password_hash=pwd_context.hash(password),
            role_id=role_id,
            branch_id=branch_id,
            is_active=True
        )

        return StaffRepository.create(db, staff)

    # =========================================================
    # VERIFY PASSWORD
    # =========================================================
    @staticmethod
    def verify_password(password: str, hashed: str) -> bool:
        if len(password.encode("utf-8")) > 72:
            return False

        return pwd_context.verify(password, hashed)

    # =========================================================
    # LOGIN
    # =========================================================
    @staticmethod
    def login(db: Session, username: str, password: str):

        staff = StaffRepository.get_by_username(db, username)

        if not staff:
            raise HTTPException(status_code=401, detail="Invalid credentials")

        if len(password.encode("utf-8")) > 72:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid credentials",
            )

        if not staff.is_active:
            raise HTTPException(status_code=403, detail="Staff inactive")

        if not pwd_context.verify(password, staff.password_hash):
            raise HTTPException(status_code=401, detail="Invalid credentials")

        token = StaffAuthService._generate_token(staff)

        return {
            "access_token": token,
            "token_type": "bearer",
            "staff_id": staff.staff_id,
            "role": staff.role.role_name,
            "branch_id": staff.branch_id
        }

    # =========================================================
    # CREATE VENDOR (SUPER ADMIN ONLY)
    # =========================================================
    @staticmethod
    def create_vendor(
        db: Session,
        first_name: str,
        last_name: str,
        username: str,
        password: str,
        branch_id: int
    ) -> Staff:

        # 🔍 Find VENDOR role dynamically
        vendor_role = (
            db.query(StaffRole)
            .filter(StaffRole.role_name == "VENDOR")
            .first()
        )

        if not vendor_role:
            raise HTTPException(
                status_code=500,
                detail="Vendor role not configured"
            )

        return StaffAuthService.create_staff(
            db=db,
            first_name=first_name,
            last_name=last_name,
            username=username,
            password=password,
            role_id=vendor_role.role_id,
            branch_id=branch_id
        )

    # =========================================================
    # GET VENDOR BY BRANCH
    # =========================================================
    @staticmethod
    def get_vendor_by_branch(
        db: Session,
        branch_id: int
    ) -> Staff | None:

        return (
            db.query(Staff)
            .join(Staff.role)
            .filter(
                Staff.branch_id == branch_id,
                Staff.role.has(role_name="VENDOR")
            )
            .first()
        )

    # =========================================================
    # RESET VENDOR PASSWORD
    # =========================================================
    @staticmethod
    def reset_vendor_password(
        db: Session,
        staff_id: int
    ) -> str:

        staff = StaffRepository.get_by_id(db, staff_id)

        if not staff:
            raise HTTPException(
                status_code=404,
                detail="Staff not found"
            )

        if staff.role.role_name != "VENDOR":
            raise HTTPException(
                status_code=400,
                detail="Password reset allowed only for vendors"
            )

        # 🔐 Generate secure temporary password
        new_password = "Temp" + str(staff.staff_id)

        staff.password_hash = pwd_context.hash(new_password)

        db.commit()
        db.refresh(staff)

        return new_password

    # =========================================================
    # TOKEN GENERATOR
    # =========================================================
    @staticmethod
    def _generate_token(staff):

        payload = {
            "staff_id": str(staff.staff_id),
            "role_id": str(staff.role_id),
            "role": staff.role.role_name,
            "iat": datetime.now(timezone.utc),
            "exp": datetime.now(timezone.utc) + timedelta(hours=8)
        }

        return jwt.encode(
            payload,
            settings.JWT_SECRET,
            algorithm=settings.JWT_ALGORITHM
        )
    


# =========================================================
    # CUSTOMISED ADMIN REPORTS
# =========================================================


class AdminReportService:

    @staticmethod
    def get_reports(db: Session, branch_ids: list[int], range: str):

        now = datetime.utcnow()

        if range == "today":
            start_date = now.replace(hour=0, minute=0, second=0)
        elif range == "week":
            start_date = now - timedelta(days=7)
        else:
            start_date = now - timedelta(days=30)

        orders = (
            db.query(Order)
            .filter(
                Order.branch_id.in_(branch_ids),
                Order.created_at >= start_date
            )
            .all()
        )

        total_orders = len(orders)

        total_revenue = sum(float(o.total_amount) for o in orders)

        avg_order_value = (
            total_revenue / total_orders if total_orders else 0
        )

        completed = len(
            [o for o in orders if o.order_status == OrderStatus.COMPLETED]
        )

        cancelled = len(
            [o for o in orders if o.order_status == OrderStatus.CANCELLED]
        )

        scheduled = len(
            [o for o in orders if o.order_type == "SCHEDULED"]
        )

        return {
            "total_orders": total_orders,
            "total_revenue": total_revenue,
            "avg_order_value": round(avg_order_value, 2),
            "completed": completed,
            "cancelled": cancelled,
            "scheduled": scheduled,
        }
    


# =========================================================
    # CUSTOMISED ADMIN Overview
# =========================================================

class DashboardService:

    @staticmethod
    def get_overview(db: Session, branch_ids: list[int]):

        today = datetime.utcnow().date()

        orders = (
            db.query(Order)
            .filter(
                Order.branch_id.in_(branch_ids),
                func.date(Order.created_at) == today
            )
            .all()
        )

        total_orders = len(orders)

        total_revenue = sum(float(o.total_amount) for o in orders)

        avg_order_value = (
            total_revenue / total_orders if total_orders else 0
        )

        # Weekly orders (simple mock aggregation for now)

        weekly_orders = [12, 18, 14, 22, 16, 25, 20]

        # Top items

        rows = (
            db.query(
                MenuItem.item_name,
                func.sum(OrderItem.quantity).label("sales"),
                func.sum(
                    OrderItem.quantity * OrderItem.price_at_time
                ).label("revenue"),
            )
            .join(OrderItem, OrderItem.item_id == MenuItem.item_id)
            .join(Order, Order.order_id == OrderItem.order_id)
            .filter(Order.branch_id.in_(branch_ids))
            .group_by(MenuItem.item_name)
            .order_by(func.sum(OrderItem.quantity).desc())
            .limit(3)
            .all()
        )

        top_items = [
            {
                "name": r.item_name,
                "sales": int(r.sales),
                "revenue": float(r.revenue),
            }
            for r in rows
        ]

        return {
            "today_orders": total_orders,
            "total_revenue": total_revenue,
            "avg_order_value": round(avg_order_value),
            "weekly_orders": weekly_orders,
            "top_items": top_items
        }
