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
)
from app.modules.payments.service import PaymentService


logger = logging.getLogger(__name__)


MAX_REFUNDS_PER_RUN = 20


def process_pending_refunds():
    """
    Process orders that are waiting for refund.

    Flow:

        REFUND_PENDING
              ↓
        PaymentIntent.SUCCEEDED
              ↓
        initiate_refund_internal()
              ↓
        REFUND_INITIATED
              ↓
        PhonePe
              ↓
        sync_refund_status()
              ↓
        REFUNDED / REFUND_FAILED
    """

    db: Session = SessionLocal()

    processed = 0
    skipped = 0
    failed = 0

    try:

        # --------------------------------------------------------
        # Find refund-pending orders
        # --------------------------------------------------------

        orders = (
            db.query(Order)
            .filter(
                Order.payment_status
                == PaymentStatus.REFUND_PENDING,
            )
            .order_by(
                Order.updated_at.asc()
            )
            .limit(MAX_REFUNDS_PER_RUN)
            .with_for_update(
                skip_locked=True,
            )
            .all()
        )

        logger.info(
            "Refund processor found %s pending refunds",
            len(orders),
        )

        for order in orders:

            try:

                # ------------------------------------------------
                # Re-check payment state
                # ------------------------------------------------

                if (
                    order.payment_status
                    != PaymentStatus.REFUND_PENDING
                ):
                    skipped += 1
                    continue

                # ------------------------------------------------
                # Get intent
                # ------------------------------------------------

                intent = (
                    db.query(PaymentIntent)
                    .filter(
                        PaymentIntent.order_id
                        == order.order_id
                    )
                    .first()
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
                # ALREADY REFUNDED
                # =================================================

                if (
                    intent.status
                    == PaymentIntentStatus.REFUNDED.value
                ):

                    logger.info(
                        "Refund already completed | order=%s",
                        order.order_id,
                    )

                    skipped += 1
                    continue

                # =================================================
                # REFUND CURRENTLY PROCESSING
                # =================================================

                if (
                    intent.status
                    == PaymentIntentStatus.REFUND_INITIATED.value
                ):

                    logger.info(
                        "Checking existing refund | order=%s",
                        order.order_id,
                    )

                    # Do not create another refund.
                    #
                    # Ask PhonePe for the status of the
                    # existing refund attempt.

                    PaymentService.sync_refund_status(
                        db=db,
                        order_id=order.order_id,
                    )

                    processed += 1
                    continue

                # =================================================
                # REFUND FAILED
                #
                # This is retryable.
                # =================================================

                if (
                    intent.status
                    == PaymentIntentStatus.REFUND_FAILED.value
                ):

                    logger.warning(
                        "Retrying failed refund | order=%s",
                        order.order_id,
                    )

                    # initiate_refund_internal() accepts
                    # REFUND_FAILED and creates a new attempt.
                    PaymentService.initiate_refund_internal(
                        db=db,
                        order_id=order.order_id,
                    )

                    processed += 1
                    continue

                # =================================================
                # INITIAL REFUND
                # =================================================

                if (
                    intent.status
                    == PaymentIntentStatus.SUCCEEDED.value
                ):

                    logger.info(
                        "Starting refund | order=%s",
                        order.order_id,
                    )

                    PaymentService.initiate_refund_internal(
                        db=db,
                        order_id=order.order_id,
                    )

                    processed += 1
                    continue

                # =================================================
                # INVALID STATE
                # =================================================

                logger.error(
                    "Invalid refund state | "
                    "order=%s intent_status=%s",
                    order.order_id,
                    intent.status,
                )

                skipped += 1

            except Exception:

                db.rollback()

                failed += 1

                logger.exception(
                    "Refund processing failed | order=%s",
                    order.order_id,
                )

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