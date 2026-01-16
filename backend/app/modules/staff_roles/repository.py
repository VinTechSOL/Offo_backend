from sqlalchemy.orm import Session
from sqlalchemy import select
from .models import StaffRole

class StaffRoleRepository:

    @staticmethod
    def create(db: Session, role: StaffRole):
        db.add(role)
        db.commit()
        db.refresh(role)
        return role

    @staticmethod
    def get_by_name(db: Session, role_name: str, cafe_id=None):
        stmt = select(StaffRole).where(
            StaffRole.role_name == role_name,
            StaffRole.cafe_id == cafe_id
        )
        return db.execute(stmt).scalar_one_or_none()
