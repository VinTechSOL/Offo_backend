from sqlalchemy.orm import Session
from fastapi import HTTPException

from app.modules.locations.models import (
    City,
    Campus,
    Building,
    UserContext,
)

from app.modules.locations.repository import LocationRepository


# =========================================================
# USER CONTEXT
# =========================================================

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

        campus = db.get(Campus, campus_id)

        if not campus or campus.city_id != city_id:
            raise HTTPException(400, "Invalid campus")

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

        return context

    @staticmethod
    def get_context(
        db: Session,
        user_id: int,
    ):

        context = LocationRepository.get_by_user(
            db,
            user_id,
        )

        if not context:
            raise HTTPException(
                status_code=404,
                detail="User location context not set",
            )

        return context

    @staticmethod
    def get_context_details(
        db: Session,
        user_id: int,
    ):

        context = LocationRepository.get_by_user(
            db,
            user_id,
        )

        if not context:
            return None

        city = db.get(City, context.city_id)
        campus = db.get(Campus, context.campus_id)

        building = None

        if context.building_id:
            building = db.get(Building, context.building_id)

        return {
            "city_id": city.city_id,
            "city_name": city.city_name,
            "campus_id": campus.campus_id,
            "campus_name": campus.campus_name,
            "building_id": building.building_id if building else None,
            "building_name": building.building_name if building else None,
        }


# =========================================================
# LOCATION MASTER SERVICE
# =========================================================

class LocationService:

    @staticmethod
    def create_city(
        db: Session,
        city_name: str,
    ):

        existing = (
            db.query(City)
            .filter(City.city_name == city_name.strip())
            .first()
        )

        if existing:
            raise HTTPException(
                400,
                "City already exists",
            )

        city = City(
            city_name=city_name.strip()
        )

        return LocationRepository.create_city(
            db,
            city,
        )

    @staticmethod
    def create_campus(
        db: Session,
        city_id: int,
        campus_name: str,
    ):

        city = db.get(City, city_id)

        if not city:
            raise HTTPException(
                404,
                "City not found",
            )

        existing = (
            db.query(Campus)
            .filter(
                Campus.city_id == city_id,
                Campus.campus_name == campus_name.strip(),
            )
            .first()
        )

        if existing:
            raise HTTPException(
                400,
                "Campus already exists",
            )

        campus = Campus(
            city_id=city_id,
            campus_name=campus_name.strip(),
        )

        return LocationRepository.create_campus(
            db,
            campus,
        )

    @staticmethod
    def create_building(
        db: Session,
        campus_id: int,
        building_name: str,
        latitude: float | None,
        longitude: float | None,
    ):

        campus = db.get(Campus, campus_id)

        if not campus:
            raise HTTPException(
                404,
                "Campus not found",
            )

        existing = (
            db.query(Building)
            .filter(
                Building.campus_id == campus_id,
                Building.building_name == building_name.strip(),
            )
            .first()
        )

        if existing:
            raise HTTPException(
                400,
                "Building already exists",
            )

        building = Building(
            campus_id=campus_id,
            building_name=building_name.strip(),
            latitude=latitude,
            longitude=longitude,
        )

        return LocationRepository.create_building(
            db,
            building,
        )

    @staticmethod
    def get_location_tree(
        db: Session,
    ):

        cities = LocationRepository.get_location_tree(db)

        response = []

        for city in cities:

            campuses = []

            for campus in city.campuses:

                campuses.append(
                    {
                        "campus_id": campus.campus_id,
                        "campus_name": campus.campus_name,
                        "buildings": [
                            {
                                "building_id": b.building_id,
                                "building_name": b.building_name,
                            }
                            for b in campus.buildings
                        ],
                    }
                )

            response.append(
                {
                    "city_id": city.city_id,
                    "city_name": city.city_name,
                    "campuses": campuses,
                }
            )

        return response