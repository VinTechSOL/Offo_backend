from sqlalchemy.orm import Session
from sqlalchemy import distinct

from app.modules.vendor.models import CafeBranch
from app.modules.locations.models import (
    UserContext,
    City,
    Campus,
    Building,
)


class LocationRepository:

    # =====================================================
    # Existing dropdown methods
    # =====================================================

    @staticmethod
    def get_city_ids(db: Session):
        return (
            db.query(distinct(CafeBranch.city_id))
            .filter(CafeBranch.is_active == True)
            .all()
        )

    @staticmethod
    def get_campus_ids(db: Session, city_id: int):
        return (
            db.query(distinct(CafeBranch.campus_id))
            .filter(
                CafeBranch.city_id == city_id,
                CafeBranch.is_active == True,
            )
            .all()
        )

    @staticmethod
    def get_building_ids(db: Session, campus_id: int):
        return (
            db.query(distinct(CafeBranch.building_id))
            .filter(
                CafeBranch.campus_id == campus_id,
                CafeBranch.is_active == True,
                CafeBranch.building_id.isnot(None),
            )
            .all()
        )

    # =====================================================
    # User Context
    # =====================================================

    @staticmethod
    def get_by_user(db: Session, user_id: int):
        return (
            db.query(UserContext)
            .filter(UserContext.user_id == user_id)
            .first()
        )

    @staticmethod
    def upsert(
        db: Session,
        *,
        user_id: int,
        city_id: int,
        campus_id: int,
        building_id: int | None,
    ):
        context = db.get(UserContext, user_id)

        if not context:
            context = UserContext(user_id=user_id)
            db.add(context)

        context.city_id = city_id
        context.campus_id = campus_id
        context.building_id = building_id

        return context

    # =====================================================
    # Create City
    # =====================================================

    @staticmethod
    def create_city(db: Session, city: City):
        db.add(city)
        db.commit()
        db.refresh(city)
        return city

    # =====================================================
    # Create Campus
    # =====================================================

    @staticmethod
    def create_campus(db: Session, campus: Campus):
        db.add(campus)
        db.commit()
        db.refresh(campus)
        return campus

    # =====================================================
    # Create Building
    # =====================================================

    @staticmethod
    def create_building(db: Session, building: Building):
        db.add(building)
        db.commit()
        db.refresh(building)
        return building
    
    # =====================================================
    # Update City
    # =====================================================

    @staticmethod
    def update_city(
        db: Session,
        city: City,
    ):
        db.add(city)
        db.commit()
        db.refresh(city)
        return city

    # =====================================================
    # Update Campus
    # =====================================================

    @staticmethod
    def update_campus(
        db: Session,
        campus: Campus,
    ):
        db.add(campus)
        db.commit()
        db.refresh(campus)
        return campus

    # =====================================================
    # Update Building
    # =====================================================

    @staticmethod
    def update_building(
        db: Session,
        building: Building,
    ):
        db.add(building)
        db.commit()
        db.refresh(building)
        return building

    # =====================================================
    # Tree Data
    # =====================================================

    @staticmethod
    def get_location_tree(db: Session):
        return (
            db.query(City)
            .order_by(City.city_name)
            .all()
        )