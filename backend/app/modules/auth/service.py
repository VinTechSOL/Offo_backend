import random
from datetime import datetime, timedelta, timezone
import jwt

from sqlalchemy.orm import Session
from app.core.redis import redis_client
from app.core.config import settings
from app.modules.auth.constants import (
    OTP_TTL_SECONDS,
    REDIS_OTP_PREFIX,
)
from app.modules.auth.repository import AuthRepository


class AuthService:

    @staticmethod
    def send_otp(mobile: str):
        otp = str(random.randint(100000, 999999))

        redis_client.setex(
            f"{REDIS_OTP_PREFIX}{mobile}",
            OTP_TTL_SECONDS,
            otp
        )

        # TODO: Integrate MSG91 here
        print(f"[DEV OTP] {mobile} -> {otp}")

        return True

    @staticmethod
    def verify_otp(db: Session, mobile: str, otp: str):
        redis_key = f"{REDIS_OTP_PREFIX}{mobile}"
        cached_otp = redis_client.get(redis_key)

        if not cached_otp or cached_otp != otp:
            raise ValueError("Invalid or expired OTP")

        redis_client.delete(redis_key)

        user = AuthRepository.get_user_by_mobile(db, mobile)
        if not user:
            user = AuthRepository.create_user(db, mobile)
        else:
            AuthRepository.mark_verified(db, user)

        db.commit()  # important

        token = AuthService._generate_jwt(user.user_id)
        return token

    @staticmethod
    def _generate_jwt(user_id: int):
        now = datetime.now(timezone.utc)

        payload = {
            "sub": str(user_id),
            "iat": now,
            "exp": now + timedelta(minutes=30),
        }

        return jwt.encode(
            payload,
            settings.JWT_SECRET,
            algorithm=settings.JWT_ALGORITHM
        )
