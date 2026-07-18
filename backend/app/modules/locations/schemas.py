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


class CreateCityRequest(BaseModel):
    city_name: str


class CreateCampusRequest(BaseModel):
    city_id: int
    campus_name: str


class CreateBuildingRequest(BaseModel):
    campus_id: int
    building_name: str
    latitude: float | None = None
    longitude: float | None = None

class BuildingTreeResponse(BaseModel):
    building_id: int
    building_name: str


class CampusTreeResponse(BaseModel):
    campus_id: int
    campus_name: str
    buildings: list[BuildingTreeResponse]


class CityTreeResponse(BaseModel):
    city_id: int
    city_name: str
    campuses: list[CampusTreeResponse]


class UpdateCityRequest(BaseModel):
    city_name: str


class UpdateCampusRequest(BaseModel):
    campus_name: str


class UpdateBuildingRequest(BaseModel):
    building_name: str
    latitude: float | None = None
    longitude: float | None = None