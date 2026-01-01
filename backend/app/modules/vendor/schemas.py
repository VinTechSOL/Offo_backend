from pydantic import BaseModel

class CafeteriaCreate(BaseModel):
    cafe_name: str
    phone_number: str
    email_id: str | None = None


class CafeBranchCreate(BaseModel):
    cafe_id: int
    branch_name: str
    email_id: str | None = None
