from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.core.security import get_current_user
from app.modules.payments.schemas import (
    PaymentInitiateRequest,
    PaymentIntentResponse,
    PaymentInitiateResponse,
    PaymentStatusResponse,
)
from app.modules.payments.constants import PaymentGateway
from app.modules.payments.service import PaymentService
from app.modules.payments.repository import PaymentRepository
from app.modules.orders.repository import OrderRepository


router = APIRouter(prefix="/payments", tags=["Payments"])


@router.post(
    "/initiate",
    response_model=PaymentInitiateResponse,
)
def initiate_payment(
    data: PaymentInitiateRequest,
    db: Session = Depends(get_db),
    user=Depends(get_current_user),
):
    result = PaymentService.initiate_payment(
        db=db,
        user_id=user.user_id,
        order_id=data.order_id,
        gateway=PaymentGateway.PHONEPE,
    )

    return PaymentInitiateResponse(
        intent=result["intent"],
        checkout_url=result["checkout_url"],
    )


@router.get("/order/{order_id}", response_model=PaymentIntentResponse)
def get_payment_for_order(
    order_id: int,
    db: Session = Depends(get_db),
    user=Depends(get_current_user),
):
    order = OrderRepository.get_order(
        db,
        order_id,
    )

    if not order:
        raise HTTPException(
            status_code=404,
            detail="Order not found",
        )

    if order.user_id != user.user_id:
        raise HTTPException(
            status_code=403,
            detail="Unauthorized",
        )

    intent = PaymentRepository.get_intent_by_order(
        db,
        order_id,
    )

    if not intent:
        raise HTTPException(
            status_code=404,
            detail="Payment not found",
        )

    return intent


@router.post("/refund/{order_id}")
def refund_payment(
    order_id: int,
    db: Session = Depends(get_db),
    user=Depends(get_current_user),
):
    result = PaymentService.initiate_refund(
        db=db,
        order_id=order_id,
        user_id=user.user_id,
    )

    return {
        "message": "Refund initiated",
        "order_id": order_id,
        "refund_attempt_id": (
            result["refund_attempt"].attempt_id
        ),
        "merchant_refund_id": result["merchant_refund_id"],
        "refund_id": result["refund_id"],
        "state": result["state"],
        "amount": result["amount"],
    }

@router.get(
    "/refund/status/{order_id}",
)
def refund_status(
    order_id: int,
    db: Session = Depends(get_db),
    user=Depends(get_current_user),
):
    order = OrderRepository.get_order(
        db,
        order_id,
    )

    if not order:
        raise HTTPException(
            status_code=404,
            detail="Order not found",
        )

    if order.user_id != user.user_id:
        raise HTTPException(
            status_code=403,
            detail="Unauthorized",
        )

    intent = PaymentService.sync_refund_status(
        db=db,
        order_id=order_id,
    )

    refund_attempt = PaymentRepository.get_refund_attempt(
        db,
        intent.intent_id,
    )

    return {
        "order_id": order_id,
        "payment_status": order.payment_status,
        "intent_status": intent.status,
        "refund_attempt_status": (
            refund_attempt.status
            if refund_attempt
            else None
        ),
        "merchant_refund_id": (
            refund_attempt.merchant_refund_id
            if refund_attempt
            else None
        ),
        "gateway_refund_id": (
            refund_attempt.gateway_refund_id
            if refund_attempt
            else None
        ),

        "refund_transaction_id": (
            refund_attempt.gateway_transaction_id
            if refund_attempt
            else None
        ),
    }



@router.get(
    "/status/{order_id}",
    response_model=PaymentStatusResponse,
)
def payment_status(
    order_id: int,
    db: Session = Depends(get_db),
    user=Depends(get_current_user),
):
    return PaymentService.get_payment_status(
        db=db,
        user_id=user.user_id,
        order_id=order_id,
    )


@router.post(
    "/retry/{order_id}",
    response_model=PaymentInitiateResponse,
)
def retry_payment(
    order_id: int,
    db: Session = Depends(get_db),
    user=Depends(get_current_user),
):
    result = PaymentService.retry_payment(
        db=db,
        user_id=user.user_id,
        order_id=order_id,
    )

    return PaymentInitiateResponse(
        intent=result["intent"],
        checkout_url=result["checkout_url"],
    )


@router.post("/cancel/{order_id}")
def cancel_payment(
    order_id: int,
    db: Session = Depends(get_db),
    user=Depends(get_current_user),
):
    return PaymentService.cancel_payment(
        db=db,
        user_id=user.user_id,
        order_id=order_id,
    )