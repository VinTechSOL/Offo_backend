from sqlalchemy.orm import Session
from .models import StaffRole
from .repository import StaffRoleRepository

class StaffRoleService:

    @staticmethod
    def create_role(db: Session, role_name: str, cafe_id=None, description=None):
        role = StaffRole(
            role_name=role_name,
            cafe_id=cafe_id,
            description=description
        )
        return StaffRoleRepository.create(db, role)
