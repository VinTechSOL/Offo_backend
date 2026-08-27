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
from app.modules.orders.constants import PaymentStatus
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
        order_ids=data.order_ids,
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
        "message": "Refund request processed",
        "order_id": order_id,
        "status": result.get("status"),
        "refund_attempt_id": (
            result["refund_attempt"].attempt_id
            if result.get("refund_attempt")
            else None
        ),
        "merchant_refund_id": (
            result.get("merchant_refund_id")
        ),
        "refund_id": (
            result.get("refund_id")
        ),
        "state": (
            result.get("state")
        ),
        "amount": (
            result.get("amount")
        ),
    }

@router.get(
    "/refund/status/{order_id}",
)
def refund_status(
    order_id: int,
    db: Session = Depends(get_db),
    user=Depends(get_current_user),
):
    """
    Return the refund status for one specific order.

    Important:

    A PaymentIntent may contain multiple orders.

    Therefore this endpoint always resolves the refund
    attempt using:

        intent_id + order_id

    and never returns another order's refund attempt.
    """

    # ============================================================
    # 1. LOAD ORDER
    # ============================================================

    order = OrderRepository.get_order(
        db,
        order_id,
    )

    if not order:
        raise HTTPException(
            status_code=404,
            detail="Order not found",
        )

    # ============================================================
    # 2. OWNERSHIP
    # ============================================================

    if order.user_id != user.user_id:
        raise HTTPException(
            status_code=403,
            detail="Unauthorized",
        )

    # ============================================================
    # 3. FIND PAYMENT INTENT
    # ============================================================

    intent = PaymentRepository.get_intent_by_order(
        db,
        order_id,
    )

    if not intent:
        raise HTTPException(
            status_code=404,
            detail="Payment not found",
        )

    # ============================================================
    # 4. SYNC REFUND
    # ============================================================

    # If a refund is currently active, synchronize it with
    # PhonePe first.
    #
    # If there is no refund attempt yet, the service will
    # return the appropriate error.

    if order.payment_status == PaymentStatus.REFUND_PENDING.value:

        try:

            intent = PaymentService.sync_refund_status(
                db=db,
                order_id=order_id,
            )

            db.refresh(order)

        except HTTPException as e:

            # If refund has not actually been initiated yet,
            # still allow the endpoint to return the local state.

            if e.detail not in (
                "Refund attempt not found for order",
                "Refund is not currently active",
            ):
                raise

    # ============================================================
    # 5. GET REFUND ATTEMPT FOR THIS ORDER ONLY
    # ============================================================

    refund_attempt = (
        PaymentRepository
        .get_latest_refund_attempt_for_order(
            db=db,
            intent_id=intent.intent_id,
            order_id=order_id,
        )
    )

    # ============================================================
    # 6. RESPONSE
    # ============================================================

    return {
        "order_id": order_id,

        "order_payment_status": (
            order.payment_status
        ),

        "intent_id": intent.intent_id,

        "intent_status": (
            intent.status
        ),

        "refund_attempt_id": (
            refund_attempt.attempt_id
            if refund_attempt
            else None
        ),

        "refund_attempt_status": (
            refund_attempt.status
            if refund_attempt
            else None
        ),

        "refund_amount": (
            float(refund_attempt.amount)
            if refund_attempt
            and refund_attempt.amount is not None
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