from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.core.database import get_db

from app.modules.locations.models import (
    City,
    Campus,
    Building,
)

from app.modules.locations.schemas import (
    CreateCityRequest,
    CreateCampusRequest,
    CreateBuildingRequest,
)

from app.modules.locations.service import (
    LocationService,
)

router = APIRouter(
    prefix="/locations",
    tags=["Locations"],
)


# =========================================================
# Existing Dropdown APIs
# =========================================================

@router.get("/cities")
def list_cities(
    db: Session = Depends(get_db),
):
    return (
        db.query(City)
        .order_by(City.city_name)
        .all()
    )


@router.get("/campuses")
def list_campuses(
    city_id: int,
    db: Session = Depends(get_db),
):
    return (
        db.query(Campus)
        .filter(Campus.city_id == city_id)
        .order_by(Campus.campus_name)
        .all()
    )


@router.get("/buildings")
def list_buildings(
    campus_id: int,
    db: Session = Depends(get_db),
):
    return (
        db.query(Building)
        .filter(Building.campus_id == campus_id)
        .order_by(Building.building_name)
        .all()
    )


# =========================================================
# Create City
# =========================================================

@router.post("/cities")
def create_city(
    payload: CreateCityRequest,
    db: Session = Depends(get_db),
):
    return LocationService.create_city(
        db,
        payload.city_name,
    )


# =========================================================
# Create Campus
# =========================================================

@router.post("/campuses")
def create_campus(
    payload: CreateCampusRequest,
    db: Session = Depends(get_db),
):
    return LocationService.create_campus(
        db,
        payload.city_id,
        payload.campus_name,
    )


# =========================================================
# Create Building
# =========================================================

@router.post("/buildings")
def create_building(
    payload: CreateBuildingRequest,
    db: Session = Depends(get_db),
):
    return LocationService.create_building(
        db,
        payload.campus_id,
        payload.building_name,
        payload.latitude,
        payload.longitude,
    )


# =========================================================
# Tree
# =========================================================

@router.get("/tree")
def get_location_tree(
    db: Session = Depends(get_db),
):
    return LocationService.get_location_tree(db)