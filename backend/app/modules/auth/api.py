from fastapi import APIRouter, Depends, HTTPException, Response, Request
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.core.config import settings

from app.modules.auth.schemas import (
    SendOTPRequest,
    VerifyOTPRequest,
    TokenResponse,
    SignupInitRequest,
    SignupVerifyRequest,
)

from app.modules.auth.service import AuthService, REFRESH_TOKEN_EXPIRE_DAYS


router = APIRouter(
    prefix="/auth",
    tags=["Auth"],
)


# ============================================================
# REFRESH COOKIE CONFIG
# ============================================================

REFRESH_COOKIE_NAME = "offo_refresh_token"

REFRESH_COOKIE_MAX_AGE = (
    REFRESH_TOKEN_EXPIRE_DAYS * 24 * 60 * 60
)


def set_refresh_cookie(
    response: Response,
    refresh_token: str,
):
    """
    Store refresh token in a secure HttpOnly cookie.

    The browser stores this cookie, but JavaScript cannot
    access document.cookie for this token.
    """

    is_production = (
        settings.ENVIRONMENT == "production"
    )

    response.set_cookie(
        key=REFRESH_COOKIE_NAME,
        value=refresh_token,
        max_age=REFRESH_COOKIE_MAX_AGE,
        httponly=True,
        secure=False,
        samesite="lax",
        path="/",
    )


def clear_refresh_cookie(
    response: Response,
):
    response.delete_cookie(
        key=REFRESH_COOKIE_NAME,
        httponly=True,
        secure=(
            settings.ENVIRONMENT == "production"
        ),
        samesite="lax",
        path="/",
    )


# ============================================================
# SIGNUP INIT
# ============================================================

@router.post("/signup/init")
def signup_init(
    data: SignupInitRequest,
    db: Session = Depends(get_db),
):
    AuthService.signup_init(
        db=db,
        mobile=data.phone,
        first_name=data.first_name,
        last_name=data.last_name,
    )

    return {
        "status": "otp_sent"
    }


# ============================================================
# SIGNUP VERIFY
# ============================================================

@router.post(
    "/signup/verify",
    response_model=TokenResponse,
)
def signup_verify(
    data: SignupVerifyRequest,
    response: Response,
    db: Session = Depends(get_db),
):
    tokens = AuthService.signup_verify(
        db=db,
        mobile=data.phone,
        otp=data.otp,
    )

    set_refresh_cookie(
        response=response,
        refresh_token=tokens["refresh_token"],
    )

    return {
        "access_token": tokens["access_token"],
        "token_type": "bearer",
    }


# ============================================================
# SEND LOGIN OTP
# ============================================================

@router.post("/send-otp")
def send_otp(
    data: SendOTPRequest,
    db: Session = Depends(get_db),
):
    AuthService.send_otp(
        db,
        data.mobile_number,
    )

    return {
        "message": "OTP sent successfully"
    }


# ============================================================
# VERIFY LOGIN OTP
# ============================================================

@router.post(
    "/verify-otp",
    response_model=TokenResponse,
)
def verify_otp(
    data: VerifyOTPRequest,
    response: Response,
    db: Session = Depends(get_db),
):
    tokens = AuthService.verify_otp(
        db,
        data.mobile_number,
        data.otp,
    )

    set_refresh_cookie(
        response=response,
        refresh_token=tokens["refresh_token"],
    )

    return {
        "access_token": tokens["access_token"],
        "token_type": "bearer",
    }


# ============================================================
# REFRESH ACCESS TOKEN
# ============================================================

@router.post(
    "/refresh",
    response_model=TokenResponse,
)
def refresh_token(
    request: Request,
    response: Response,
    db: Session = Depends(get_db),
):
    refresh_token_value = request.cookies.get(
        REFRESH_COOKIE_NAME
    )

    if not refresh_token_value:
        raise HTTPException(
            status_code=401,
            detail="Refresh session not found",
        )

    tokens = AuthService.refresh_access_token(
        db=db,
        refresh_token=refresh_token_value,
    )

    # --------------------------------------------------------
    # Replace old refresh cookie with rotated token
    # --------------------------------------------------------

    set_refresh_cookie(
        response=response,
        refresh_token=tokens["refresh_token"],
    )

    return {
        "access_token": tokens["access_token"],
        "token_type": "bearer",
    }


# ============================================================
# LOGOUT
# ============================================================

@router.post("/logout")
def logout(
    request: Request,
    response: Response,
    db: Session = Depends(get_db),
):
    refresh_token_value = request.cookies.get(
        REFRESH_COOKIE_NAME
    )

    AuthService.logout(
        db=db,
        refresh_token=refresh_token_value,
    )

    clear_refresh_cookie(
        response
    )

    return {
        "message": "Logged out successfully"
    }