from sqlalchemy.orm import Session
from fastapi import HTTPException
from datetime import datetime, timezone
import logging
from sqlalchemy.exc import IntegrityError
from requests.exceptions import ReadTimeout, ConnectionError
from phonepe.sdk.pg.common.exceptions import PhonePeException

from app.modules.orders.repository import OrderRepository
from app.modules.orders.payment_service import OrderPaymentService
from app.modules.orders.constants import PaymentStatus, OrderStatus

from app.modules.payments.repository import PaymentRepository
from app.modules.payments.constants import (
    PaymentGateway,
    PaymentIntentStatus,
    PaymentAttemptStatus,
)
from app.modules.payments.gateways.phonepe.client import PhonePeClient
from app.modules.payments.utils import (
    generate_merchant_order_id,
    generate_merchant_refund_id,
)

from requests.exceptions import ReadTimeout, ConnectionError

logger = logging.getLogger(__name__)


class PaymentService:

    # ============================================================
    # INITIATE PAYMENT
    # ============================================================

    @staticmethod
    def initiate_payment(
        db: Session,
        user_id: int,
        order_id: int,
        gateway: str,
    ):
        order = OrderRepository.get_order(
            db,
            order_id,
        )

        if not order or order.user_id != user_id:
            raise HTTPException(
                status_code=404,
                detail="Order not found",
            )

        if order.order_status not in (
            OrderStatus.CREATED.value,
            OrderStatus.CANCELLED.value,
        ):
            raise HTTPException(
                status_code=400,
                detail="Order is not eligible for payment"
            )

        if order.payment_status in [
            PaymentStatus.PAID.value,
            PaymentStatus.REFUNDED.value,
        ]:
            raise HTTPException(
                status_code=400,
                detail="Order already paid",
            )

        # --------------------------------------------------------
        # Get or create payment intent
        # --------------------------------------------------------

        intent = PaymentRepository.get_intent_by_order(
            db,
            order_id,
        )

        if not intent:

            try:
                intent = PaymentRepository.create_intent(
                    db,
                    order_id=order.order_id,
                    amount=order.total_amount,
                )

                db.commit()

            except IntegrityError:

                
                # Another concurrent request may have created
                # the unique payment intent for this order.
                db.rollback()

                intent = PaymentRepository.get_intent_by_order(
                    db,
                    order_id,
                )

                if not intent:
                    raise


        # --------------------------------------------------------
        # LOCK PAYMENT INTENT
        # --------------------------------------------------------
        #
        # This is the important race-condition protection.
        #
        # Only one request can inspect/create an active attempt
        # for this payment intent at a time.
        #

        intent = PaymentRepository.get_intent_by_order_for_update(
            db,
            order_id,
        )

        if not intent:
            raise HTTPException(
                status_code=404,
                detail="Payment intent not found",
            )


        # --------------------------------------------------------
        # Reuse active attempt
        # --------------------------------------------------------

        active_attempt = PaymentRepository.get_active_attempt(
            db,
            intent.intent_id,
        )

        if (
            active_attempt
            and active_attempt.response_payload
        ):
            logger.info(
                "♻️ Reusing active payment attempt %s",
                active_attempt.attempt_id,
            )

            return {
                "intent": intent,
                "checkout_url": (
                    active_attempt
                    .response_payload
                    .get("redirect_url")
                ),
            }

        # --------------------------------------------------------
        # Create new payment attempt
        # --------------------------------------------------------

        merchant_order_id = generate_merchant_order_id()

        attempt = PaymentRepository.create_attempt(
            db=db,
            intent_id=intent.intent_id,
            gateway=gateway,
            merchant_order_id=merchant_order_id,
        )

        intent.status = PaymentIntentStatus.PROCESSING.value

        db.commit()
        db.refresh(intent)

        logger.info(
            "💳 PAYMENT INITIATED | "
            "order=%s intent=%s attempt=%s",
            order_id,
            intent.intent_id,
            attempt.attempt_id,
        )

        # --------------------------------------------------------
        # PhonePe
        # --------------------------------------------------------

        if gateway == PaymentGateway.PHONEPE:

            client = PhonePeClient()

            try:
                response = client.initiate_payment(
                    merchant_order_id=merchant_order_id,
                    order_id=order.order_id,
                    amount=int(intent.amount * 100),
                    user_id=user_id,
                )

            except PhonePeException as e:

                logger.exception(
                    "PhonePe initiate payment failed: %s",
                    str(e),
                )

                db.rollback()

                attempt.status = (
                    PaymentAttemptStatus.FAILED.value
                )

                attempt.response_payload = {
                    "error": getattr(
                        e,
                        "message",
                        str(e),
                    ),
                    "http_status": getattr(
                        e,
                        "http_status_code",
                        None,
                    ),
                }

                intent.status = (
                    PaymentIntentStatus.FAILED.value
                )

                # ------------------------------------------------
                # Order payment state belongs to OrderPaymentService
                # ------------------------------------------------

                OrderPaymentService.sync_payment_status(
                    db=db,
                    order_id=order_id,
                    payment_status=PaymentStatus.FAILED,
                    provider_reference=merchant_order_id,
                )

                db.commit()

                raise HTTPException(
                    status_code=502,
                    detail=(
                        "Unable to connect to payment gateway. "
                        "Please try again."
                    ),
                )

            PaymentRepository.save_phonepe_order(
                db=db,
                attempt=attempt,
                phonepe_order_id=response["phonepe_order_id"],
                response=response,
            )

            return {
                "intent": intent,
                "checkout_url": response["redirect_url"],
            }

        return {
            "intent": intent,
            "checkout_url": None,
        }

    # ============================================================
    # RETRY PAYMENT
    # ============================================================

    @staticmethod
    def retry_payment(
        db: Session,
        user_id: int,
        order_id: int,
    ):
        """
        Retry a failed/cancelled payment.

        A new PaymentAttempt is created under the
        existing PaymentIntent.
        """

        order = OrderRepository.get_order(
            db,
            order_id,
        )

        if not order:
            raise HTTPException(
                status_code=404,
                detail="Order not found",
            )

        if order.user_id != user_id:
            raise HTTPException(
                status_code=403,
                detail="Unauthorized",
            )

        if order.payment_status in [
            PaymentStatus.PAID.value,
            PaymentStatus.REFUNDED.value,
        ]:
            raise HTTPException(
                status_code=400,
                detail="Order already paid",
            )

        intent = PaymentRepository.get_intent_by_order(
            db,
            order_id,
        )

        if not intent:
            raise HTTPException(
                status_code=404,
                detail="Payment intent not found",
            )

        merchant_order_id = generate_merchant_order_id()

        attempt = PaymentRepository.create_attempt(
            db=db,
            intent_id=intent.intent_id,
            gateway=PaymentGateway.PHONEPE,
            merchant_order_id=merchant_order_id,
        )

        intent.status = PaymentIntentStatus.PROCESSING.value

        db.commit()
        db.refresh(intent)

        logger.info(
            "🔁 PAYMENT RETRY | "
            "order=%s intent=%s attempt=%s",
            order.order_id,
            intent.intent_id,
            attempt.attempt_id,
        )

        client = PhonePeClient()

        try:
            response = client.initiate_payment(
                merchant_order_id=merchant_order_id,
                order_id=order.order_id,
                amount=int(intent.amount * 100),
                user_id=user_id,
            )

        except PhonePeException as e:

            logger.exception(
                "PhonePe retry payment failed: %s",
                str(e),
            )

            db.rollback()

            attempt.status = (
                PaymentAttemptStatus.FAILED.value
            )

            attempt.response_payload = {
                "error": getattr(
                    e,
                    "message",
                    str(e),
                ),
                "http_status": getattr(
                    e,
                    "http_status_code",
                    None,
                ),
            }

            intent.status = (
                PaymentIntentStatus.FAILED.value
            )

            OrderPaymentService.sync_payment_status(
                db=db,
                order_id=order_id,
                payment_status=PaymentStatus.FAILED,
                provider_reference=merchant_order_id,
            )

            db.commit()

            raise HTTPException(
                status_code=502,
                detail=(
                    "Unable to connect to payment gateway. "
                    "Please try again."
                ),
            )

        PaymentRepository.save_phonepe_order(
            db=db,
            attempt=attempt,
            phonepe_order_id=response["phonepe_order_id"],
            response=response,
        )

        return {
            "intent": intent,
            "checkout_url": response["redirect_url"],
        }

    # ============================================================
    # INITIATE REFUND
    # ============================================================

    @staticmethod
    def initiate_refund(
        db: Session,
        order_id: int,
        user_id: int,
    ):
        """
        Start a PhonePe refund.

        The order may be:

            PAID
            OR
            REFUND_PENDING

        REFUND_PENDING is important because the order service may
        already have marked the order for refund due to:

            - vendor rejection
            - automatic cancellation
            - another business rule

        In that situation this method only starts the actual
        gateway refund.
        """

        order = OrderRepository.get_order(
            db,
            order_id,
        )

        if not order or order.user_id != user_id:
            raise HTTPException(
                status_code=404,
                detail="Order not found",
            )

        current_payment_status = PaymentStatus(
            order.payment_status
        )

        # --------------------------------------------------------
        # Order must be PAID or already awaiting refund
        # --------------------------------------------------------

        if current_payment_status not in (
            PaymentStatus.PAID,
            PaymentStatus.REFUND_PENDING,
        ):
            raise HTTPException(
                status_code=400,
                detail="Order is not eligible for refund",
            )

        intent = PaymentRepository.get_intent_by_order_for_update(
            db,
            order_id,
        )

        if not intent:
            raise HTTPException(
                status_code=400,
                detail="Payment intent not found",
            )

        # --------------------------------------------------------
        # Already refunded
        # --------------------------------------------------------

        if intent.status == PaymentIntentStatus.REFUNDED.value:
            raise HTTPException(
                status_code=400,
                detail="Order already refunded",
            )

        # --------------------------------------------------------
        # Refund currently processing
        # --------------------------------------------------------

        if intent.status == PaymentIntentStatus.REFUND_INITIATED.value:

            raise HTTPException(
                status_code=400,
                detail="Refund already initiated",
            )

        # --------------------------------------------------------
        # We need a successful original payment
        # --------------------------------------------------------

        payment_attempt = next(
            (
                attempt
                for attempt in intent.attempts
                if (
                    attempt.status
                    == PaymentAttemptStatus.SUCCESS.value
                    and attempt.parent_payment_id is None
                    and attempt.merchant_order_id
                )
            ),
            None,
        )

        if not payment_attempt:

            raise HTTPException(
                status_code=400,
                detail="Successful payment attempt not found",
            )

        # --------------------------------------------------------
        # Intent must be in a refund-compatible state
        # --------------------------------------------------------

        if intent.status not in (
            PaymentIntentStatus.SUCCEEDED.value,
            PaymentIntentStatus.REFUND_FAILED.value,
        ):
            raise HTTPException(
                status_code=400,
                detail="Payment is not eligible for refund",
            )

        #-----------------------------------------
        # 5. Check for existing refund attempt
        # -----------------------------------------

        existing_refund = PaymentRepository.get_refund_attempt_for_update(
           db,
           intent.intent_id,
        )

        if existing_refund:
            if existing_refund.status in (
                PaymentAttemptStatus.INITIATED.value,
                PaymentAttemptStatus.REDIRECTED.value,
            ):
                raise HTTPException(
                  status_code=400,
                  detail="Refund already initiated",
                )


            if existing_refund.status in (
                PaymentAttemptStatus.SUCCESS.value,
            ):
                raise HTTPException(
                  status_code=400,
                  detail="Refund already completed",
                )

            #Failed refund attempts are allowed to be retried

        # --------------------------------------------------------
        # Create refund attempt
        # --------------------------------------------------------

        refund_attempt = PaymentRepository.create_refund_attempt(
            db=db,
            intent_id=intent.intent_id,
            parent_attempt_id=payment_attempt.attempt_id,
            gateway=payment_attempt.gateway,
        )

        merchant_refund_id = generate_merchant_refund_id()

        # Existing schema uses merchant_order_id for refund ID.
        refund_attempt.merchant_refund_id = merchant_refund_id

        # --------------------------------------------------------
        # Mark internal refund state
        # --------------------------------------------------------

        intent.status = (
            PaymentIntentStatus.REFUND_INITIATED.value
        )

        db.commit()

        db.refresh(refund_attempt)
        db.refresh(intent)

        logger.info(
            "🔄 REFUND CREATED | "
            "order=%s intent=%s refund_attempt=%s "
            "merchant_refund_id=%s",
            order_id,
            intent.intent_id,
            refund_attempt.attempt_id,
            merchant_refund_id,
        )

        # --------------------------------------------------------
        # Call PhonePe
        # --------------------------------------------------------

        client = PhonePeClient()

        try:

            response = client.initiate_refund(
                merchant_refund_id=merchant_refund_id,
                amount=int(intent.amount * 100),
                original_merchant_order_id=(
                    payment_attempt.merchant_order_id
                ),
            )

        except PhonePeException as e:

            logger.exception(
                "PhonePe refund failed: %s",
                str(e),
            )

            refund_attempt.status = (
                PaymentAttemptStatus.FAILED.value
            )

            refund_attempt.response_payload = {
                "error": getattr(
                    e,
                    "message",
                    str(e),
                ),
                "http_status": getattr(
                    e,
                    "http_status_code",
                    None,
                ),
            }

            intent.status = (
                PaymentIntentStatus.REFUND_FAILED.value
            )

            # IMPORTANT:
            # Order remains REFUND_PENDING.
            #
            # This records the failed gateway operation while
            # keeping the order eligible for retry.

            OrderPaymentService.mark_refund_failed(
                db=db,
                order_id=order_id,
                provider_reference=merchant_refund_id,
                commit=False,
            )

            db.commit()

            raise HTTPException(
                status_code=502,
                detail=(
                    "Unable to initiate refund with "
                    "payment gateway. Please try again."
                ),
            )

        # --------------------------------------------------------
        # Save PhonePe refund response
        # --------------------------------------------------------

        PaymentRepository.save_phonepe_refund(
            db=db,
            attempt=refund_attempt,
            merchant_refund_id=merchant_refund_id,
            gateway_refund_id=response["refund_id"],
            response=response,
        )

        return {
            "intent": intent,
            "refund_attempt": refund_attempt,
            "refund_id": response["refund_id"],
            "merchant_refund_id": merchant_refund_id,
            "state": response["state"],
            "amount": response["amount"],
        }

    # ============================================================
    # SYNC PAYMENT STATUS
    # ============================================================

    @staticmethod
    def sync_payment_status(
        db: Session,
        order_id: int,
        merchant_order_id: str | None = None,
    ):
        """
        Fetch latest payment status from PhonePe and synchronize:

            PhonePe
                ↓
            PaymentAttempt
                ↓
            PaymentIntent
                ↓
            OrderPaymentService
                ↓
            Order.payment_status
                ↓
            PaymentEvent
        """

        intent = PaymentRepository.get_intent_by_order(
            db,
            order_id,
        )

        if not intent:
            raise HTTPException(
                status_code=404,
                detail="Payment not found",
            )

        # --------------------------------------------------------
        # Final payment states
        # --------------------------------------------------------

        if intent.status in (
            PaymentIntentStatus.SUCCEEDED.value,
            PaymentIntentStatus.FAILED.value,
            PaymentIntentStatus.REFUNDED.value,
        ):
            return intent

        # --------------------------------------------------------
        # Get attempts
        # --------------------------------------------------------

        if merchant_order_id:
            payment_attempt = (
               PaymentRepository.get_attempt_by_merchant_order_id(
                    db,
                    merchant_order_id,
                )
            )

            if not payment_attempt:
                raise HTTPException(
                    status_code=404,
                    detail="Payment attempt not found",
                )

            if payment_attempt.intent_id != intent.intent_id:
                raise HTTPException(
                    status_code=400,
                    detail="Payment attempt does not belong to order",
                )

        else:
            payment_attempt = (
                PaymentRepository.get_latest_payment_attempt(
                  db,
                  intent.intent_id,
                )
            )

        if not payment_attempt:
            return intent

        client = PhonePeClient()

        try:

            status = client.get_order_status(
                payment_attempt.merchant_order_id,
            )

            logger.info(
                "========== PHONEPE STATUS =========="
            )
            logger.info(
                "Order ID: %s",
                order_id,
            )
            logger.info(
                "Merchant Order ID: %s",
                payment_attempt.merchant_order_id,
            )
            logger.info(
                "State: %s",
                status.get("state"),
            )
            logger.info(
                "Payment Details: %s",
                status.get("payment_details"),
            )
            logger.info(
                "====================================="
            )

        except (ReadTimeout, ConnectionError):

            logger.warning(
                "PhonePe order status timed out. Will retry."
            )

            return intent

        except PhonePeException as e:

            logger.exception(
                "PhonePe sync failed: %s",
                getattr(e, "message", str(e)),
            )

            raise HTTPException(
                status_code=502,
                detail="Unable to fetch payment status.",
            )

        # --------------------------------------------------------
        # Save latest PhonePe response
        # --------------------------------------------------------

        payment_attempt.phonepe_order_id = (
            status.get("phonepe_order_id")
        )

        payment_attempt.response_payload = status

        payment_details = (
            status.get("payment_details")
            or []
        )

        transaction_id = None

        if payment_details:

            transaction_id = (
                payment_details[-1]
                .get("transaction_id")
            )

            payment_attempt.gateway_transaction_id = (
                transaction_id
            )


        # ========================================================
        #PAYMENT AMOUNT VERIFICATION
        # ========================================================

        gateway_amount = status.get("amount")

        if gateway_amount is not None:
            expected_amount = int(intent.amount * 100)

            if int(gateway_amount) != expected_amount:
                logger.error(
                    "Payment amount mismatch | "
                    "order=%s expected=%s gateway=%s",
                    order_id,
                    expected_amount,
                    gateway_amount,
                )

                payment_attempt.status = (
                    PaymentAttemptStatus.FAILED.value
                )

                intent.status = (
                    PaymentIntentStatus.FAILED.value
                )

                OrderPaymentService.sync_payment_status(
                    db=db,
                    order_id=order_id,
                    payment_status=PaymentStatus.FAILED,
                    provider_reference=(
                        payment_attempt.merchant_order_id
                    ),
                    commit=False,
                )

                db.commit()

                raise HTTPException(
                    status_code=400,
                    detail="Payment amount verification failed",
                )

        

        # ========================================================
        # EXPIRY
        # ========================================================

        expiry = None

        expire_at = status.get("expire_at")

        if expire_at:

            expiry = datetime.fromtimestamp(
                expire_at / 1000,
                tz=timezone.utc,
            )

        if (
            expiry
            and datetime.now(timezone.utc) > expiry
            and status.get("state") == "PENDING"
        ):

            payment_attempt.status = (
                PaymentAttemptStatus.EXPIRED.value
            )

            intent.status = (
                PaymentIntentStatus.FAILED.value
            )

            OrderPaymentService.sync_payment_status(
                db=db,
                order_id=order_id,
                payment_status=PaymentStatus.FAILED,
                provider_reference=(
                    payment_attempt.merchant_order_id
                ),
                provider_transaction_id=transaction_id,
                commit=False,
            )

            db.commit()

            db.refresh(intent)

            logger.info(
                "⏰ PAYMENT EXPIRED | order=%s",
                order_id,
            )

            return intent

        # ========================================================
        # PHONEPE COMPLETED
        # ========================================================

        if status.get("state") == "COMPLETED":

            payment_attempt.status = (
                PaymentAttemptStatus.SUCCESS.value
            )

            payment_attempt.completed_at = (
                datetime.now(timezone.utc)
            )

            intent.status = (
                PaymentIntentStatus.SUCCEEDED.value
            )

            OrderPaymentService.sync_payment_status(
                db=db,
                order_id=order_id,
                payment_status=PaymentStatus.PAID,
                provider_reference=(
                    payment_attempt.merchant_order_id
                ),
                provider_transaction_id=transaction_id,
                commit=False,
            )

            db.commit()

            db.refresh(intent)

            logger.info(
                "✅ PAYMENT COMPLETED | order=%s",
                order_id,
            )

            return intent

        # ========================================================
        # PHONEPE FAILED
        # ========================================================

        if status.get("state") == "FAILED":

            payment_attempt.status = (
                PaymentAttemptStatus.FAILED.value
            )

            payment_attempt.completed_at = (
                datetime.now(timezone.utc)
            )

            intent.status = (
                PaymentIntentStatus.FAILED.value
            )

            OrderPaymentService.sync_payment_status(
                db=db,
                order_id=order_id,
                payment_status=PaymentStatus.FAILED,
                provider_reference=(
                    payment_attempt.merchant_order_id
                ),
                provider_transaction_id=transaction_id,
                commit=False,
            )

            db.commit()

            db.refresh(intent)

            logger.info(
                "❌ PAYMENT FAILED | order=%s",
                order_id,
            )

            return intent


        

        # --------------------------------------------------------
        # Still pending
        # --------------------------------------------------------

        db.commit()

        return intent

    # ============================================================
    # GET PAYMENT STATUS
    # ============================================================

    @staticmethod
    def get_payment_status(
        db: Session,
        user_id: int,
        order_id: int,
    ):
        """
        Returns latest payment status.

        If payment is still PROCESSING,
        synchronize with PhonePe first.
        """

        order = OrderRepository.get_order(
            db,
            order_id,
        )

        if not order:
            raise HTTPException(
                status_code=404,
                detail="Order not found",
            )

        if order.user_id != user_id:
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

        if intent.status == PaymentIntentStatus.PROCESSING.value:

            PaymentService.sync_payment_status(
                db=db,
                order_id=order_id,
            )

            db.refresh(intent)
            db.refresh(order)

        attempt = PaymentRepository.get_latest_attempt(
            db,
            intent.intent_id,
        )

        redirect_url = None

        if (
            attempt
            and attempt.response_payload
        ):
            redirect_url = (
                attempt.response_payload
                .get("redirect_url")
            )

        return {
            "order_id": order.order_id,
            "payment_status": order.payment_status,
            "intent_status": intent.status,
            "attempt_status": (
                attempt.status
                if attempt
                else None
            ),
            "redirect_url": redirect_url,
            "transaction_id": (
                attempt.gateway_transaction_id
                if attempt
                else None
            ),
        }

    # ============================================================
    # CANCEL PAYMENT
    # ============================================================

    @staticmethod
    def cancel_payment(
        db: Session,
        user_id: int,
        order_id: int,
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

        if order.user_id != user_id:
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

        latest_attempt = PaymentRepository.get_latest_attempt(
            db,
            intent.intent_id,
        )

        if not latest_attempt:
            raise HTTPException(
                status_code=404,
                detail="Payment attempt not found",
            )

        if latest_attempt.status not in [
            PaymentAttemptStatus.INITIATED.value,
            PaymentAttemptStatus.REDIRECTED.value,
        ]:
            return {
                "message": "Payment already completed",
            }

        PaymentRepository.mark_attempt_cancelled(
            db,
            latest_attempt,
        )

        intent.status = (
            PaymentIntentStatus.CANCELLED.value
        )

        db.commit()

        return {
            "message": "Payment cancelled",
        }

    
    # ============================================================
    #  REFUND Internal system Initiation
    # ============================================================

    @staticmethod
    def initiate_refund_internal(
        db: Session,
        order_id: int,
    ):
        """
        Internal/system refund initiation.

        Used by:
        - vendor rejection
        - automatic order cancellation
        - system workflows

        This method does NOT perform user authorization.

        Important:

        This method creates a NEW refund attempt only when
        there is no currently active refund attempt.
        """

        order = OrderRepository.get_order(
            db,
            order_id,
        )

        if not order:
            raise HTTPException(
                status_code=404,
                detail="Order not found",
            )

        if order.payment_status != PaymentStatus.REFUND_PENDING.value:
            raise HTTPException(
                status_code=400,
                detail="Order is not awaiting refund",
            )

        intent = PaymentRepository.get_intent_by_order_for_update(
            db,
            order_id,
        )

        if not intent:
            raise HTTPException(
                status_code=400,
                detail="Payment intent not found",
            )

        if intent.status == PaymentIntentStatus.REFUNDED.value:
            return {
               "status": "already_refunded",
               "order_id": order_id,
            }

        if intent.status == PaymentIntentStatus.REFUND_INITIATED.value:
            return {
                "status": "already_initiated",
                "order_id": order_id,
            }

        # --------------------------------------------------------
        # Existing active refund
        #
        # NEVER create another refund while one is active.
        # --------------------------------------------------------

        active_refund = (
            PaymentRepository.get_active_refund_attempt(
                db,
                intent.intent_id,
            )
        )

        if active_refund:

            logger.info(
                "Refund already active | "
                "order=%s refund_attempt=%s",
                order_id,
                active_refund.attempt_id,
            )

            return {
                "status": "already_initiated",
                "order_id": order_id,
                "refund_attempt": active_refund,
                "merchant_refund_id": (
                    active_refund.merchant_refund_id
                ),
            }

        # --------------------------------------------------------
        # Payment must have succeeded
        # --------------------------------------------------------

        if intent.status not in (
            PaymentIntentStatus.SUCCEEDED.value,
            PaymentIntentStatus.REFUND_FAILED.value,
        ):
            raise HTTPException(
                status_code=400,
                detail="Payment is not eligible for refund",
            )

        # --------------------------------------------------------
        # Find successful original payment
        # --------------------------------------------------------
        payment_attempt = (
            PaymentRepository
            .get_latest_successful_payment_attempt(
                db,
                intent.intent_id,
            )
        )

        if not payment_attempt:
            raise HTTPException(
                status_code=400,
                detail="Successful payment attempt not found",
            )

        # --------------------------------------------------------
        # Create refund attempt
        # --------------------------------------------------------

        refund_attempt = (
            PaymentRepository.create_refund_attempt(
                db=db,
                intent_id=intent.intent_id,
                parent_attempt_id=payment_attempt.attempt_id,
                gateway=payment_attempt.gateway,
            )
        )

        merchant_refund_id = (
            generate_merchant_refund_id()
        )

        refund_attempt.merchant_refund_id = (
            merchant_refund_id
        )

        intent.status = (
            PaymentIntentStatus.REFUND_INITIATED.value
        )

        db.commit()

        db.refresh(refund_attempt)
        db.refresh(intent)

        logger.info(
            "REFUND INITIATED | "
            "order=%s intent=%s attempt=%s merchant_refund_id=%s",
            order_id,
            intent.intent_id,
            refund_attempt.attempt_id,
            merchant_refund_id,
        )

        # --------------------------------------------------------
        # Call PhonePe
        # --------------------------------------------------------

        client = PhonePeClient()

        try:

            response = client.initiate_refund(
                merchant_refund_id=merchant_refund_id,
                amount=int(intent.amount * 100),
                original_merchant_order_id=(
                    payment_attempt.merchant_order_id
                ),
            )

        except (ReadTimeout, ConnectionError) as e:

            logger.warning(
                "PhonePe refund request outcome unknown | "
                "order=%s merchant_refund_id=%s error=%s",
                order_id,
                merchant_refund_id,
                str(e),
            )     

            # We do NOT know whether PhonePe received the request.
            #
            # Therefore:
            # - keep refund attempt INITIATED
            # - keep intent REFUND_INITIATED
            # - DO NOT create another refund attempt
            #
            # The next processor run will call
            # sync_refund_status() using this same merchant_refund_id.

            refund_attempt.status = (
               PaymentAttemptStatus.INITIATED.value
            )

            refund_attempt.response_payload = {
               "error": str(e),
               "outcome": "UNKNOWN",
            }

            intent.status = (
                PaymentIntentStatus.REFUND_INITIATED.value
            )

            db.commit()

            return {
                "status": "processing",
                "order_id": order_id,
                "refund_attempt": refund_attempt,
                "merchant_refund_id": merchant_refund_id,
                "state": "UNKNOWN",
            }  

        except (PhonePeException) as e:

            logger.exception(
                "PhonePe internal refund failed: %s",
                getattr(e, "message", str(e)),
            )

            refund_attempt.status = (
                PaymentAttemptStatus.FAILED.value
            )

            refund_attempt.response_payload = {
                "error": getattr(
                    e,
                    "message",
                    str(e),
                ),
                "http_status": getattr(
                    e,
                    "http_status_code",
                    None,
                ),
            }

            intent.status = (
                PaymentIntentStatus.REFUND_FAILED.value
            )

            db.commit()

            # IMPORTANT:
            #
            # Order.payment_status remains REFUND_PENDING.
            #
            # The refund processor can retry.

            raise

        PaymentRepository.save_phonepe_refund(
            db=db,
            attempt=refund_attempt,
            merchant_refund_id=merchant_refund_id,
            gateway_refund_id=response["refund_id"],
            response=response,
        )

        # --------------------------------------------------------
        # PhonePe may return PROCESSING.
        #
        # Do NOT mark the refund SUCCESS here unless PhonePe
        # explicitly says COMPLETED.
        # --------------------------------------------------------

        if response["state"] == "COMPLETED":

            refund_attempt.status = (
                PaymentAttemptStatus.SUCCESS.value
            )

            refund_attempt.completed_at = (
                datetime.now(timezone.utc)
            )

            intent.status = (
                PaymentIntentStatus.REFUNDED.value
            )

            OrderPaymentService.mark_refunded(
                db=db,
                order_id=order_id,
                provider_reference=merchant_refund_id,
                provider_transaction_id=None,
                commit=False,
            )

            db.commit()

            return {
                "status": "refunded",
                "order_id": order_id,
                "refund_attempt": refund_attempt,
                "merchant_refund_id": merchant_refund_id,
                "refund_id": response["refund_id"],
                "state": response["state"],
                "amount": response["amount"],
            }

        # --------------------------------------------------------
        # Still processing
        # --------------------------------------------------------

        return {
            "status": "initiated",
            "order_id": order_id,
            "refund_attempt": refund_attempt,
            "merchant_refund_id": merchant_refund_id,
            "refund_id": response["refund_id"],
            "state": response["state"],
            "amount": response["amount"],
        }

    # ============================================================
    # SYNC REFUND STATUS
    # ============================================================

    @staticmethod
    def sync_refund_status(
        db: Session,
        order_id: int,
    ):
        """
        Fetch the latest refund status from PhonePe.

        Synchronization flow:

            PhonePe
                ↓
            Refund PaymentAttempt
                ↓
            PaymentIntent
                ↓
            OrderPaymentService
                ↓
            Order.payment_status
                ↓
            PaymentEvent
        """

        intent = PaymentRepository.get_intent_by_order(
            db,
            order_id,
        )

        if not intent:
            raise HTTPException(
                status_code=404,
                detail="Payment intent not found",
            )

        # --------------------------------------------------------
        # Already final
        # --------------------------------------------------------

        if intent.status in [
            PaymentIntentStatus.REFUNDED.value,
        ]:
            return intent

        if intent.status != (
            PaymentIntentStatus.REFUND_INITIATED.value
        ):
            raise HTTPException(
                status_code=400,
                detail="Refund has not been initiated",
            )

        # --------------------------------------------------------
        # Find refund attempt
        # --------------------------------------------------------

        refund_attempt = PaymentRepository.get_refund_attempt(
            db,
            intent.intent_id,
        )

        if not refund_attempt:
            raise HTTPException(
                status_code=404,
                detail="Refund attempt not found",
            )

        if not refund_attempt.merchant_refund_id:
            raise HTTPException(
                status_code=400,
                detail="Merchant refund ID not found",
            )

        client = PhonePeClient()

        # --------------------------------------------------------
        # Fetch PhonePe refund status
        # --------------------------------------------------------

        try:

            status = client.get_refund_status(
                merchant_refund_id=(
                    refund_attempt.merchant_refund_id
                ),
            )

        except (ReadTimeout, ConnectionError):

            logger.warning(
                "PhonePe refund status timed out. Will retry."
            )

            return intent

        except PhonePeException as e:

            logger.exception(
                "PhonePe refund status failed: %s",
                getattr(e, "message", str(e)),
            )

            raise HTTPException(
                status_code=502,
                detail="Unable to fetch refund status.",
            )

        # --------------------------------------------------------
        # Save raw gateway response
        # --------------------------------------------------------

        PaymentRepository.save_refund_status(
            db=db,
            attempt=refund_attempt,
            response=status,
        )

        gateway_state = status.get("state")

        logger.info(
            "REFUND STATUS | "
            "order=%s refund_attempt=%s state=%s",
            order_id,
            refund_attempt.attempt_id,
            gateway_state,
        )

        # --------------------------------------------------------
        # Extract refund transaction
        # --------------------------------------------------------

        payment_details = (
            status.get("payment_details")
            or []
        )

        refund_transaction_id = None

        if payment_details:

            latest_detail = payment_details[-1]

            if latest_detail.get("transaction_id"):

                refund_transaction_id = (
                    latest_detail["transaction_id"]
                )

                refund_attempt.gateway_transaction_id = (
                    refund_transaction_id
                )

            if latest_detail.get("state"):

                gateway_state = (
                    latest_detail["state"]
                )

        # ========================================================
        # REFUND COMPLETED
        # ========================================================

        if gateway_state == "COMPLETED":

            refund_attempt.status = (
                PaymentAttemptStatus.SUCCESS.value
            )

            refund_attempt.completed_at = (
                datetime.now(timezone.utc)
            )

            intent.status = (
                PaymentIntentStatus.REFUNDED.value
            )

            # ----------------------------------------------------
            # Order status is changed ONLY through
            # OrderPaymentService.
            # ----------------------------------------------------

            OrderPaymentService.mark_refunded(
                db=db,
                order_id=order_id,
                provider_reference=(
                    refund_attempt.merchant_refund_id
                ),
                provider_transaction_id=(
                    refund_transaction_id
                ),
                commit=False,
            )

            db.commit()

            db.refresh(intent)

            logger.info(
                "✅ REFUND COMPLETED | order=%s",
                order_id,
            )

            return intent

        # ========================================================
        # REFUND FAILED
        # ========================================================

        if gateway_state == "FAILED":

            refund_attempt.status = (
                PaymentAttemptStatus.FAILED.value
            )

            intent.status = (
                PaymentIntentStatus.REFUND_FAILED.value
            )

            # ----------------------------------------------------
            # IMPORTANT:
            #
            # Order remains REFUND_PENDING.
            #
            # This means money is still owed back to the customer
            # and the refund can be retried.
            # ----------------------------------------------------

            OrderPaymentService.mark_refund_failed(
                db=db,
                order_id=order_id,
                provider_reference=(
                    refund_attempt.merchant_refund_id
                ),
                provider_transaction_id=(
                    refund_transaction_id
                ),
                commit=False,
            )

            db.commit()

            db.refresh(intent)

            logger.warning(
                "❌ REFUND FAILED | order=%s",
                order_id,
            )

            return intent

        # ========================================================
        # STILL PROCESSING
        # ========================================================

        db.commit()

        return intent