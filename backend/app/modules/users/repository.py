from sqlalchemy.orm import Session
from sqlalchemy import select
from app.modules.users.models import User, UserAddress
from app.modules.orders.constants import OrderStatus

class UserRepository:

    @staticmethod
    def get_by_id(db: Session, user_id: int):
        return db.execute(
            select(User).where(User.user_id == user_id)
        ).scalar_one_or_none()

    @staticmethod
    def update_profile(db: Session, user: User, data):
        user.first_name = data.first_name
        user.last_name = data.last_name
        db.commit()
        return user

    @staticmethod
    def add_address(db: Session, user_id: int, data):
        address = UserAddress(user_id=user_id, **data.dict())
        db.add(address)
        db.commit()
        db.refresh(address)
        return address
    
    
