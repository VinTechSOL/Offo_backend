from pydantic import BaseModel
from datetime import time
class CafeteriaCreate(BaseModel):
    cafe_name: str
    phone_number: str
    email_id: str | None = None


class CafeBranchCreate(BaseModel):
    cafe_id: int
    branch_name: str
    city_id : int
    campus_id: int
    building_id: int | None = None
    opens_at: time
    closes_at: time
    is_active: bool = True

class UpdateBranchStatusRequest(BaseModel):
    is_active: bool


class UpdateBranchRequest(BaseModel):
    branch_name: str
    city_id: int
    campus_id: int
    building_id: int | None = None
    opens_at: time
    closes_at: time
    is_active: bool = True

class CafeForUserResponse(BaseModel):
    branch_id: int
    branch_name: str
    image_url: str | None
    building_name: str | None
    campus_name: str
    city_name: str
    opens_at: time
    closes_at: time
    is_open: bool

    class Config:
        from_attributes = True
