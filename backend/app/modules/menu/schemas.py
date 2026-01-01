from pydantic import BaseModel

class CategoryCreate(BaseModel):
    cafe_id: int
    branch_id: int
    category_name: str
    category_description: str | None = None
    parent_id: int | None = None


class MenuItemCreate(BaseModel):
    item_name: str
    item_description: str | None = None
    item_type_id: int
    image_url: str | None = None


class BranchMenuItemCreate(BaseModel):
    cafe_id: int
    branch_id: int
    item_id: int
    category_id: int
    price: float


class BranchMenuItemUpdate(BaseModel):
    price: float | None = None
    is_available: bool | None = None
