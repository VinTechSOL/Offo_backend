from datetime import datetime, timezone
import logging
from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.modules.payments.models import PaymentAttempt
from app.modules.payments.constants import (
    PaymentAttemptStatus,
    PaymentIntentStatus,
)
from app.modules.orders.repository import OrderRepository

router = APIRouter(
    prefix="/payments/phonepe",
    tags=["PhonePe"],
)

logger = logging.getLogger(__name__)

@router.post("/webhook")
def phonepe_webhook(
    payload: dict,
    db: Session = Depends(get_db),
):
    logger.info(f"PHONEPE WEBHOOK RECEIVED: {payload}")

    merchant_txn_id = payload.get("merchantTransactionId")
    status = payload.get("status")
    transaction_id = payload.get("transactionId")

    if not merchant_txn_id:
        return {"status": "ignored"}

    attempt = (
        db.query(PaymentAttempt)
        .filter(
            PaymentAttempt.attempt_id == int(merchant_txn_id)
        )
        .first()
    )

    if not attempt:
        return {"status": "attempt_not_found"}

    # ===============================
    # Idempotency Protection
    # ===============================

    if attempt.status == PaymentAttemptStatus.SUCCESS.value:
        return {
            "status": "already_processed"
        }

    intent = attempt.intent

    if not intent:
        return {
            "status": "intent_not_found"
        }

    order = OrderRepository.get_order(
        db,
        intent.order_id,
    )

    if not order:
        return {
            "status": "order_not_found"
        }

    # Save gateway txn id if provided
    if transaction_id:
        attempt.gateway_transaction_id = transaction_id

    # ===============================
    # SUCCESS
    # ===============================

    if status == "SUCCESS":

        attempt.status = (
            PaymentAttemptStatus.SUCCESS.value
        )

        attempt.completed_at = datetime.now(
            timezone.utc
        )

        if attempt.parent_payment_id:
            # REFUND SUCCESS

            intent.status = (
                PaymentIntentStatus.REFUNDED.value
            )

            order.payment_status = "REFUNDED"

            logger.info(
                f" REFUND SUCCESS | "
                f"order={order.order_id}"
            )

        else:
            # PAYMENT SUCCESS

            intent.status = (
                PaymentIntentStatus.SUCCEEDED.value
            )

            order.payment_status = "PAID"

            logger.info(
                f" PAYMENT SUCCESS | "
                f"order={order.order_id}"
            )

    # ===============================
    # FAILURE
    # ===============================

    else:

        attempt.status = (
            PaymentAttemptStatus.FAILED.value
        )

        attempt.completed_at = datetime.now(
            timezone.utc
        )

        if attempt.parent_payment_id:

            intent.status = (
                PaymentIntentStatus.REFUND_FAILED.value
            )

            logger.info(
                f" REFUND FAILED | "
                f"order={order.order_id}"
            )

        else:

            intent.status = (
                PaymentIntentStatus.FAILED.value
            )

            logger.info(
                f" PAYMENT FAILED | "
                f"order={order.order_id}"
            )

    db.commit()

    return {
        "status": "ok"
    }