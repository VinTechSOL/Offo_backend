from pydantic import BaseModel, Field
from datetime import datetime


class PaymentInitiateRequest(BaseModel):
    order_ids: list[int] = Field(
        min_length=1,
    )

    gateway: str = "PHONEPE"


class PaymentAttemptResponse(BaseModel):
    attempt_id: int
    gateway: str
    status: str
    attempt_number: int
    created_at: datetime

    class Config:
        from_attributes = True


class PaymentIntentResponse(BaseModel):
    intent_id: int

    # Anchor order
    order_id: int

    amount: float
    status: str
    created_at: datetime

    attempts: list[PaymentAttemptResponse]

    class Config:
        from_attributes = True


class PaymentInitiateResponse(BaseModel):
    intent: PaymentIntentResponse
    checkout_url: str | None

    class Config:
        from_attributes = True


class PaymentStatusResponse(BaseModel):
    order_id: int
    payment_status: str
    intent_status: str
    attempt_status: str | None = None
    redirect_url: str | None = None
    transaction_id: str | None = None