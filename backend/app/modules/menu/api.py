from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session
from app.core.database import get_db
from app.modules.menu.schemas import (
    CategoryCreate,
    MenuItemCreate,
    BranchMenuItemCreate,
    BranchMenuItemUpdate
)
from app.modules.menu.service import MenuService

router = APIRouter(prefix="/menu", tags=["Menu"])

@router.post("/categories")
def create_category(data: CategoryCreate, db: Session = Depends(get_db)):
    return MenuService.create_category(db, data)

@router.post("/items")
def create_menu_item(data: MenuItemCreate, db: Session = Depends(get_db)):
    return MenuService.create_menu_item(db, data)

@router.post("/branch-items")
def attach_item_to_branch(data: BranchMenuItemCreate, db: Session = Depends(get_db)):
    return MenuService.attach_item_to_branch(db, data)

@router.patch("/branch-items/{branch_menu_item_id}")
def update_branch_item(
    branch_menu_item_id: int,
    data: BranchMenuItemUpdate,
    db: Session = Depends(get_db)
):
    return MenuService.update_branch_item(db, branch_menu_item_id, data)

@router.get("/branch/{branch_id}")
def list_branch_menu(branch_id: int, db: Session = Depends(get_db)):
    return MenuService.list_branch_menu(db, branch_id)
