from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.modules.payments.models import PaymentAttempt
from app.modules.payments.constants import (
    PaymentAttemptStatus,
    PaymentIntentStatus,
)
from app.modules.orders.repository import OrderRepository

router = APIRouter(prefix="/payments/phonepe", tags=["PhonePe"])

@router.post("/webhook")
def phonepe_webhook(payload: dict, db: Session = Depends(get_db)):
    print("📥 PHONEPE WEBHOOK RECEIVED:", payload)

    merchant_txn_id = payload.get("merchantTransactionId")
    status = payload.get("status")

    if not merchant_txn_id:
        return {"status": "ignored"}

    attempt = (
        db.query(PaymentAttempt)
        .filter(PaymentAttempt.attempt_id == int(merchant_txn_id))
        .first()
    )

    if not attempt:
        return {"status": "attempt not found"}

    intent = attempt.intent
    order = OrderRepository.get_order(db, intent.order_id)

    if status == "SUCCESS":
        attempt.status = PaymentAttemptStatus.SUCCESS

        if attempt.parent_payment_id:
            # REFUND SUCCESS
            intent.status = PaymentIntentStatus.REFUNDED
            order.payment_status = "REFUNDED"
            print(f"💸 REFUND SUCCESS | order={order.order_id}")
        else:
            # PAYMENT SUCCESS
            intent.status = PaymentIntentStatus.SUCCEEDED
            order.payment_status = "PAID"
            print(f"💰 PAYMENT SUCCESS | order={order.order_id}")

    else:
        attempt.status = PaymentAttemptStatus.FAILED
        intent.status = PaymentIntentStatus.FAILED

    db.commit()
    return {"status": "ok"}
