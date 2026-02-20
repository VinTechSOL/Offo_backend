from sqlalchemy.orm import Session
from app.modules.menu.repository import MenuRepository
from fastapi import HTTPException

class MenuService:

    @staticmethod
    def create_category(db: Session, data):
        exists = MenuRepository.category_exists(
            db,
            branch_id=data.branch_id,
            category_name=data.category_name,
        )

        if exists:
          raise HTTPException(
            status_code=409,
            detail="Category already exists for this branch",
           )

        return MenuRepository.create_category(db, data)

    @staticmethod
    def create_menu_item(db: Session, data):
        return MenuRepository.create_menu_item(db, data)
    
    @staticmethod
    def update_menu_item(db: Session, item_id: int, data):
        return MenuRepository.update_menu_item(db, item_id, data)


    @staticmethod
    def attach_item_to_branch(db: Session, data,branch_id: int):
        if data.price is not None and data.price <= 0:
            raise HTTPException(status_code=400, detail="price must be greater than zero")
        
        return MenuRepository.attach_item_to_branch(db, data,branch_id)

    @staticmethod
    def update_branch_item(db: Session, branch_menu_item_id: int, data):
        if data.price is not None and data.price <= 0:
            raise HTTPException(status_code=400, detail="price must be greater than zero")
        
        return MenuRepository.update_branch_item(db, branch_menu_item_id, data)

    @staticmethod
    def list_branch_menu(db: Session, branch_id: int):
        return MenuRepository.list_branch_menu(db, branch_id)
    
    @staticmethod
    def list_categories(db: Session, branch_id: int):
        categories = MenuRepository.list_categories_by_branch(db, branch_id)
        return [
            {
                "category_id": c.category_id,
                "category_name": c.category_name
            }
            for c in categories
        ]

    
    @staticmethod
    def list_branch_menu_for_users(db: Session, branch_id: int):
        rows = MenuRepository.get_branch_menu_for_users(db, branch_id)

        categories = {}

        for r in rows:
            if r.category_id not in categories:
                categories[r.category_id] = {
                    "category_id": r.category_id,
                    "category_name": r.category_name,
                    "items": []
                }

            categories[r.category_id]["items"].append({
                "branch_menu_item_id": r.branch_menu_item_id,
                "item_id": r.item_id,
                "name": r.item_name,
                "price": float(r.price),
                "imageUrl": r.image_url,
                "is_veg": r.item_type.lower() == "veg",
                "is_available": r.is_available,
                "category_name": r.category_name,
            })

        return {
            "branch_id": branch_id,
            "categories": list(categories.values())
        }
    


