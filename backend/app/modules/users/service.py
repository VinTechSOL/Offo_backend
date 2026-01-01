from sqlalchemy.orm import Session
from app.modules.users.repository import UserRepository

class UserService:

    @staticmethod
    def get_profile(db: Session, user_id: int):
        return UserRepository.get_by_id(db, user_id)

    @staticmethod
    def update_profile(db: Session, user, data):
        return UserRepository.update_profile(db, user, data)

    @staticmethod
    def add_address(db: Session, user_id: int, data):
        return UserRepository.add_address(db, user_id, data)
