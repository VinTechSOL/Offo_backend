from fastapi import APIRouter, Depends, Request
from sqlalchemy.orm import Session
import logging

from app.core.database import get_db

from app.modules.payments.gateways.phonepe.client import (
    PhonePeClient,
)

from app.modules.payments.repository import (
    PaymentRepository,
)

from app.modules.payments.service import (
    PaymentService,
)


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

    IMPORTANT:

    The webhook is only a trigger.

    We do NOT trust the callback payment/refund state.

    We use the callback identifier to find the local
    payment/refund attempt and then fetch the authoritative
    status directly from PhonePe.
    """

    # ============================================================
    # AUTHORIZATION
    # ============================================================

    authorization = request.headers.get(
        "Authorization"
    )

    if not authorization:

        logger.warning(
            "PhonePe webhook missing Authorization header"
        )

        return {
            "status": "missing_authorization",
        }

    # ============================================================
    # READ BODY
    # ============================================================

    body = await request.body()

    client = PhonePeClient()

    # ============================================================
    # VALIDATE CALLBACK
    # ============================================================

    try:

        callback = client.validate_callback(
            authorization=authorization,
            body=body.decode(),
        )

    except Exception as e:

        logger.exception(
            "PhonePe callback validation failed: %s",
            str(e),
        )

        return {
            "status": "invalid_callback",
        }

    # ============================================================
    # CALLBACK PAYLOAD
    # ============================================================

    payload = getattr(
        callback,
        "payload",
        None,
    )

    if not payload:

        logger.warning(
            "PhonePe callback payload missing"
        )

        return {
            "status": "invalid_payload",
        }

    # ------------------------------------------------------------
    # TEMPORARY DEBUG LOG
    # ------------------------------------------------------------
    #
    # Keep this while testing PhonePe sandbox callbacks.
    #
    # It helps us confirm the exact SDK payload structure,
    # especially for refund callbacks.
    #

    logger.info(
        "PhonePe validated callback payload: %s",
        payload,
    )

    # ============================================================
    # PAYMENT CALLBACK
    # ============================================================

    merchant_order_id = getattr(
        payload,
        "original_merchant_order_id",
        None,
    )

    if merchant_order_id:

        logger.info(
            "PhonePe payment callback received | "
            "merchant_order_id=%s",
            merchant_order_id,
        )

        attempt = (
            PaymentRepository
            .get_attempt_by_merchant_order_id(
                db,
                merchant_order_id,
            )
        )

        if not attempt:

            logger.warning(
                "Payment attempt not found | "
                "merchant_order_id=%s",
                merchant_order_id,
            )

            return {
                "status": "attempt_not_found",
            }

        try:

            PaymentService.sync_payment_status(
                db=db,
                order_id=attempt.intent.order_id,
                merchant_order_id=(
                    attempt.merchant_order_id
                ),
            )

        except Exception:

            logger.exception(
                "Failed to synchronize payment | "
                "merchant_order_id=%s",
                merchant_order_id,
            )

            return {
                "status": "sync_failed",
            }

        logger.info(
            "PhonePe payment synchronized | "
            "merchant_order_id=%s",
            merchant_order_id,
        )

        return {
            "status": "ok",
            "type": "payment",
        }

    # ============================================================
    # REFUND CALLBACK
    # ============================================================
    #
    # IMPORTANT:
    #
    # We are deliberately checking multiple possible SDK
    # attribute names until the real sandbox callback confirms
    # the exact PhonePe payload structure.
    #

    merchant_refund_id = (
        getattr(
            payload,
            "merchant_refund_id",
            None,
        )
        or getattr(
            payload,
            "original_merchant_refund_id",
            None,
        )
    )

    if merchant_refund_id:

        logger.info(
            "PhonePe refund callback received | "
            "merchant_refund_id=%s",
            merchant_refund_id,
        )

        refund_attempt = (
            PaymentRepository
            .get_refund_attempt_by_merchant_refund_id(
                db,
                merchant_refund_id,
            )
        )

        if not refund_attempt:

            logger.warning(
                "Refund attempt not found | "
                "merchant_refund_id=%s",
                merchant_refund_id,
            )

            return {
                "status": "refund_attempt_not_found",
            }

        try:

            PaymentService.sync_refund_status(
                db=db,
                order_id=refund_attempt.intent.order_id,
            )

        except Exception:

            logger.exception(
                "Failed to synchronize refund | "
                "merchant_refund_id=%s",
                merchant_refund_id,
            )

            return {
                "status": "refund_sync_failed",
            }

        logger.info(
            "PhonePe refund synchronized | "
            "merchant_refund_id=%s",
            merchant_refund_id,
        )

        return {
            "status": "ok",
            "type": "refund",
        }

    # ============================================================
    # UNKNOWN CALLBACK
    # ============================================================

    logger.warning(
        "PhonePe callback did not contain a recognized "
        "payment/refund identifier"
    )

    return {
        "status": "unknown_callback",
    }