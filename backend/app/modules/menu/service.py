from sqlalchemy.orm import Session
from app.modules.menu.repository import MenuRepository

class MenuService:

    @staticmethod
    def create_category(db: Session, data):
        return MenuRepository.create_category(db, data)

    @staticmethod
    def create_menu_item(db: Session, data):
        return MenuRepository.create_menu_item(db, data)

    @staticmethod
    def attach_item_to_branch(db: Session, data):
        return MenuRepository.attach_item_to_branch(db, data)

    @staticmethod
    def update_branch_item(db: Session, branch_menu_item_id: int, data):
        return MenuRepository.update_branch_item(db, branch_menu_item_id, data)

    @staticmethod
    def list_branch_menu(db: Session, branch_id: int):
        return MenuRepository.list_branch_menu(db, branch_id)
