from pydantic import BaseModel
from datetime import datetime
from typing import Optional


class PaymentInitiateRequest(BaseModel):
    order_id: int
    gateway: str  # PHONEPE (for now)


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
    order_id: int
    amount: float
    status: str
    created_at: datetime
    attempts: list[PaymentAttemptResponse]

    class Config:
        from_attributes = True
