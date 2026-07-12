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
    def list_branches(
        db: Session,
        cafe_id: int,
    ):

        rows = VendorRepository.list_branches(
            db,
            cafe_id,
        )

        branches = []

        for row in rows:

            branch = row[0]

            branches.append({

                "branch_id": branch.branch_id,

                "cafe_id": branch.cafe_id,

                "branch_name": branch.branch_name,

                "city_id": branch.city_id,

                "city_name": row.city_name,

                "campus_id": branch.campus_id,

                "campus_name": row.campus_name,

                "building_id": branch.building_id,

                "building_name": row.building_name,

                "opens_at": branch.opens_at,

                "closes_at": branch.closes_at,

                "image_url": branch.image_url,

                "is_active": branch.is_active,

                "has_vendor": row.vendor_staff_id is not None,

            })

        return branches
    
    @staticmethod
    def update_branch(
        db: Session,
        branch_id: int,
        data,
    ):
        branch = VendorRepository.update_branch(
           db=db,
           branch_id=branch_id,
           data=data,
        )

        if not branch:
            raise HTTPException(
                status_code=404,
                detail="Branch not found"
            )

        return branch
    
    



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
