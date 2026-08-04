from sqlalchemy.orm import Session, aliased
from sqlalchemy import select
from app.modules.staff.models import Staff
from app.modules.staff_roles.models import StaffRole
from app.modules.vendor.models import Cafeteria, CafeBranch
from app.modules.locations.models import City,Campus,Building
from app.modules.vendor.models import BranchDocument
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
        branch = CafeBranch(**data.model_dump())
        db.add(branch)
        db.commit()
        db.refresh(branch)
        return branch

    @staticmethod
    def create_branch_document(
        db: Session,
        branch_id: int,
        document_name: str,
        document_url: str,
    ):
        document = BranchDocument(
            branch_id=branch_id,
            document_name=document_name,
            document_url=document_url,
        )

        db.add(document)
        db.commit()
        db.refresh(document)

        return document

    @staticmethod
    def list_branches(db: Session, cafe_id: int):

        VendorRole = aliased(StaffRole)

        return (
            db.query(
                CafeBranch,
                City.city_name,
                Campus.campus_name,
                Building.building_name,
                Staff.staff_id.label("vendor_staff_id"),
            )
            .join(
                City,
                City.city_id == CafeBranch.city_id,
            )
            .join(
                Campus,
                Campus.campus_id == CafeBranch.campus_id,
            )
            .outerjoin(
                Building,
                Building.building_id == CafeBranch.building_id,
            )
            .outerjoin(
                Staff,
                (Staff.branch_id == CafeBranch.branch_id)
                & (Staff.role.has(role_name="VENDOR"))
            )
            
            .filter(
                CafeBranch.cafe_id == cafe_id
            )
            .distinct(CafeBranch.branch_id)
            .all()
        )
    
    @staticmethod
    def update_branch(
        db: Session,
        branch_id: int,
        data,
    ):
        branch = (
            db.query(CafeBranch)
            .filter(CafeBranch.branch_id == branch_id)
            .first()
        )

        if not branch:
            return None

        update_data = data.model_dump()

        for field, value in update_data.items():
           if hasattr(branch, field): 
              setattr(branch, field, value)

        db.commit()
        db.refresh(branch)

        return branch


    @staticmethod
    def get_branch_by_id(
        db: Session,
        branch_id: int,
    ):
        return (
            db.query(CafeBranch)
            .filter(CafeBranch.branch_id == branch_id)
            .first()
        )

    @staticmethod
    def get_branch_by_owner_phone(
        db: Session,
        phone: str,
    ) -> CafeBranch | None:

        return (
            db.query(CafeBranch)
            .filter(
               CafeBranch.owner_phone_number == phone,
               CafeBranch.is_active == True,
            )
            .first()
        )


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
