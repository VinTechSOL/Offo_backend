from pydantic import BaseModel, Field
from typing import Optional
from datetime import date ,datetime
from app.modules.orders.constants import PaymentStatus,OrderStatus

class ScheduleItem(BaseModel):
    scheduled_date: date
    scheduled_time: str

class PlaceOrderRequest(BaseModel):
    order_type: str  # INSTANT / SCHEDULED
    schedules: list[ScheduleItem] = Field(
        default_factory=list
    )
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
    order_status: OrderStatus      # CREATED / ACCEPTED / PREPARING / READY / COMPLETED
    payment_status: PaymentStatus            # PENDING / PAID / FAILED

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
    items: list[OrderItemResponse] = Field(
        default_factory=list
    )

    class Config:
        orm_mode = True


class OrderTimelineItem(BaseModel):
    status: str
    changed_by: str
    changed_by_id: int | None
    created_at: datetime

    class Config:
        from_attributes = True


class MoveOrderRequest(BaseModel):
    status: OrderStatus
