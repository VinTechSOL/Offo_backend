from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.core.security import get_current_staff
from app.modules.staff.schemas import (
    StaffLoginRequest,
    VendorCreateRequest,
    VendorResponse,
)
from app.modules.staff.service import StaffAuthService


router = APIRouter(prefix="/staff", tags=["Staff Auth"])


# =========================================================
# LOGIN (USED BY SUPER ADMIN + VENDOR)
# =========================================================
@router.post("/auth/login")
def staff_login(
    data: StaffLoginRequest,
    db: Session = Depends(get_db)
):
    return StaffAuthService.login(
        db=db,
        username=data.username,
        password=data.password
    )


# =========================================================
# GET CURRENT PROFILE
# =========================================================
@router.get("/auth/me")
def get_my_profile(
    staff=Depends(get_current_staff)
):
    return {
        "staff_id": staff.staff_id,
        "username": staff.username,
        "role": staff.role.role_name,
        "branch_id": staff.branch_id,
        "is_active": staff.is_active,
    }


# =========================================================
# CREATE VENDOR (SUPER ADMIN ONLY)
# =========================================================
@router.post("/vendors", response_model=VendorResponse)
def create_vendor(
    payload: VendorCreateRequest,
    db: Session = Depends(get_db),
    current_staff=Depends(get_current_staff),
):
    if current_staff.role.role_name != "SUPER_ADMIN":
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Access denied. Only super admin allowed."
        )

    vendor = StaffAuthService.create_vendor(
        db=db,
        first_name=payload.first_name,
        last_name=payload.last_name,
        username=payload.username,
        password=payload.password,
        branch_id=payload.branch_id,
    )

    return vendor


# =========================================================
# GET VENDOR BY BRANCH (SUPER ADMIN ONLY)
# =========================================================
@router.get("/vendors")
def get_vendor_by_branch(
    branch_id: int,
    db: Session = Depends(get_db),
    current_staff=Depends(get_current_staff),
):
    if current_staff.role.role_name != "SUPER_ADMIN":
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Access denied."
        )

    vendor = StaffAuthService.get_vendor_by_branch(
        db=db,
        branch_id=branch_id
    )

    if not vendor:
        return None

    return {
        "staff_id": vendor.staff_id,
        "first_name": vendor.first_name,
        "last_name": vendor.last_name,
        "username": vendor.username,
        "branch_id": vendor.branch_id,
        "is_active": vendor.is_active,
        "created_at": vendor.created_at,
    }


# =========================================================
# RESET VENDOR PASSWORD (SUPER ADMIN ONLY)
# =========================================================
@router.patch("/vendors/{staff_id}/reset-password")
def reset_vendor_password(
    staff_id: int,
    db: Session = Depends(get_db),
    current_staff=Depends(get_current_staff),
):
    if current_staff.role.role_name != "SUPER_ADMIN":
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Access denied."
        )

    new_password = StaffAuthService.reset_vendor_password(
        db=db,
        staff_id=staff_id
    )

    return {
        "message": "Password reset successfully",
        "new_password": new_password
    }