from fastapi import APIRouter, Depends, Request
from sqlalchemy.orm import Session
import logging

from app.core.database import get_db
from app.modules.payments.gateways.phonepe.client import PhonePeClient
from app.modules.payments.repository import PaymentRepository
from app.modules.payments.service import PaymentService

router = APIRouter(
    prefix="/payments/phonepe",
    tags=["PhonePe"],
)

logger = logging.getLogger(__name__)


@router.post("/webhook")
async def phonepe_webhook(
    request: Request,
    db: Session = Depends(get_db),
):
    """
    PhonePe Server-to-Server callback.

    The callback is only used as a trigger.

    We NEVER trust callback payload for payment state.
    We always fetch the latest status directly from PhonePe.
    """

    authorization = request.headers.get("Authorization")

    if not authorization:
        logger.warning("Missing Authorization header")

        return {
            "status": "missing_authorization",
        }

    body = await request.body()

    client = PhonePeClient()

    try:
        callback = client.validate_callback(
            authorization=authorization,
            body=body.decode(),
        )

    except Exception as e:
        logger.exception("PhonePe callback validation failed : %s", str(e))

        return {
            "status": "invalid_callback"
        }

    merchant_order_id = getattr(
        callback.payload,
        "original_merchant_order_id",
        None,
    )

    if not merchant_order_id:
        logger.warning("Merchant order id missing in callback")
        return {
            "status": "invalid_payload",
        }

    logger.info(
        "PhonePe callback received for merchant_order_id=%s",merchant_order_id
    )

    attempt = PaymentRepository.get_attempt_by_merchant_order_id(
        db,
        merchant_order_id,
    )

    if not attempt:

        logger.warning(
            "Attempt not found for merchant_order_id=%s",merchant_order_id
        )

        return {
            "status": "attempt_not_found"
        }

    try:
        PaymentService.sync_payment_status(
            db=db,
            order_id=attempt.intent.order_id,
        )

    except Exception:
        logger.exception(
            "Failed to sync payment status for %s", merchant_order_id,
        )

        return {
            "status": "sync_failed",
        }

    logger.info(
        "payment synced successfully for %s", merchant_order_id,
    )

    

    return {
        "status": "ok"
    }