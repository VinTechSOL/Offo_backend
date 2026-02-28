from pydantic import BaseModel
from datetime import datetime

class StaffLoginRequest(BaseModel):
    username: str
    password: str


class StaffLoginResponse(BaseModel):
    access_token: str
    token_type: str = "Bearer"
    role: str

class VendorCreateRequest(BaseModel):
    first_name: str
    last_name: str
    username: str
    password: str
    branch_id: int


class VendorResponse(BaseModel):
    staff_id: int
    first_name: str
    last_name: str
    username: str
    branch_id: int
    is_active: bool
    created_at: datetime

    class Config:
        from_attributes = True