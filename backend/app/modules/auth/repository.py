from datetime import datetime, timezone

from sqlalchemy.orm import Session
from sqlalchemy import select

from app.modules.users.models import User
from app.modules.auth.models import SignupSession, RefreshSession


class AuthRepository:

    # ============================================================
    # USER
    # ============================================================

    @staticmethod
    def get_user_by_mobile(
        db: Session,
        mobile: str,
    ):
        return db.execute(
            select(User).where(
                User.mobile_number == mobile
            )
        ).scalar_one_or_none()

    @staticmethod
    def create_user(
        db: Session,
        mobile: str,
        first_name: str | None = None,
        last_name: str | None = None,
    ):
        user = User(
            mobile_number=mobile,
            first_name=first_name,
            last_name=last_name,
            is_otp_verified=True,
        )

        db.add(user)
        db.commit()
        db.refresh(user)

        return user

    @staticmethod
    def mark_verified(
        db: Session,
        user: User,
    ):
        user.is_otp_verified = True

        db.commit()

        return user

    # ============================================================
    # SIGNUP SESSION
    # ============================================================

    @staticmethod
    def create_signup_session(
        db: Session,
        phone: str,
        first_name: str,
        last_name: str,
        otp: str,
    ):
        from datetime import timedelta

        session = SignupSession(
            phone=phone,
            first_name=first_name,
            last_name=last_name,
            otp=otp,
            expires_at=(
                datetime.now(timezone.utc)
                + timedelta(minutes=5)
            ),
        )

        db.add(session)
        db.flush()

        return session

    @staticmethod
    def get_valid_signup_session(
        db: Session,
        phone: str,
        otp: str,
    ):
        return (
            db.query(SignupSession)
            .filter(
                SignupSession.phone == phone,
                SignupSession.otp == otp,
                SignupSession.expires_at
                > datetime.now(timezone.utc),
                SignupSession.verified == False,
            )
            .first()
        )

    # ============================================================
    # REFRESH SESSIONS
    # ============================================================

    @staticmethod
    def create_refresh_session(
        db: Session,
        user_id: int,
        token_hash: str,
        expires_at: datetime,
    ):
        session = RefreshSession(
            user_id=user_id,
            token_hash=token_hash,
            expires_at=expires_at,
        )

        db.add(session)
        db.flush()

        return session

    @staticmethod
    def get_refresh_session(
        db: Session,
        token_hash: str,
    ):
        return db.execute(
            select(RefreshSession).where(
                RefreshSession.token_hash == token_hash
            )
        ).scalar_one_or_none()

    @staticmethod
    def revoke_refresh_session(
        db: Session,
        session: RefreshSession,
    ):
        session.revoked_at = datetime.now(timezone.utc)

        db.commit()

        return session

    @staticmethod
    def update_refresh_session_usage(
        db: Session,
        session: RefreshSession,
    ):
        session.last_used_at = datetime.now(timezone.utc)

        db.commit()

        return session