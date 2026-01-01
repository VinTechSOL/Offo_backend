from pydantic import BaseModel
from typing import Optional
from datetime import date

class PlaceOrderRequest(BaseModel):
    order_type: str  # INSTANT / SCHEDULED
    scheduled_date: Optional[date] = None
    scheduled_time: Optional[str] = None  # "09:30 AM"
    repeat_weekly: bool = False


class PlaceOrderResponse(BaseModel):
    order_id: int
    status: str
