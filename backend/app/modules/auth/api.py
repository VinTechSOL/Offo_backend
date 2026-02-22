from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.modules.auth.schemas import SendOTPRequest, VerifyOTPRequest, TokenResponse,SignupInitRequest,SignupVerifyRequest
from app.modules.auth.service import AuthService

router = APIRouter(prefix="/auth", tags=["Auth"])



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
    return {"status": "otp_sent"}


@router.post("/signup/verify", response_model=TokenResponse)
def signup_verify(
    data: SignupVerifyRequest,
    db: Session = Depends(get_db),
):
    token = AuthService.signup_verify(
        db=db,
        mobile=data.phone,
        otp=data.otp,
    )
    return {"access_token": token}


@router.post("/send-otp")
def send_otp(data: SendOTPRequest, db: Session = Depends(get_db)):
    AuthService.send_otp(db,data.mobile_number)
    return {"message": "OTP sent successfully"}


@router.post("/verify-otp", response_model=TokenResponse)
def verify_otp(data: VerifyOTPRequest, db: Session = Depends(get_db)):
    try:
        token = AuthService.verify_otp(db, data.mobile_number, data.otp)
        return {"access_token": token}
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    

