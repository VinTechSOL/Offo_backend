import logging

from sqlalchemy.orm import Session

from app.core.database import SessionLocal
from app.modules.orders.models import Order
from app.modules.orders.constants import PaymentStatus
from app.modules.payments.models import (
    PaymentIntent,
)
from app.modules.payments.constants import (
    PaymentIntentStatus,
    PaymentAttemptStatus,
)
from app.modules.payments.repository import PaymentRepository
from app.modules.payments.service import PaymentService


logger = logging.getLogger(__name__)


MAX_REFUNDS_PER_RUN = 20


def process_pending_refunds():
    """
    Process orders waiting for refund.

    Order-level flow:

        REFUND_PENDING
              ↓
        PaymentIntent.SUCCEEDED
              ↓
        initiate_refund_internal()
              ↓
        RefundAttempt
              ↓
        REFUND_INITIATED
              ↓
        PhonePe
              ↓
        sync_refund_status()
              ↓
        Order REFUNDED
              ↓
        If all linked orders refunded:
              PaymentIntent REFUNDED

    IMPORTANT:

    A PaymentIntent may contain multiple orders.

    Therefore each refund is processed independently
    for the specific order that was cancelled/rejected.
    """

    db: Session = SessionLocal()

    processed = 0
    skipped = 0
    failed = 0

    try:

        # ========================================================
        # 1. FIND ORDERS WAITING FOR REFUND
        # ========================================================

        orders = (
            db.query(Order)
            .filter(
                Order.payment_status
                == PaymentStatus.REFUND_PENDING.value,
            )
            .order_by(
                Order.updated_at.asc()
            )
            .limit(MAX_REFUNDS_PER_RUN)
            .all()
        )

        logger.info(
            "Refund processor found %s pending refunds",
            len(orders),
        )

        # ========================================================
        # 2. PROCESS EACH ORDER
        # ========================================================

        for order in orders:

            try:

                logger.info(
                    "Processing refund | order=%s",
                    order.order_id,
                )

                # ------------------------------------------------
                # Re-check payment state
                # ------------------------------------------------

                if (
                    order.payment_status
                    != PaymentStatus.REFUND_PENDING.value
                ):
                    skipped += 1
                    continue

                # ------------------------------------------------
                # Get payment intent
                # ------------------------------------------------

                intent = (
                    PaymentRepository
                    .get_intent_by_order_for_update(
                        db,
                        order.order_id,
                    )
                )

                if not intent:

                    logger.error(
                        "Refund pending order has no "
                        "payment intent | order=%s",
                        order.order_id,
                    )

                    skipped += 1
                    continue

                # =================================================
                # FIND REFUND ATTEMPT FOR THIS ORDER
                # =================================================

                refund_attempt = (
                    PaymentRepository
                    .get_refund_attempt_for_order_for_update(
                        db=db,
                        intent_id=intent.intent_id,
                        order_id=order.order_id,
                    )
                )

                # =================================================
                # NO REFUND ATTEMPT YET
                # =================================================

                if not refund_attempt:

                    logger.info(
                        "No refund attempt exists | "
                        "order=%s intent=%s",
                        order.order_id,
                        intent.intent_id,
                    )

                    # ------------------------------------------------
                    # Payment must have succeeded before refund.
                    # ------------------------------------------------

                    if intent.status not in (
                        PaymentIntentStatus.SUCCEEDED.value,
                        PaymentIntentStatus.REFUND_FAILED.value,
                    ):
                        logger.warning(
                            "Order waiting for refund but intent "
                            "not refund eligible | "
                            "order=%s intent_status=%s",
                            order.order_id,
                            intent.status,
                        )

                        skipped += 1
                        continue

                    # ------------------------------------------------
                    # Start a brand-new refund.
                    # ------------------------------------------------

                    PaymentService.initiate_refund_internal(
                        db=db,
                        order_id=order.order_id,
                    )

                    processed += 1
                    continue

                # =================================================
                # ALREADY REFUNDED
                # =================================================

                if (
                    refund_attempt.status
                    == PaymentAttemptStatus.SUCCESS.value
                ):

                    logger.info(
                        "Refund already completed | "
                        "order=%s refund_attempt=%s",
                        order.order_id,
                        refund_attempt.attempt_id,
                    )

                    # The order should normally already be
                    # REFUNDED. This is defensive recovery.

                    if (
                        order.payment_status
                        == PaymentStatus.REFUND_PENDING.value
                    ):
                        try:
                            PaymentService.sync_refund_status(
                                db=db,
                                order_id=order.order_id,
                            )
                        except Exception:
                            logger.exception(
                                "Failed to reconcile already "
                                "successful refund | order=%s",
                                order.order_id,
                            )
                            db.rollback()
                            failed += 1
                            continue

                    skipped += 1
                    continue

                # =================================================
                # REFUND CURRENTLY ACTIVE
                # =================================================

                if (
                    refund_attempt.status
                    in (
                        PaymentAttemptStatus.INITIATED.value,
                        PaymentAttemptStatus.REDIRECTED.value,
                    )
                ):

                    logger.info(
                        "Checking existing refund | "
                        "order=%s refund_attempt=%s "
                        "merchant_refund_id=%s",
                        order.order_id,
                        refund_attempt.attempt_id,
                        refund_attempt.merchant_refund_id,
                    )

                    # ------------------------------------------------
                    # IMPORTANT:
                    #
                    # NEVER create another refund here.
                    #
                    # We already have a merchant_refund_id.
                    #
                    # Query PhonePe for this SAME refund.
                    # ------------------------------------------------

                    PaymentService.sync_refund_status(
                        db=db,
                        order_id=order.order_id,
                    )

                    processed += 1
                    continue

                # =================================================
                # REFUND FAILED
                # =================================================

                if (
                    refund_attempt.status
                    == PaymentAttemptStatus.FAILED.value
                ):

                    logger.warning(
                        "Retrying failed refund | "
                        "order=%s refund_attempt=%s",
                        order.order_id,
                        refund_attempt.attempt_id,
                    )

                    PaymentService.initiate_refund_internal(
                        db=db,
                        order_id=order.order_id,
                    )

                    processed += 1
                    continue

                # =================================================
                # UNKNOWN REFUND ATTEMPT STATE
                # =================================================

                logger.error(
                    "Invalid refund attempt state | "
                    "order=%s intent=%s "
                    "refund_attempt=%s status=%s",
                    order.order_id,
                    intent.intent_id,
                    refund_attempt.attempt_id,
                    refund_attempt.status,
                )

                skipped += 1

            except Exception:

                db.rollback()

                failed += 1

                logger.exception(
                    "Refund processing failed | order=%s",
                    order.order_id,
                )

        # ========================================================
        # FINAL SUMMARY
        # ========================================================

        logger.info(
            "Refund processor finished | "
            "processed=%s skipped=%s failed=%s",
            processed,
            skipped,
            failed,
        )

    except Exception:

        db.rollback()

        logger.exception(
            "Refund processor crashed",
        )

    finally:

        db.close()