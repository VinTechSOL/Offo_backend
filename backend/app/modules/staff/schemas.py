from pydantic import BaseModel


class StaffLoginRequest(BaseModel):
    username: str
    password: str


class StaffLoginResponse(BaseModel):
    access_token: str
    token_type: str = "Bearer"
    role: str
