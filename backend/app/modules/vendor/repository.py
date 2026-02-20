from sqlalchemy.orm import Session
from sqlalchemy import select
from app.modules.vendor.models import Cafeteria, CafeBranch
from app.modules.locations.models import City,Campus,Building

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


class CafeRepository:

    @staticmethod
    def get_for_user_context(
        db: Session,
        *,
        city_id: int,
        campus_id: int,
        building_id: int | None,
    ):
        query = (
            db.query(
                CafeBranch.branch_id,
                CafeBranch.branch_name,
                CafeBranch.image_url,
                Building.building_name,
                Campus.campus_name,
                City.city_name,
                CafeBranch.opens_at,
                CafeBranch.closes_at,
                CafeBranch.is_active.label("is_open"),
            )
            .join(City, City.city_id == CafeBranch.city_id)
            .join(Campus, Campus.campus_id == CafeBranch.campus_id)
            .outerjoin(Building, Building.building_id == CafeBranch.building_id)
            .filter(
                CafeBranch.city_id == city_id,
                CafeBranch.campus_id == campus_id,
                CafeBranch.is_active == True,
            )
        )

        if building_id:
            query = query.order_by(
                (CafeBranch.building_id == building_id).desc()
            )

        return query.all()
