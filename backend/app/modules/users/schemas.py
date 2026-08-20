from pydantic import BaseModel, Field
from datetime import datetime
from typing import Optional

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




class OrderDetailItemResponse(BaseModel):
    item_id: int
    name: str
    quantity: int
    price_at_time: float
    image_url: str | None = None


class OrderBillResponse(BaseModel):
    subtotal: float
    convenience_fee: float
    total: float


class OrderPaymentResponse(BaseModel):
    status: str
    transaction_id: str | None = None
    paid_at: datetime | None = None


class OrderDetailTimelineResponse(BaseModel):
    status: str
    changed_by: str
    changed_by_id: int | None = None
    created_at: datetime


class UserOrderDetailResponse(BaseModel):
    order_id: int

    # --------------------------------------------------
    # Order
    # --------------------------------------------------

    order_type: str
    order_status: str
    payment_status: str

    scheduled_time: datetime | None = None
    created_at: datetime
    updated_at: datetime | None = None

    # --------------------------------------------------
    # Cafe / Branch
    # --------------------------------------------------

    cafe_id: int
    cafe_name: str | None = None
    branch_id: int

    # --------------------------------------------------
    # Amount
    # --------------------------------------------------

    bill: OrderBillResponse

    # --------------------------------------------------
    # Items
    # --------------------------------------------------

    items: list[OrderDetailItemResponse] = Field(
        default_factory=list
    )

    # --------------------------------------------------
    # Payment
    # --------------------------------------------------

    payment: OrderPaymentResponse

    # --------------------------------------------------
    # Timeline
    # --------------------------------------------------

    timeline: list[OrderDetailTimelineResponse] = Field(
        default_factory=list
    )