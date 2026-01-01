from pydantic import BaseModel

class UserProfileUpdate(BaseModel):
    first_name: str
    last_name: str


class UserResponse(BaseModel):
    user_id: int
    first_name: str | None
    last_name: str | None
    mobile_number: str


class AddressCreate(BaseModel):
    address_line_1: str
    city: str
    state: str
    country: str
    pincode: str
