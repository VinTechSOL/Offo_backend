from sqlalchemy.orm import Session
from sqlalchemy import select
from app.modules.users.models import User
from datetime import datetime,timedelta,timezone
from app.modules.auth.models import SignupSession

class AuthRepository:

    @staticmethod
    def get_user_by_mobile(db: Session, mobile: str):
        stmt = select(User).where(User.mobile_number == mobile)
        return db.execute(stmt).scalar_one_or_none()

    @staticmethod
    def create_user(db: Session, mobile: str,first_name: str | None = None,last_name: str | None = None,):
        user = User(mobile_number=mobile,first_name = first_name,last_name = last_name, is_otp_verified=True)
        db.add(user)
        db.commit()
        db.refresh(user)
        return user

    @staticmethod
    def mark_verified(db: Session, user: User):
        user.is_otp_verified = True
        db.commit()
        return user
    
    @staticmethod
    def create_signup_session(
        db: Session, phone: str, first_name: str, last_name: str, otp: str
    ):
        session = SignupSession(
            phone=phone,
            first_name=first_name,
            last_name=last_name,
            otp=otp,
            expires_at=datetime.now(timezone.utc) + timedelta(minutes=5),
        )
        db.add(session)
        db.flush()
        return session
    
    @staticmethod
    def get_valid_signup_session(db: Session, phone: str, otp: str):
        return (
            db.query(SignupSession)
            .filter(
                SignupSession.phone == phone,
                SignupSession.otp == otp,
                SignupSession.expires_at > datetime.now(timezone.utc),
                SignupSession.verified == False,
            )
            .first()
        )
