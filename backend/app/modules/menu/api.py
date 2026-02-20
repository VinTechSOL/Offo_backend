from fastapi import APIRouter, Depends,HTTPException,File,UploadFile,Form
import uuid
import os
from sqlalchemy.orm import Session
from app.core.database import get_db
from app.modules.menu.schemas import (
    CategoryCreateRequest,
    CategoryCreate,
    MenuItemCreate,
    BranchMenuItemCreate,
    BranchMenuItemUpdate,
    MenuItemUpdate
)
from app.modules.menu.service import MenuService
from app.modules.menu.models import MenuItem
from app.core.security import get_current_staff
from app.core.s3_service import upload_image



router = APIRouter(prefix="/menu", tags=["Menu"])

@router.post("/categories")
def create_category(data: CategoryCreateRequest, db: Session = Depends(get_db),staff = Depends(get_current_staff)):
    if not staff.branch_id:
        raise HTTPException(403,"staff not assigned")
    
    category = CategoryCreate(
        cafe_id=staff.branch_id,
        branch_id=staff.branch_id,
        category_name=data.category_name,
        category_description=data.category_description,
        parent_id=data.parent_id,
    )

    return MenuService.create_category(db, category)

@router.get("/categories")
def list_categories(
    db: Session = Depends(get_db),
    staff = Depends(get_current_staff),
):
    if not staff.branch_id:
        raise HTTPException(403, "Staff not assigned to branch")

    return MenuService.list_categories(db, staff.branch_id)


@router.post("/items")
def create_menu_item(
    item_name: str = Form(...),
    item_description: str = Form(None),
    item_type_id: int = Form(...),
    image: UploadFile = File(None),
    db: Session = Depends(get_db),
):
    image_url = None

    if image:
        ext = image.filename.split(".")[-1]
        filename = f"{uuid.uuid4()}.{ext}"

        image_url = upload_image(
            file_obj=image.file,
            filename=filename,
            content_type=image.content_type,
            folder="menu"  
        )

    item = MenuItem(
        item_name=item_name,
        item_description=item_description,
        item_type_id=item_type_id,
        image_url=image_url,
    )

    db.add(item)
    db.commit()
    db.refresh(item)

    return item


@router.patch("/items/{item_id}")
def update_menu_item(
    item_id: int,
    item_name: str = Form(None),
    item_description: str = Form(None),
    item_type_id: int = Form(None),
    image: UploadFile = File(None),
    db: Session = Depends(get_db),
):
    item = db.get(MenuItem, item_id)

    if not item:
        raise HTTPException(status_code=404, detail="Item not found")

    if item_name is not None:
        item.item_name = item_name

    if item_description is not None:
        item.item_description = item_description

    if item_type_id is not None:
        item.item_type_id = item_type_id

    if image:
        ext = image.filename.split(".")[-1]
        filename = f"{uuid.uuid4()}.{ext}"

        item.image_url = upload_image(
            file_obj=image.file,
            filename=filename,
            content_type=image.content_type,
            folder="menu"  
        )

    db.commit()
    db.refresh(item)

    return item



@router.post("/branch-items")
def attach_item_to_branch(
    data: BranchMenuItemCreate,
    db: Session = Depends(get_db),
    staff = Depends(get_current_staff),
):
    if not staff.branch_id:
        raise HTTPException(403, "Staff not assigned to branch")

    return MenuService.attach_item_to_branch(
        db,
        data,
        branch_id=staff.branch_id
    )

@router.patch("/branch-items/{branch_menu_item_id}")
def update_branch_item(
    branch_menu_item_id: int,
    data: BranchMenuItemUpdate,
    db: Session = Depends(get_db)
):
    return MenuService.update_branch_item(db, branch_menu_item_id, data)

@router.get("/branchMenu/")
def list_branch_menu( db: Session = Depends(get_db),staff = Depends(get_current_staff)):
    if not staff.branch_id:
        raise HTTPException(403, "staff not assigned to branch")
    return MenuService.list_branch_menu(db, staff.branch_id)

@router.get("/branch/{branch_id}/public")
def list_branch_menu_for_users(
    branch_id: int,
    db: Session = Depends(get_db)
):
    return MenuService.list_branch_menu_for_users(db, branch_id)

