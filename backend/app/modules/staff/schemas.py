from datetime import datetime

from pydantic import BaseModel, Field


# =========================================================
# LOGIN
# =========================================================

class StaffLoginRequest(BaseModel):
    username: str
    password: str


class StaffLoginResponse(BaseModel):
    access_token: str
    token_type: str = "Bearer"
    staff_id: int
    role: str
    branch_id: int | None = None

class StaffRefreshResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"
    staff_id: int
    role: str
    branch_id: int | None = None
# =========================================================
# VENDOR MANAGEMENT
# =========================================================

class VendorCreateRequest(BaseModel):
    first_name: str
    last_name: str
    username: str
    branch_id: int


class VendorUpdateRequest(BaseModel):
    first_name: str | None = Field(
        default=None,
        min_length=1,
        max_length=100,
    )

    last_name: str | None = Field(
        default=None,
        min_length=1,
        max_length=100,
    )

    username: str | None = Field(
        default=None,
        min_length=1,
        max_length=100,
    )

    is_active: bool | None = None


class VendorResponse(BaseModel):
    staff_id: int
    first_name: str
    last_name: str
    username: str
    branch_id: int
    is_active: bool
    created_at: datetime

    class Config:
        from_attributes = True

class VendorCreateResponse(BaseModel):
    vendor: VendorResponse
    temporary_password: str


# =========================================================
# FORGOT PASSWORD
# =========================================================

class StaffSendOTPRequest(BaseModel):
    mobile_number: str = Field(..., min_length=10, max_length=15)


class StaffVerifyOTPRequest(BaseModel):
    mobile_number: str = Field(..., min_length=10, max_length=15)
    otp: str = Field(..., min_length=4, max_length=6)


class StaffVerifyOTPResponse(BaseModel):
    reset_token: str


class StaffResetPasswordRequest(BaseModel):
    reset_token: str
    new_password: str = Field(..., min_length=6)


class StaffResetPasswordResponse(BaseModel):
    message: str


# =========================================================
# CHANGE PASSWORD
# =========================================================

class StaffChangePasswordRequest(BaseModel):
    new_password: str = Field(..., min_length=6, max_length=72)


class StaffChangePasswordResponse(BaseModel):
    message: str