from pydantic import BaseModel
from typing import Optional,List
from datetime import date ,datetime

class PlaceOrderRequest(BaseModel):
    order_type: str  # INSTANT / SCHEDULED
    scheduled_date: Optional[date] = None
    scheduled_time: Optional[str] = None  # "09:30 AM"
    repeat_weekly: bool = False


class PlaceOrderResponse(BaseModel):
    order_id: int
    status: str

class OrderItemResponse(BaseModel):
    item_id: int
    name: str
    quantity: int
    price_at_time: float

    class Config:
        orm_mode = True

class OrderResponse(BaseModel):
    order_id: int

    # Ownership
    user_id: int
    branch_id: int
    cafe_id: int

    # Order info
    order_type: str                 # INSTANT / SCHEDULED
    order_status: str               # CREATED / ACCEPTED / PREPARING / READY / COMPLETED
    payment_status: str             # PENDING / PAID / FAILED

    # Timing
    scheduled_time: Optional[datetime] = None
    created_at: datetime
    updated_at: Optional[datetime] = None

    # Amount
    total_amount: float

    # Flags (useful for UI)
    is_active: Optional[bool] = None                # computed in service
    is_scheduled: Optional[bool] = None 

    # Items
    items: List[OrderItemResponse] = []

    class Config:
        orm_mode = True


class OrderTimelineItem(BaseModel):
    status: str
    changed_by: str
    changed_by_id: int | None
    created_at: datetime

    class Config:
        from_attributes = True
