from sqlalchemy.orm import Session
from sqlalchemy import select
from app.modules.menu.models import MenuCategory, MenuItem, BranchMenuItem

class MenuRepository:

    @staticmethod
    def create_category(db: Session, data):
        category = MenuCategory(**data.dict())
        db.add(category)
        db.commit()
        db.refresh(category)
        return category

    @staticmethod
    def create_menu_item(db: Session, data):
        item = MenuItem(**data.dict())
        db.add(item)
        db.commit()
        db.refresh(item)
        return item

    @staticmethod
    def attach_item_to_branch(db: Session, data):
        branch_item = BranchMenuItem(**data.dict())
        db.add(branch_item)
        db.commit()
        db.refresh(branch_item)
        return branch_item

    @staticmethod
    def update_branch_item(db: Session, branch_menu_item_id: int, data):
        item = db.get(BranchMenuItem, branch_menu_item_id)
        if data.price is not None:
            item.price = data.price
        if data.is_available is not None:
            item.is_available = data.is_available
        db.commit()
        return item

    @staticmethod
    def list_branch_menu(db: Session, branch_id: int):
        return db.execute(
            select(BranchMenuItem).where(BranchMenuItem.branch_id == branch_id)
        ).scalars().all()
