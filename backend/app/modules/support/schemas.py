from datetime import datetime

from pydantic import BaseModel, Field

from app.modules.support.constants import (
    TicketStatus,
    TicketIssueType,
)


# =========================================================
# USER - TICKET
# =========================================================

class TicketCreate(BaseModel):
    order_id: int

    order_item_id: int | None = None

    issue_type: TicketIssueType

    description: str = Field(
        ...,
        min_length=10,
        max_length=5000,
    )


class TicketResponse(BaseModel):
    ticket_id: int

    order_id: int
    order_item_id: int | None

    issue_type: str
    description: str

    image_url: str | None

    status: TicketStatus

    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True


class UserTicketListItem(BaseModel):
    ticket_id: int

    order_id: int
    issue_type: str
    status: TicketStatus

    created_at: datetime
    updated_at: datetime


# =========================================================
# TICKET MESSAGES
# =========================================================

class TicketMessageCreate(BaseModel):
    message: str = Field(
        ...,
        min_length=1,
        max_length=5000,
    )


class TicketMessageResponse(BaseModel):
    message_id: int
    ticket_id: int

    sender_type: str
    sender_id: int

    message: str

    created_at: datetime

    class Config:
        from_attributes = True


class TicketDetailResponse(BaseModel):
    ticket_id: int

    order_id: int
    order_item_id: int | None

    issue_type: str
    description: str

    image_url: str | None

    status: TicketStatus

    created_at: datetime
    updated_at: datetime

    messages: list[TicketMessageResponse] = Field(
        default_factory=list
    )

    class Config:
        from_attributes = True


# =========================================================
# ADMIN - TICKET
# =========================================================

class AdminTicketResponse(BaseModel):
    ticket_id: int

    display_ticket_id: str

    order_id: int
    display_order_id: str

    user_id: int
    customer_name: str

    cafe_id: int
    cafe_name: str

    branch_id: int

    issue_type: str
    description: str

    order_item_id: int | None
    item_name: str | None

    image_url: str | None

    status: TicketStatus

    created_at: datetime
    updated_at: datetime


class TicketStatusUpdate(BaseModel):
    status: TicketStatus


# =========================================================
# FEEDBACK
# =========================================================

class FeedbackCreate(BaseModel):
    order_id: int

    food_rating: int = Field(
        ...,
        ge=1,
        le=5,
    )

    app_rating: int = Field(
        ...,
        ge=1,
        le=5,
    )

    comments: str | None = Field(
        default=None,
        max_length=5000,
    )


class FeedbackResponse(BaseModel):
    feedback_id: int

    order_id: int

    food_rating: int
    app_rating: int

    comments: str | None

    created_at: datetime

    class Config:
        from_attributes = True


class AdminFeedbackResponse(BaseModel):
    feedback_id: int

    display_feedback_id: str

    order_id: int
    display_order_id: str

    user_id: int
    customer_name: str

    cafe_id: int
    cafe_name: str

    branch_id: int

    food_rating: int
    app_rating: int

    comments: str | None

    created_at: datetime