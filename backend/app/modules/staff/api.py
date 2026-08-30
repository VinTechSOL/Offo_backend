from fastapi import APIRouter, Depends, HTTPException, status,Query,Request, Response
from sqlalchemy.orm import Session
from datetime import date
from app.core.database import get_db
from app.core.security import get_current_staff
from app.modules.staff.schemas import (
    StaffLoginRequest,
    VendorCreateRequest,
    VendorResponse,
    VendorCreateResponse,
    VendorUpdateRequest,
    StaffSendOTPRequest,
    StaffVerifyOTPRequest,
    StaffVerifyOTPResponse,
    StaffResetPasswordRequest,
    StaffResetPasswordResponse,
    StaffLoginResponse,
    StaffRefreshResponse,
    StaffChangePasswordRequest,
    StaffChangePasswordResponse
)
from app.modules.staff.service import StaffAuthService
from app.modules.orders.repository import OrderRepository
from app.modules.staff.service import AdminReportService,DashboardService


router = APIRouter(prefix="/staff", tags=["Staff Auth"])


# =========================================================
# LOGIN (USED BY SUPER ADMIN + VENDOR)
# =========================================================
@router.post("/auth/login", response_model=StaffLoginResponse)
def staff_login(
    data: StaffLoginRequest,
    response: Response,
    db: Session = Depends(get_db),
):
    result = StaffAuthService.login(
        db=db,
        username=data.username,
        password=data.password,
    )

    refresh_token = result.pop(
        "refresh_token"
    )

    response.set_cookie(
        key="staff_refresh_token",
        value=refresh_token,
        httponly=True,
        secure=True, 
        domain=".offo.co.in",
        samesite="lax",
        max_age=30 * 24 * 60 * 60,
        path="/staff/auth",
    )
    return result

# =========================================================
# Refresh token for staff
# =========================================================
@router.post("/auth/refresh", response_model=StaffRefreshResponse)
def refresh_access_token(
    request: Request,
    response: Response,
    db: Session = Depends(get_db),
):
    print("\n========== REFRESH DEBUG ==========")
    print("ALL COOKIES:", request.cookies)
    print(
        "STAFF REFRESH COOKIE:",
        request.cookies.get("staff_refresh_token")
    )
    print("===================================\n")

    refresh_token = request.cookies.get(
        "staff_refresh_token"
    )

    result = StaffAuthService.refresh_access_token(
        db=db,
        raw_refresh_token=refresh_token,
    )

    new_refresh_token = result.pop("refresh_token")

    response.set_cookie(
        key="staff_refresh_token",
        value=new_refresh_token,
        httponly=True,
        secure=True,
        domain=".offo.co.in",
        samesite="lax",
        max_age=30 * 24 * 60 * 60,
        path="/staff/auth",
    )

    return result
# =========================================================
# SEND RESET OTP (VENDOR)
# =========================================================

@router.post("/auth/send-reset-otp")
def send_reset_otp(
    payload: StaffSendOTPRequest,
    db: Session = Depends(get_db),
):
    StaffAuthService.send_reset_otp(
        db=db,
        mobile=payload.mobile_number,
    )

    return {
        "message": "OTP sent successfully"
    }

# =========================================================
# VERIFY RESET OTP (VENDOR)
# =========================================================

@router.post(
    "/auth/verify-reset-otp",
    response_model=StaffVerifyOTPResponse,
)
def verify_reset_otp(
    payload: StaffVerifyOTPRequest,
    db: Session = Depends(get_db),
):
    reset_token = StaffAuthService.verify_reset_otp(
        db=db,
        mobile=payload.mobile_number,
        otp=payload.otp,
    )

    return {
        "reset_token": reset_token,
    }

# =========================================================
# RESET PASSWORD (VENDOR)
# =========================================================

@router.post(
    "/auth/reset-password",
    response_model=StaffResetPasswordResponse,
)
def reset_password(
    payload: StaffResetPasswordRequest,
    db: Session = Depends(get_db),
):
    return StaffAuthService.reset_password(
        db=db,
        reset_token=payload.reset_token,
        new_password=payload.new_password,
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
        "full_name": f"{staff.first_name}{staff.last_name}".strip(),
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
# CHANGE OWN PASSWORD - SUPER ADMIN
# =========================================================

@router.post(
    "/auth/change-password",
    response_model=StaffChangePasswordResponse,
)
def change_password(
    payload: StaffChangePasswordRequest,
    db: Session = Depends(get_db),
    current_staff=Depends(get_current_staff),
):

    if current_staff.role.role_name != "SUPER_ADMIN":
        raise HTTPException(
            status_code=403,
            detail="Only Super Admin can change password from this profile.",
        )

    return StaffAuthService.change_password(
        db=db,
        staff=current_staff,
        new_password=payload.new_password,
    )



# =========================================================
# CREATE VENDOR (SUPER ADMIN ONLY)
# =========================================================
@router.post("/vendors", response_model=VendorCreateResponse)
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
    start_date: date | None = Query(None),
    end_date: date | None = Query(None),
    db: Session = Depends(get_db),
):
    return AdminReportService.get_reports(
        db=db,
        branch_ids=branch_ids,
        range=range,
        start_date=start_date,
        end_date=end_date,
    )

# =========================================================
# Get Overview dashboard (SUPER ADMIN ONLY)
# =========================================================

@router.get("/dashboard-overview")
def get_dashboard_overview(
    branch_ids: list[int] = Query(...),
    db: Session = Depends(get_db),
):
    return DashboardService.get_overview(
        db=db,
        branch_ids=branch_ids,
    )

# =========================================================
# Logout
# =========================================================


@router.post("/auth/logout")
def staff_logout(
    request: Request,
    response: Response,
    db: Session = Depends(get_db),
):
    refresh_token = request.cookies.get(
        "staff_refresh_token"
    )

    StaffAuthService.logout(
        db=db,
        raw_refresh_token=refresh_token,
    )

    response.delete_cookie(
        key="staff_refresh_token",
        domain=".offo.co.in",
        path="/staff/auth",
    )

    return {
        "message": "Logged out successfully"
    }