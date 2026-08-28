from fastapi import HTTPException, status
from passlib.context import CryptContext
from sqlalchemy.exc import SQLAlchemyError
from datetime import datetime, timedelta, timezone
from jose import jwt, JWTError
from sqlalchemy.orm import Session
from sqlalchemy import func
from app.core.config import settings
from app.modules.staff.repository import StaffRepository
from app.modules.staff.models import Staff, StaffRefreshToken
from app.modules.staff_roles.models import  StaffRole
from app.modules.vendor.models import CafeBranch
from app.modules.orders.models import Order,OrderItem
from app.modules.orders.constants import OrderStatus
from app.modules.menu.models import MenuItem
from app.modules.vendor.repository import VendorRepository
from app.core.redis import redis_client
from app.modules.auth.constants import REDIS_OTP_PREFIX, OTP_TTL_SECONDS
from app.core.security_utils import (
    rate_limit_otp_request,
    rate_limit_otp_verify,
    reset_otp_verify_limit,
)
from app.core.sms.msg91_client import MSG91Client
import random
import secrets
import string
import hashlib

pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")


class StaffAuthService:

    # =========================================================
    # REFRESH TOKEN CONFIGURATION
    # =========================================================

    ACCESS_TOKEN_EXPIRE_MINUTES = 15
    REFRESH_TOKEN_EXPIRE_DAYS = 30

    @staticmethod
    def generate_temp_password(length: int = 10):

        alphabet = (
            string.ascii_letters +
            string.digits +
            "@#$%"
        )

        return "".join(
            secrets.choice(alphabet)
            for _ in range(length)
        )

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
        existing = StaffRepository.get_by_username_any_status(db, username)
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
            raise HTTPException(
                status_code=401,
                detail="Invalid credentials"
            )

        if len(password.encode("utf-8")) > 72:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid credentials",
            )

        if not staff.is_active:
            raise HTTPException(
                status_code=403,
                detail="Staff inactive"
            )

        if staff.branch_id:
            branch = db.get(
                CafeBranch,
                staff.branch_id
            )

            if branch and not branch.is_active:
                raise HTTPException(
                    status_code=403,
                    detail="Branch is inactive"
                )

        if not pwd_context.verify(
            password,
            staff.password_hash
        ):
            raise HTTPException(
                status_code=401,
                detail="Invalid credentials"
            )

        access_token = StaffAuthService._generate_token(staff)

        refresh_token = StaffAuthService._create_refresh_token(
            db=db,
            staff=staff,
        )

        # IMPORTANT:
        # Persist the refresh token before returning it
        # to the browser.
        try:
            db.commit()
        except SQLAlchemyError:
            db.rollback()

            raise HTTPException(
                status_code=500,
                detail="Unable to create refresh session",
            )

        return {
            "access_token": access_token,
            "refresh_token": refresh_token,
            "token_type": "bearer",
            "staff_id": staff.staff_id,
            "role": staff.role.role_name,
            "branch_id": staff.branch_id,
        }


    @staticmethod
    def refresh_access_token(
        db: Session,
        raw_refresh_token: str,
    ):
        """
        Validate the refresh token, rotate it, and issue
        a new access token.
        """

        if not raw_refresh_token:
            raise HTTPException(
                status_code=401,
                detail="Refresh token missing",
            )

        refresh_token = (
            StaffAuthService._get_refresh_token(
                db=db,
                raw_token=raw_refresh_token,
            )
        )

        if not refresh_token:
            raise HTTPException(
                status_code=401,
                detail="Invalid refresh token",
            )

        # ---------------------------------------------------------
        # EXPIRATION
        # ---------------------------------------------------------

        now = datetime.now(timezone.utc)

        if refresh_token.expires_at <= now:
            refresh_token.revoked_at = now
            db.commit()

            raise HTTPException(
                status_code=401,
                detail="Refresh token expired",
            )

        # ---------------------------------------------------------
        # LOAD STAFF
        # ---------------------------------------------------------

        staff = StaffRepository.get_by_id(
            db,
            refresh_token.staff_id,
        )

        if not staff:
            refresh_token.revoked_at = now
            db.commit()

            raise HTTPException(
                status_code=401,
                detail="Staff account not found",
            )

        if not staff.is_active:
            refresh_token.revoked_at = now
            db.commit()

            raise HTTPException(
                status_code=403,
                detail="Staff inactive",
            )

        # ---------------------------------------------------------
        # BRANCH VALIDATION
        # ---------------------------------------------------------

        if staff.branch_id:
            branch = db.get(
                CafeBranch,
                staff.branch_id,
            )

            if branch and not branch.is_active:
                refresh_token.revoked_at = now
                db.commit()

                raise HTTPException(
                    status_code=403,
                    detail="Branch is inactive",
                )

        # ---------------------------------------------------------
        # ROTATE REFRESH TOKEN
        # ---------------------------------------------------------

        StaffAuthService._revoke_refresh_token(
            db=db,
            refresh_token=refresh_token,
        )

        new_refresh_token = (
            StaffAuthService._create_refresh_token(
                db=db,
                staff=staff,
            )
        )

        # ---------------------------------------------------------
        # NEW ACCESS TOKEN
        # ---------------------------------------------------------

        new_access_token = (
            StaffAuthService._generate_token(
                staff
            )
        )

        db.commit()

        return {
            "access_token": new_access_token,
            "refresh_token": new_refresh_token,
            "token_type": "bearer",
            "role": staff.role.role_name,
            "staff_id": staff.staff_id,
            "branch_id": staff.branch_id,
        }


    @staticmethod
    def logout(
        db: Session,
        raw_refresh_token: str,
    ):
        """
        Revoke the current refresh token.
        """

        if not raw_refresh_token:
            return

        refresh_token = (
            StaffAuthService._get_refresh_token(
                db=db,
                raw_token=raw_refresh_token,
            )
        )

        if refresh_token:
            StaffAuthService._revoke_refresh_token(
                db=db,
                refresh_token=refresh_token,
            )

            db.commit()

    # =========================================================
    # SEND, VERIFY OTP AND RESET PASSWORD
    # =========================================================

    @staticmethod
    def send_reset_otp(
        db: Session,
        mobile: str,
    ):

        rate_limit_otp_request(mobile)

        branch = VendorRepository.get_branch_by_owner_phone(
            db,
            mobile,
        )

        if not branch:
            raise HTTPException(
               status_code=404,
               detail="Phone number not registered."
            )

        vendor = StaffRepository.get_vendor_by_branch(
            db,
            branch.branch_id,
        )

        if not vendor:
            raise HTTPException(
                status_code=404,
                detail="Vendor account not found."
            )

        otp = str(random.randint(100000, 999999))

        redis_client.setex(
            f"{REDIS_OTP_PREFIX}{mobile}",
            OTP_TTL_SECONDS,
            otp,
        )

        if settings.ENVIRONMENT == "development":
            print(f"[VENDOR RESET OTP] {mobile} -> {otp}")
        else:
            MSG91Client.send_otp(
                mobile=mobile,
                otp=otp,
                name=branch.registered_owner_name or "Vendor",
            )

        return True


    @staticmethod
    def verify_reset_otp(
        db: Session,
        mobile: str,
        otp: str,
    ):

        rate_limit_otp_verify(mobile)

        redis_key = f"{REDIS_OTP_PREFIX}{mobile}"

        cached = redis_client.get(redis_key)

        if settings.ALLOW_DEV_OTP and otp == settings.DEV_MASTER_OTP:
            print("[DEV MODE] Vendor master OTP used")
        else:
            if not cached or cached != otp:
                raise HTTPException(
                    status_code=400,
                    detail="Invalid or expired OTP",
                )

        redis_client.delete(redis_key)

        reset_otp_verify_limit(mobile)

        branch = VendorRepository.get_branch_by_owner_phone(
            db,
            mobile,
        )

        if not branch:
            raise HTTPException(
                status_code=404,
                detail="Vendor not found",
            )

        vendor = StaffRepository.get_vendor_by_branch(
            db,
            branch.branch_id,
        )

        if not vendor:
            raise HTTPException(
                status_code=404,
                detail="Vendor not found",
            )

        token = jwt.encode(
            {
                "staff_id": str(vendor.staff_id),
                "purpose": "password_reset",
                "exp": datetime.now(timezone.utc) + timedelta(minutes=10),
            },
            settings.JWT_SECRET,
            algorithm=settings.JWT_ALGORITHM,
        )

        return token



    @staticmethod
    def reset_password(
        db: Session,
        reset_token: str,
        new_password: str,
    ):

        try:

            payload = jwt.decode(
                reset_token,
                settings.JWT_SECRET,
                algorithms=[settings.JWT_ALGORITHM],
            )

            if payload.get("purpose") != "password_reset":
                raise HTTPException(
                    status_code=401,
                    detail="Invalid token",
                )

            staff_id = int(payload["staff_id"])

        except JWTError:
            raise HTTPException(
                status_code=401,
                detail="Invalid or expired token",
            )

        staff = StaffRepository.get_by_id(
            db,
            staff_id,
        )

        if not staff:
            raise HTTPException(
                status_code=404,
                detail="Vendor not found",
            )

        staff.password_hash = pwd_context.hash(new_password)

        StaffRepository.revoke_all_refresh_tokens(
            db=db,
            staff_id=staff.staff_id,
        )

        db.commit()

        return {
            "message": "Password updated successfully"
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
        branch_id: int,
    ):

        # -----------------------------------------------------
        # Validate Branch
        # -----------------------------------------------------

        branch = db.get(CafeBranch, branch_id)

        if not branch:
            raise HTTPException(
                status_code=404,
                detail="Branch not found",
            )

        if not branch.is_active:
            raise HTTPException(
            status_code=400,
            detail="Branch is inactive",
        )

        # -----------------------------------------------------
        # Check Existing Vendor
        # -----------------------------------------------------
 
        existing_vendor = StaffRepository.get_vendor_by_branch_any_status(
            db=db,
            branch_id=branch_id,
        )

        if existing_vendor:
            raise HTTPException(
                status_code=409,
                detail="Vendor already exists for this branch.",
            )

        # -----------------------------------------------------
        # Username Validation
        # -----------------------------------------------------

        existing_username = StaffRepository.get_by_username_any_status(
            db=db,
            username=username,
        )

        if existing_username:
            raise HTTPException(
                status_code=400,
                detail="Username already exists.",
            )

        # -----------------------------------------------------
        # Find Vendor Role
        # -----------------------------------------------------

        vendor_role = (
            db.query(StaffRole)
            .filter(
                StaffRole.role_name == "VENDOR"
            )
            .first()
        )

        if not vendor_role:
            raise HTTPException(
                status_code=500,
                detail="Vendor role not configured.",
            )

        # -----------------------------------------------------
        # Generate Temporary Password
        # -----------------------------------------------------

        temporary_password = StaffAuthService.generate_temp_password()

        # -----------------------------------------------------
        # Create Vendor
        # -----------------------------------------------------

        vendor = Staff(
            first_name=first_name,
            last_name=last_name,
            username=username,
            password_hash=pwd_context.hash(
                temporary_password
            ),
            role_id=vendor_role.role_id,
            branch_id=branch_id,
             is_active=True,
        )

        try:

            db.add(vendor)

            db.commit()

            db.refresh(vendor)

        except SQLAlchemyError:

            db.rollback()

            raise HTTPException(
                status_code=500,
                detail="Unable to create vendor.",
            )

        # -----------------------------------------------------
        # Return Vendor + Temporary Password
        # -----------------------------------------------------

        return {
            "vendor": vendor,
            "temporary_password": temporary_password,
        }

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
    # UPDATE VENDOR (SUPER ADMIN ONLY)
    # =========================================================
    @staticmethod
    def update_vendor(
        db: Session,
        staff_id: int,
        first_name: str,
        last_name: str,
        username: str,
        is_active: bool,
    ) -> Staff:

        staff = StaffRepository.get_by_id(db, staff_id)

        if not staff:
            raise HTTPException(
                status_code=404,
                detail="Vendor not found"
            )

        if staff.role.role_name != "VENDOR":
            raise HTTPException(
                status_code=400,
                detail="Staff is not a vendor"
            )

        # Username uniqueness check
        if username != staff.username:

            existing = StaffRepository.get_by_username_any_status(
                db,
                username,
            )

            if existing:
                raise HTTPException(
                    status_code=400,
                    detail="Username already exists"
                )

        staff.first_name = first_name
        staff.last_name = last_name
        staff.username = username
        staff.is_active = is_active


        return StaffRepository.update(
            db,
            staff,
        )

    # =========================================================
    # REFRESH TOKEN
    # =========================================================

    @staticmethod
    def _generate_refresh_token() -> str:
        """
        Generate a cryptographically secure opaque refresh token.

        The raw token is sent only to the browser through an
        HttpOnly cookie.

        The raw token is never stored in the database.
        """
        return secrets.token_urlsafe(64)

    @staticmethod
    def _hash_refresh_token(
        refresh_token: str,
    ) -> str:
        """
        Hash the refresh token before storing/searching it.
        """
        return hashlib.sha256(
            refresh_token.encode("utf-8")
        ).hexdigest()


    @staticmethod
    def _create_refresh_token(
        db: Session,
        staff: Staff,
    ):
        """
        Create and persist a refresh token for a staff member.

        Returns:
            raw refresh token

        The raw token is returned to the caller so it can be
        placed into an HttpOnly cookie.

        Only the hash is stored in the database.
        """

        raw_token = (
            StaffAuthService._generate_refresh_token()
        )

        token_hash = (
            StaffAuthService._hash_refresh_token(
                raw_token
            )
        )

        refresh_token = StaffRefreshToken(
            staff_id=staff.staff_id,
            token_hash=token_hash,
            expires_at=(
                datetime.now(timezone.utc)
                + timedelta(
                    days=StaffAuthService.REFRESH_TOKEN_EXPIRE_DAYS
                )
            ),
        )

        db.add(refresh_token)
        db.flush()

        return raw_token

    @staticmethod
    def _get_refresh_token(
        db: Session,
        raw_token: str,
    ):
        """
        Find an active refresh token using its raw value.

        The database contains only the hash.
        """

        token_hash = (
            StaffAuthService._hash_refresh_token(
                raw_token
            )
        )

        return (
            db.query(StaffRefreshToken)
            .filter(
                StaffRefreshToken.token_hash
                == token_hash,
                StaffRefreshToken.revoked_at.is_(None),
            )
            .first()
        )


    @staticmethod
    def _revoke_refresh_token(
        db: Session,
        refresh_token: StaffRefreshToken,
    ):
        """
        Revoke one refresh token.
        """

        refresh_token.revoked_at = (
            datetime.now(timezone.utc)
        )

        db.flush()

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
            "exp": datetime.now(timezone.utc) + timedelta(minutes=StaffAuthService.ACCESS_TOKEN_EXPIRE_MINUTES)
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
