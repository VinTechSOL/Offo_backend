from pydantic import BaseModel
from datetime import datetime


class NotificationResponse(BaseModel):
    id: int
    title: str
    message: str
    priority: str
    is_read: bool
    created_at: datetime
    related_order_id: int | None = None
    event_type: str

    class Config:
        from_attributes = True
