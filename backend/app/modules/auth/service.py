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
from app.modules.auth.token_utils import (
    generate_refresh_token,
    hash_refresh_token,
)
from app.core.security_utils import (
    rate_limit_otp_request,
    reset_otp_verify_limit,
    rate_limit_otp_verify,
    validate_name,
)
from app.core.sms.msg91_client import MSG91Client


# ============================================================
# SESSION CONFIG
# ============================================================

ACCESS_TOKEN_EXPIRE_MINUTES = 15
REFRESH_TOKEN_EXPIRE_DAYS = 30


class AuthService:

    # ============================================================
    # LOGIN FLOW
    # ============================================================

    @staticmethod
    def send_otp(
        db: Session,
        mobile: str,
    ):

        rate_limit_otp_request(mobile)

        user = AuthRepository.get_user_by_mobile(
            db,
            mobile,
        )

        if not user:
            raise HTTPException(
                status_code=400,
                detail=(
                    "Mobile number not registered. "
                    "Please signup first."
                ),
            )

        otp = str(
            random.randint(
                100000,
                999999,
            )
        )

        redis_client.setex(
            f"{REDIS_OTP_PREFIX}{mobile}",
            OTP_TTL_SECONDS,
            otp,
        )

        # --------------------------------------------------------
        # Development
        # --------------------------------------------------------

        if settings.ENVIRONMENT == "development":

            print(
                f"[DEV OTP LOGIN] "
                f"{mobile} -> {otp}"
            )

        # --------------------------------------------------------
        # Production
        # --------------------------------------------------------

        else:

            user_name = user.first_name or "User"

            MSG91Client.send_otp(
                mobile=mobile,
                otp=otp,
                name=user_name,
            )

        return True

    # ============================================================
    # VERIFY LOGIN OTP
    # ============================================================

    @staticmethod
    def verify_otp(
        db: Session,
        mobile: str,
        otp: str,
    ):

        rate_limit_otp_verify(mobile)

        redis_key = f"{REDIS_OTP_PREFIX}{mobile}"

        cached_otp = redis_client.get(
            redis_key
        )

        # --------------------------------------------------------
        # Development master OTP
        # --------------------------------------------------------

        if (
            settings.ALLOW_DEV_OTP
            and otp == settings.DEV_MASTER_OTP
        ):

            print(
                "[DEV MODE] Master OTP used"
            )

        else:

            if (
                not cached_otp
                or cached_otp != otp
            ):

                raise HTTPException(
                    status_code=400,
                    detail="Invalid or expired OTP",
                )

        # --------------------------------------------------------
        # OTP successfully verified
        # --------------------------------------------------------

        redis_client.delete(
            redis_key
        )

        reset_otp_verify_limit(
            mobile
        )

        user = AuthRepository.get_user_by_mobile(
            db,
            mobile,
        )

        if not user:

            raise HTTPException(
                status_code=400,
                detail=(
                    "Mobile number not registered"
                ),
            )

        # --------------------------------------------------------
        # Create authentication session
        # --------------------------------------------------------

        return AuthService.create_auth_session(
            db=db,
            user_id=user.user_id,
        )

    # ============================================================
    # SIGNUP INIT
    # ============================================================

    @staticmethod
    def signup_init(
        db: Session,
        mobile: str,
        first_name: str,
        last_name: str,
    ):

        rate_limit_otp_request(
            mobile
        )

        existing_user = (
            AuthRepository.get_user_by_mobile(
                db,
                mobile,
            )
        )

        if existing_user:

            raise HTTPException(
                status_code=400,
                detail=(
                    "Phone number already "
                    "registered. Please login."
                ),
            )

        validate_name(
            first_name,
            "First name",
        )

        validate_name(
            last_name,
            "Last name",
        )

        otp = str(
            random.randint(
                100000,
                999999,
            )
        )

        expires_at = (
            datetime.now(timezone.utc)
            + timedelta(
                seconds=OTP_TTL_SECONDS
            )
        )

        # --------------------------------------------------------
        # Remove old signup session
        # --------------------------------------------------------

        db.query(
            SignupSession
        ).filter(
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

        # --------------------------------------------------------
        # Send OTP
        # --------------------------------------------------------

        if settings.ENVIRONMENT == "development":

            print(
                f"[DEV OTP SIGNUP] "
                f"{mobile} -> {otp}"
            )

        else:

            MSG91Client.send_otp(
                mobile=mobile,
                otp=otp,
                name=first_name,
            )

        return True

    # ============================================================
    # SIGNUP VERIFY
    # ============================================================

    @staticmethod
    def signup_verify(
        db: Session,
        mobile: str,
        otp: str,
    ):

        rate_limit_otp_verify(
            mobile
        )

        # --------------------------------------------------------
        # Development master OTP
        # --------------------------------------------------------

        if (
            settings.ALLOW_DEV_OTP
            and otp == settings.DEV_MASTER_OTP
        ):

            print(
                f"[DEV MODE] Master OTP used "
                f"for {mobile}"
            )

            signup = (
                db.query(SignupSession)
                .filter(
                    SignupSession.phone == mobile,
                    SignupSession.expires_at
                    >= datetime.now(timezone.utc),
                )
                .first()
            )

        # --------------------------------------------------------
        # Normal OTP
        # --------------------------------------------------------

        else:

            signup = (
                db.query(SignupSession)
                .filter(
                    SignupSession.phone == mobile,
                    SignupSession.otp == otp,
                    SignupSession.expires_at
                    >= datetime.now(timezone.utc),
                )
                .first()
            )

        if not signup:

            raise HTTPException(
                status_code=400,
                detail="Invalid or expired OTP",
            )

        # --------------------------------------------------------
        # Prevent duplicate account
        # --------------------------------------------------------

        existing_user = (
            AuthRepository.get_user_by_mobile(
                db,
                mobile,
            )
        )

        if existing_user:

            raise HTTPException(
                status_code=400,
                detail=(
                    "Account already exists. "
                    "Please login."
                ),
            )

        # --------------------------------------------------------
        # Create user
        # --------------------------------------------------------

        user = AuthRepository.create_user(
            db=db,
            mobile=mobile,
            first_name=signup.first_name,
            last_name=signup.last_name,
        )

        AuthRepository.mark_verified(
            db,
            user,
        )

        signup.verified = True

        reset_otp_verify_limit(
            mobile
        )

        db.commit()

        # --------------------------------------------------------
        # Create authentication session
        # --------------------------------------------------------

        return AuthService.create_auth_session(
            db=db,
            user_id=user.user_id,
        )

    # ============================================================
    # CREATE AUTH SESSION
    # ============================================================

    @staticmethod
    def create_auth_session(
        db: Session,
        user_id: int,
    ):

        now = datetime.now(
            timezone.utc
        )

        # --------------------------------------------------------
        # ACCESS TOKEN
        # --------------------------------------------------------

        access_token = AuthService._generate_access_token(
            user_id=user_id,
            now=now,
        )

        # --------------------------------------------------------
        # REFRESH TOKEN
        # --------------------------------------------------------

        refresh_token = generate_refresh_token()

        refresh_token_hash = hash_refresh_token(
            refresh_token
        )

        refresh_expires_at = (
            now
            + timedelta(
                days=REFRESH_TOKEN_EXPIRE_DAYS
            )
        )

        AuthRepository.create_refresh_session(
            db=db,
            user_id=user_id,
            token_hash=refresh_token_hash,
            expires_at=refresh_expires_at,
        )

        db.commit()

        return {
            "access_token": access_token,
            "refresh_token": refresh_token,
        }

    # ============================================================
    # GENERATE ACCESS TOKEN
    # ============================================================

    @staticmethod
    def _generate_access_token(
        user_id: int,
        now: datetime | None = None,
    ):

        if now is None:
            now = datetime.now(
                timezone.utc
            )

        payload = {
            "sub": str(user_id),
            "type": "user",
            "iat": now,
            "exp": (
                now
                + timedelta(
                    minutes=ACCESS_TOKEN_EXPIRE_MINUTES
                )
            ),
        }

        return jwt.encode(
            payload,
            settings.JWT_SECRET,
            algorithm=settings.JWT_ALGORITHM,
        )

    # ============================================================
    # REFRESH ACCESS TOKEN
    # ============================================================

    @staticmethod
    def refresh_access_token(
        db: Session,
        refresh_token: str,
    ):

        if not refresh_token:

            raise HTTPException(
                status_code=401,
                detail="Refresh session required",
            )

        token_hash = hash_refresh_token(
            refresh_token
        )

        session = (
            AuthRepository.get_refresh_session(
                db,
                token_hash,
            )
        )

        if not session:

            raise HTTPException(
                status_code=401,
                detail="Invalid refresh session",
            )

        now = datetime.now(
            timezone.utc
        )

        # --------------------------------------------------------
        # Revoked session
        # --------------------------------------------------------

        if session.revoked_at is not None:

            raise HTTPException(
                status_code=401,
                detail="Refresh session revoked",
            )

        # --------------------------------------------------------
        # Expired session
        # --------------------------------------------------------

        if session.expires_at <= now:

            session.revoked_at = now

            db.commit()

            raise HTTPException(
                status_code=401,
                detail="Refresh session expired",
            )

        # --------------------------------------------------------
        # User must still exist
        # --------------------------------------------------------

        user = AuthRepository.get_user_by_mobile

        from app.modules.users.models import User

        user = db.get(
            User,
            session.user_id,
        )

        if not user:

            session.revoked_at = now

            db.commit()

            raise HTTPException(
                status_code=401,
                detail="User not found",
            )

        # --------------------------------------------------------
        # ROTATE REFRESH TOKEN
        # --------------------------------------------------------

        session.revoked_at = now

        new_refresh_token = (
            generate_refresh_token()
        )

        new_refresh_token_hash = (
            hash_refresh_token(
                new_refresh_token
            )
        )

        new_refresh_expires_at = (
            now
            + timedelta(
                days=REFRESH_TOKEN_EXPIRE_DAYS
            )
        )

        AuthRepository.create_refresh_session(
            db=db,
            user_id=user.user_id,
            token_hash=new_refresh_token_hash,
            expires_at=new_refresh_expires_at,
        )

        # --------------------------------------------------------
        # New access token
        # --------------------------------------------------------

        new_access_token = (
            AuthService._generate_access_token(
                user_id=user.user_id,
                now=now,
            )
        )

        db.commit()

        return {
            "access_token": new_access_token,
            "refresh_token": new_refresh_token,
        }

    # ============================================================
    # LOGOUT
    # ============================================================

    @staticmethod
    def logout(
        db: Session,
        refresh_token: str | None,
    ):

        if not refresh_token:
            return

        token_hash = hash_refresh_token(
            refresh_token
        )

        session = (
            AuthRepository.get_refresh_session(
                db,
                token_hash,
            )
        )

        if not session:
            return

        if session.revoked_at is None:

            session.revoked_at = (
                datetime.now(timezone.utc)
            )

            db.commit()