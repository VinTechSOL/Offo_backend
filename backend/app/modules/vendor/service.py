from sqlalchemy.orm import Session
from app.modules.vendor.repository import VendorRepository

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
