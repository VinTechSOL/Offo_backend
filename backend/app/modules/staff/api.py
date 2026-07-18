from fastapi import APIRouter, Depends, HTTPException, status,Query
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.core.security import get_current_staff
from app.modules.staff.schemas import (
    StaffLoginRequest,
    VendorCreateRequest,
    VendorResponse,
    VendorUpdateRequest,
)
from app.modules.staff.service import StaffAuthService
from app.modules.orders.repository import OrderRepository
from app.modules.staff.service import AdminReportService,DashboardService

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
    staff = Depends(get_current_staff)
):

    role_name = staff.role.role_name

    # Determine access scope
    if staff.role.cafe_id is None:
        access_scope = "GLOBAL"
    elif staff.branch_id is None:
        access_scope = "CAFE"
    else:
        access_scope = "BRANCH"

    response = {
        "staff_id": staff.staff_id,
        "username": staff.username,
        "full_name": f"{staff.first_name}{staff.last_name}",
        "role": role_name,
        "access_scope": access_scope,
        "is_active": staff.is_active,
        "created_at": staff.created_at,
    }

    # Only include branch_id for branch staff
    if access_scope == "BRANCH":
        response["branch_id"] = staff.branch_id

    return response
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


# =========================================================
# UPDATE VENDOR (SUPER ADMIN ONLY)
# =========================================================

@router.patch(
    "/vendors/{staff_id}",
    response_model=VendorResponse,
)
def update_vendor(
    staff_id: int,
    payload: VendorUpdateRequest,
    db: Session = Depends(get_db),
    current_staff=Depends(get_current_staff),
):

    if current_staff.role.role_name != "SUPER_ADMIN":
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Access denied."
        )

    return StaffAuthService.update_vendor(
        db=db,
        staff_id=staff_id,
        first_name=payload.first_name,
        last_name=payload.last_name,
        username=payload.username,
        is_active=payload.is_active,
    )


# =========================================================
# Get customised customers details (SUPER ADMIN ONLY)
# =========================================================

@router.get("/get-customised-user-info")
def get_users_by_branch(
    branch_ids: list[int] = Query(...),
    db: Session = Depends(get_db)
):
    return OrderRepository.get_users_by_branches(db, branch_ids)


# =========================================================
# Get customised users reports (SUPER ADMIN ONLY)
# =========================================================


@router.get("/customised-reports")
def get_reports(
    branch_ids: list[int] = Query(...),
    range: str = Query("month"),
    db: Session = Depends(get_db)
):
    return AdminReportService.get_reports(
        db=db,
        branch_ids=branch_ids,
        range=range
    )


# =========================================================
# Get Overview dashboard (SUPER ADMIN ONLY)
# =========================================================

@router.get("/dashboard-overview")
def get_dashboard_overview(
    branch_ids: list[int] = Query(...),
    db: Session = Depends(get_db)
):
    return DashboardService.get_overview(
        db=db,
        branch_ids=branch_ids
    )