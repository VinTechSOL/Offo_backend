from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.core.security import get_current_user
from app.modules.payments.schemas import (
    PaymentInitiateRequest,
    PaymentIntentResponse,
)
from app.modules.payments.constants import PaymentGateway
from app.modules.payments.service import PaymentService
from app.modules.payments.repository import PaymentRepository

router = APIRouter(prefix="/payments", tags=["Payments"])


@router.post("/initiate", response_model=PaymentIntentResponse)
def initiate_payment(
    data: PaymentInitiateRequest,
    db: Session = Depends(get_db),
    user=Depends(get_current_user),
):
    return PaymentService.initiate_payment(
        db=db,
        user_id=user.user_id,
        order_id=data.order_id,
        gateway=PaymentGateway.PHONEPE,
    )


@router.get("/order/{order_id}", response_model=PaymentIntentResponse)
def get_payment_for_order(
    order_id: int,
    db: Session = Depends(get_db),
    user=Depends(get_current_user),
):
    return PaymentRepository.get_intent_by_order(db, order_id)


@router.post("/refund/{order_id}")
def refund_payment(
    order_id: int,
    db: Session = Depends(get_db),
    user=Depends(get_current_user),
):
    """
    Trigger refund for a paid order (FULL REFUND)
    """
    refund_attempt = PaymentService.initiate_refund(
        db=db,
        order_id=order_id,
        user_id=user.user_id,
    )

    return {
        "message": "Refund initiated",
        "refund_attempt_id": refund_attempt.attempt_id,
        "status": refund_attempt.status,
    }