import random
from datetime import datetime, timedelta, timezone
import jwt
from fastapi import HTTPException
from sqlalchemy.orm import Session
from app.core.redis import redis_client
from app.core.config import settings
from app.modules.auth.constants import (
    OTP_TTL_SECONDS,
    REDIS_OTP_PREFIX,
)
from app.modules.auth.repository import AuthRepository
from app.modules.auth.models import SignupSession
from app.core.security_utils import (rate_limit_otp_request,reset_otp_verify_limit,rate_limit_otp_verify,validate_name)



class AuthService:

    # -------------------------
    # LOGIN FLOW 
    # -------------------------
    @staticmethod
    def send_otp(db: Session, mobile: str):

        rate_limit_otp_request(mobile)

        user = AuthRepository.get_user_by_mobile(db,mobile)

        if not user:
            
            raise HTTPException(
                status_code=400,
                detail="Mobile number not registered. Please signup first."
            )
        
        
        otp = str(random.randint(100000, 999999))

        redis_client.setex(
            f"{REDIS_OTP_PREFIX}{mobile}",
            OTP_TTL_SECONDS,
            otp
        )

        # TODO: MSG91 integration
        print(f"[DEV OTP LOGIN] {mobile} -> {otp}")

        return True

    @staticmethod
    def verify_otp(db: Session, mobile: str, otp: str):

        rate_limit_otp_verify(mobile)

        redis_key = f"{REDIS_OTP_PREFIX}{mobile}"
        cached_otp = redis_client.get(redis_key)
        #temporary otp setup for testing,remove if statement in production

        if settings.ALLOW_DEV_OTP and otp == settings.DEV_MASTER_OTP:
            print("[DEV MODE] Master OTP used")
        else:
            if not cached_otp or cached_otp != otp:
               raise HTTPException(status_code=400,detail="Invalid or expired OTP")

        redis_client.delete(redis_key)
        reset_otp_verify_limit(mobile)

        user = AuthRepository.get_user_by_mobile(db, mobile)
        if not user:
            raise HTTPException(status_code=400,detail="Mobile number not registered")
        

        db.commit()

        return AuthService._generate_jwt(user.user_id)

    # -------------------------
    # SIGNUP FLOW 
    # -------------------------
    @staticmethod
    def signup_init(
        db: Session,
        mobile: str,
        first_name: str,
        last_name: str,
    ):
        rate_limit_otp_request(mobile)
        
        existing_user = AuthRepository.get_user_by_mobile(db,mobile)

        if existing_user:
            raise HTTPException(
                status_code=400,
                detail="Phone number already registered. Please login."
            )
        
        validate_name(first_name, "First name")
        validate_name(last_name,"Last name")
        
        otp = str(random.randint(100000, 999999))
        expires_at = datetime.now(timezone.utc) + timedelta(seconds=OTP_TTL_SECONDS)

        # Remove any old signup session
        db.query(SignupSession).filter(
            SignupSession.phone == mobile
        ).delete()

        signup = SignupSession(
            phone=mobile,
            first_name=first_name,
            last_name=last_name,
            otp=otp,
            expires_at=expires_at,
        )

        db.add(signup)
        db.commit()

        print(f"[DEV OTP SIGNUP] {mobile} -> {otp}")

        return True

    @staticmethod
    def signup_verify(db: Session, mobile: str, otp: str):
        rate_limit_otp_verify(mobile)
        
        # in production,no requirement of if and above signup none thing only use else 
        if settings.ALLOW_DEV_OTP and otp == settings.DEV_MASTER_OTP:
            print(f"[dev mode] master otp used for {mobile}")
            signup = db.query(SignupSession).filter(
                SignupSession.phone == mobile,
                SignupSession.expires_at >= datetime.now(timezone.utc),
            ).first()
        else:
            signup = (
              db.query(SignupSession)
              .filter(
                SignupSession.phone == mobile,
                SignupSession.otp == otp,
                SignupSession.expires_at >= datetime.now(timezone.utc),
              )
              .first()
            )

        if not signup:
            raise HTTPException(status_code=400, detail="Invalid or expired OTP")

        existing_user = AuthRepository.get_user_by_mobile(db, mobile)

        if existing_user:
            raise HTTPException(status_code=400, detail="Account already exists.Please login.")

        
        user = AuthRepository.create_user(
            db,
            mobile=mobile,
            first_name=signup.first_name,
            last_name=signup.last_name,
        )
        
        AuthRepository.mark_verified(db,user)

        signup.verified = True
        reset_otp_verify_limit(mobile)
        db.commit()

        return AuthService._generate_jwt(user.user_id)

    # -------------------------
    # JWT
    # -------------------------
    @staticmethod
    def _generate_jwt(user_id: int):
        now = datetime.now(timezone.utc)

        payload = {
            "sub": str(user_id),
            "type": "user",
            "iat": now,
            "exp": now + timedelta(minutes=30),
        }

        return jwt.encode(
            payload,
            settings.JWT_SECRET,
            algorithm=settings.JWT_ALGORITHM
        )
    

    
