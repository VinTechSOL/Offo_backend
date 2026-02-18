from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session
from app.core.database import get_db
from app.modules.locations.models import City, Campus, Building

router = APIRouter(prefix="/locations", tags=["Locations"])


@router.get("/cities")
def list_cities(db: Session = Depends(get_db)):
    return db.query(City).all()


@router.get("/campuses")
def list_campuses(city_id: int, db: Session = Depends(get_db)):
    return db.query(Campus).filter(Campus.city_id == city_id).all()


@router.get("/buildings")
def list_buildings(campus_id: int, db: Session = Depends(get_db)):
    return db.query(Building).filter(Building.campus_id == campus_id).all()
