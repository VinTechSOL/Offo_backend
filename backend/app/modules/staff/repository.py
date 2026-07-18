from sqlalchemy.orm import Session
from sqlalchemy import select
from app.modules.staff.models import Staff

class StaffRepository:

    @staticmethod
    def create(db: Session, staff: Staff) -> Staff:
        db.add(staff)
        db.commit()
        db.refresh(staff)
        return staff

    @staticmethod
    def get_by_id(db: Session, staff_id: int) -> Staff | None:
        return db.query(Staff).filter(Staff.staff_id == staff_id).first()

    @staticmethod
    def get_by_branch_and_role(
        db: Session,
        branch_id: int,
        role_name: str
    ) -> Staff | None:
        return (
            db.query(Staff)
            .join(Staff.role)
            .filter(
                Staff.branch_id == branch_id,
                Staff.role.has(role_name=role_name)
            )
            .first()
        )

    @staticmethod
    def update(db: Session, staff: Staff) -> Staff:
        db.commit()
        db.refresh(staff)
        return staff

    @staticmethod
    def get_by_username(db: Session, username: str):
        stmt = (
            select(Staff)
            .where(Staff.username == username)
            .where(Staff.is_active == True)
        )
        return db.execute(stmt).scalar_one_or_none()
    

    @staticmethod
    def get_by_username_any_status(
       db: Session,
       username: str,
    ):
        return (
           db.query(Staff)
           .filter(Staff.username == username)
           .first()
        )