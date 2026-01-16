from sqlalchemy.orm import Session
from sqlalchemy import select
from app.modules.staff.models import Staff


class StaffRepository:

    def get_by_username(db: Session, username: str):
        stmt = (
            select(Staff)
            .where(Staff.username == username)
            .where(Staff.is_active == True)
        )
        return db.execute(stmt).scalar_one_or_none()

    @staticmethod
    def create(db: Session, staff: Staff):
        db.add(staff)
        db.commit()
        db.refresh(staff)
        return staff
