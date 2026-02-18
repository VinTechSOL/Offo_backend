from sqlalchemy.orm import Session
from sqlalchemy import distinct
from app.modules.vendor.models import CafeBranch
from app.modules.locations.models import UserContext


class LocationRepository:

    # dropdowns (derived from vendors)
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

    # user context
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

