from sqlalchemy.orm import Session
from sqlalchemy import select
from app.modules.vendor.models import Cafeteria, CafeBranch

class VendorRepository:

    @staticmethod
    def create_cafeteria(db: Session, data):
        cafe = Cafeteria(**data.dict())
        db.add(cafe)
        db.commit()
        db.refresh(cafe)
        return cafe

    @staticmethod
    def list_cafeterias(db: Session):
        return db.execute(select(Cafeteria)).scalars().all()

    @staticmethod
    def create_branch(db: Session, data):
        branch = CafeBranch(**data.dict())
        db.add(branch)
        db.commit()
        db.refresh(branch)
        return branch

    @staticmethod
    def list_branches(db: Session, cafe_id: int):
        return db.execute(
            select(CafeBranch).where(CafeBranch.cafe_id == cafe_id)
        ).scalars().all()
