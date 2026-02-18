from pydantic import BaseModel

class CategoryCreate(BaseModel):
    cafe_id: int
    branch_id: int
    category_name: str
    category_description: str | None = None
    parent_id: int | None = None

class CategoryCreateRequest(BaseModel):
    category_name: str
    category_description: str | None = None
    parent_id: int | None = None



class MenuItemCreate(BaseModel):
    item_name: str
    item_description: str | None = None
    item_type_id: int
    

class MenuItemUpdate(BaseModel):
    item_name: str | None = None
    item_description: str | None = None



class BranchMenuItemCreate(BaseModel):
    item_id: int
    category_id: int
    price: float


class BranchMenuItemUpdate(BaseModel):
    price: float | None = None
    is_available: bool | None = None


class MenuItemOut(BaseModel):
    branch_menu_item_id: int
    item_id: int
    name: str
    price: float
    image: str | None
    is_veg: bool
    is_available: bool
    category_name: str

class MenuCategoryOut(BaseModel):
    category_id: int
    category_name: str
    items: list[MenuItemOut]

class BranchMenuOut(BaseModel):
    categories: list[MenuCategoryOut]
