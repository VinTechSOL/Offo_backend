from sqlalchemy.orm import Session
from sqlalchemy import select
from app.modules.users.models import User

class AuthRepository:

    @staticmethod
    def get_user_by_mobile(db: Session, mobile: str):
        stmt = select(User).where(User.mobile_number == mobile)
        return db.execute(stmt).scalar_one_or_none()

    @staticmethod
    def create_user(db: Session, mobile: str):
        user = User(mobile_number=mobile, is_otp_verified=True)
        db.add(user)
        db.commit()
        db.refresh(user)
        return user

    @staticmethod
    def mark_verified(db: Session, user: User):
        user.is_otp_verified = True
        db.commit()
        return user
