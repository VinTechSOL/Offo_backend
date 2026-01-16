from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from jose import jwt
from datetime import datetime, timedelta
from app.core.config import settings
from app.core.database import get_db
from app.modules.staff.schemas import StaffLoginRequest, StaffLoginResponse
from app.modules.staff.service import StaffAuthService
from app.modules.staff.repository import StaffRepository
from app.modules.staff.service import StaffAuthService
from app.core.security import get_current_staff

router = APIRouter(prefix="/staff/auth", tags=["Staff Auth"])


@router.post("/login")
def staff_login(username: str, password: str, db: Session = Depends(get_db)):
    staff = StaffRepository.get_by_username(db, username)

    if not staff or not StaffAuthService.verify_password(password, staff.password_hash):
        raise HTTPException(status_code=401, detail="Invalid credentials")

    payload = {
        "staff_id": staff.staff_id,
        "type": "staff",
        "role_id": staff.role_id,
        "exp": datetime.utcnow() + timedelta(hours=8)
    }

    token = jwt.encode(payload, settings.JWT_SECRET, algorithm=settings.JWT_ALGORITHM)
    return {"access_token": token}

@router.get("/me")
def get_my_profile(staff=Depends(get_current_staff)):
    return {
        "staff_id": staff.staff_id,
        "username": staff.username,
        "role": staff.role.role_name,
        "branch_id": staff.branch_id,
    }