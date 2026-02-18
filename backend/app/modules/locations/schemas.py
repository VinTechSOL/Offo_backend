from pydantic import BaseModel


class CityResponse(BaseModel):
    city: str


class CampusResponse(BaseModel):
    campus: str


class BuildingResponse(BaseModel):
    building: str

class UserContextCreateRequest(BaseModel):
    city_id: int
    campus_id: int
    building_id: int | None


class UserContextResponse(BaseModel):
    city_id: int
    campus_id: int
    building_id: int
    is_active: bool

    class Config:
        from_attributes = True