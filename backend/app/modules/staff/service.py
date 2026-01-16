from fastapi import HTTPException, status
from passlib.context import CryptContext
from datetime import datetime, timedelta, timezone
from jose import jwt, JWTError
from sqlalchemy.orm import Session
from app.core.config import settings
from app.modules.staff.repository import StaffRepository
from app.modules.staff.models import Staff

pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")


class StaffAuthService:

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
        staff = Staff(
            first_name=first_name,
            last_name=last_name,
            username=username,
            password_hash=pwd_context.hash(password),
            role_id=role_id,
            branch_id=branch_id
        )
        return StaffRepository.create(db, staff)

    @staticmethod
    def verify_password(password: str, hashed: str) -> bool:

        if len(password.encode("utf-8")) > 72:
            return False
        
        return pwd_context.verify(password, hashed)

    @staticmethod
    def login(db, username: str, password: str):
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
