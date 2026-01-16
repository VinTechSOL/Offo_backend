from pydantic import BaseModel


class PhonePeInitiateResponse(BaseModel):
    success: bool
    code: str
    message: str
    data: dict | None
