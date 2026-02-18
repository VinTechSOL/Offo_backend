from sqlalchemy.orm import Session
from fastapi import HTTPException
from app.modules.vendor.repository import VendorRepository ,CafeRepository
from app.modules.locations.repository import LocationRepository
from datetime import datetime,time
from app.core.time_utils import now_utc

class VendorService:

    @staticmethod
    def create_cafeteria(db: Session, data):
        return VendorRepository.create_cafeteria(db, data)

    @staticmethod
    def list_cafeterias(db: Session):
        return VendorRepository.list_cafeterias(db)

    @staticmethod
    def create_branch(db: Session, data):
        return VendorRepository.create_branch(db, data)

    @staticmethod
    def list_branches(db: Session, cafe_id: int):
        return VendorRepository.list_branches(db, cafe_id)
    
    



class CafeService:

    @staticmethod
    def get_for_user(db: Session, user_id: int):
        context = LocationRepository.get_by_user(db, user_id)

        if not context or not context.city_id or not context.campus_id:
            raise HTTPException(400, "User location context not set")

        return CafeRepository.get_for_user_context(
            db,
            city_id=context.city_id,
            campus_id=context.campus_id,
            building_id=context.building_id,
        )
    
    @staticmethod
    def is_branch_open(branch):
      if not branch.opens_at or not branch.closes_at:
        return True  # legacy fallback
      now = now_utc().time()
      return branch.opens_at <= now <= branch.closes_at
