from sqlalchemy.orm import Session
from sqlalchemy import outerjoin
from fastapi import HTTPException
from app.modules.locations.models import Campus,Building
from app.modules.locations.repository import LocationRepository
from app.modules.locations.models import City, Campus, Building, UserContext

class UserContextService:

    @staticmethod
    def set_context(
        db: Session,
        *,
        user_id: int,
        city_id: int,
        campus_id: int,
        building_id: int | None,
    ):
        # validate campus-city
        campus = db.get(Campus, campus_id)
        if not campus or campus.city_id != city_id:
            raise HTTPException(400, "Invalid campus")

        # validate building-campus
        if building_id:
            building = db.get(Building, building_id)
            if not building or building.campus_id != campus_id:
                raise HTTPException(400, "Invalid building")

        context = LocationRepository.upsert(
            db,
            user_id=user_id,
            city_id=city_id,
            campus_id=campus_id,
            building_id=building_id,
        )

        db.commit()
        db.refresh(context)

        print(
            f"📍 USER CONTEXT SET | "
            f"user={user_id} city={city_id} campus={campus_id} building={building_id}"
        )

        return context

    @staticmethod
    def get_context(db: Session, user_id: int):
        context = LocationRepository.get_by_user(db, user_id)

        if not context:
            raise HTTPException(404, "User location context not set")

        return context
    

    @staticmethod
    def get_context_details(db: Session, user_id: int):
        result = (
            db.query(
                City.city_id,
                City.city_name,
                Campus.campus_id,
                Campus.campus_name,
                Building.building_id,
                Building.building_name,
            )
            .join(UserContext, UserContext.city_id == City.city_id)
            .join(Campus, Campus.campus_id == UserContext.campus_id)
            .outerjoin(
                Building,
                Building.building_id == UserContext.building_id,
            )
            .filter(UserContext.user_id == user_id)
            .first()
        )

        if not result:
            return None

        (city_id,city_name, campus_id,campus_name, building_id,building_name) = result

        return {
            "city_id": city_id,
            "city_name": city_name,
            "campus_id": campus_id,
            "campus_name": campus_name,
            "building_id": building_id, 
            "building_name":building_name # may be None
        }





