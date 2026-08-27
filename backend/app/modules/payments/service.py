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
from app.modules.payments.models import PaymentIntent
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

from decimal import Decimal


PLATFORM_FEE = Decimal("5.00")
GST_RATE = Decimal("0.18")


def calculate_checkout_fee():
    platform_fee = PLATFORM_FEE

    gst = (
        platform_fee * GST_RATE
    ).quantize(
        Decimal("0.01")
    )

    checkout_fee = platform_fee + gst

    return {
        "platform_fee": platform_fee,
        "gst": gst,
        "checkout_fee": checkout_fee,
    }


logger = logging.getLogger(__name__)


class PaymentService:

    # ============================================================
    # INITIATE PAYMENT
    # ============================================================

    @staticmethod
    def initiate_payment(
        db: Session,
        user_id: int,
        order_ids: list[int],
        gateway: str,
    ):
        # ============================================================
        # 1. NORMALIZE ORDER IDS
        # ============================================================
        order_ids = list(dict.fromkeys(order_ids))

        if not order_ids:
            raise HTTPException(
                status_code=400,
                detail="At least one order is required",
            )

        # ============================================================
        # 2. LOAD + VALIDATE ALL ORDERS
        # ============================================================
        orders = []
        for order_id in order_ids:
            order = OrderRepository.get_order(
                db,
                order_id,
            )

            if not order:
                raise HTTPException(
                    status_code=404,
                    detail=f"Order {order_id} not found",
                )

            if order.user_id != user_id:
                raise HTTPException(
                    status_code=403,
                    detail="Unauthorized order in payment request",
                )

            if order.order_status != OrderStatus.CREATED.value:
                raise HTTPException(
                    status_code=400,
                    detail=f"Order {order_id} is not eligible for payment",
                )

            if order.payment_status in (
                PaymentStatus.PAID.value,
                PaymentStatus.REFUND_PENDING.value,
                PaymentStatus.REFUNDED.value,
            ):
                raise HTTPException(
                    status_code=400,
                    detail=f"Order {order_id} is not eligible for payment",
                )

            orders.append(order)

        # ============================================================
        # 3. VALIDATE SAME CHECKOUT CONTEXT
        # ============================================================
        anchor_order = orders[0]

        for order in orders:
            if order.user_id != anchor_order.user_id:
                raise HTTPException(
                    status_code=400,
                    detail="Orders belong to different users",
                )

            if order.cafe_id != anchor_order.cafe_id:
                raise HTTPException(
                    status_code=400,
                    detail="Orders belong to different cafes",
                )

            if order.branch_id != anchor_order.branch_id:
                raise HTTPException(
                    status_code=400,
                    detail="Orders belong to different branches",
                )

        # ============================================================
        # 4. CHECK FOR EXISTING INTENTS
        # ============================================================
        existing_intents = []
        for order in orders:
            existing = PaymentRepository.get_intent_by_order(
                db,
                order.order_id,
            )
            if existing:
                existing_intents.append(existing)

        if existing_intents:
            unique_intent_ids = {
                intent.intent_id
                for intent in existing_intents
            }

            # Orders cannot already belong to different payments.
            if len(unique_intent_ids) > 1:
                raise HTTPException(
                    status_code=409,
                    detail="Orders are already associated with different payment intents",
                )

            intent = existing_intents[0]

            existing_order_ids = set(
                PaymentRepository.get_order_ids_for_intent(
                    db,
                    intent.intent_id,
                )
            )

            # Legacy/single-order intent may not yet have a link row.
            existing_order_ids.add(intent.order_id)

            if existing_order_ids != set(order_ids):
                raise HTTPException(
                    status_code=409,
                    detail="Payment request does not match the existing checkout",
                )

        else:
            # ========================================================
            # 5. CALCULATE TOTAL ON BACKEND
            # ========================================================
            orders_subtotal = sum(
                (
                    Decimal(str(order.total_amount))
                    for order in orders
                ),
                Decimal("0.00"),
            )

            fee = calculate_checkout_fee()

            platform_fee = fee["platform_fee"]
            gst = fee["gst"]
            checkout_fee = fee["checkout_fee"]

            total_amount = (
                orders_subtotal + checkout_fee
            ).quantize(
                Decimal("0.01")
            )

            # ========================================================
            # 6. CREATE ONE PAYMENT INTENT
            # ========================================================
            try:
                intent = PaymentRepository.create_intent(
                    db=db,
                    order_id=anchor_order.order_id,
                    amount=float(total_amount),
                    platform_fee=float(platform_fee),
                    gst=float(gst),
                    checkout_fee=float(checkout_fee),
                )

                # ====================================================
                # 7. LINK EVERY ORDER TO INTENT
                # ====================================================
                PaymentRepository.add_orders_to_intent(
                    db=db,
                    intent_id=intent.intent_id,
                    order_ids=[
                        order.order_id
                        for order in orders
                    ],
                )

                db.commit()
                db.refresh(intent)

            except IntegrityError:
                db.rollback()
                raise HTTPException(
                    status_code=409,
                    detail="Payment was already created for one or more orders",
                )

        # ============================================================
        # 8. LOCK PAYMENT INTENT
        # ============================================================
        intent = PaymentRepository.get_intent_by_order_for_update(
            db,
            anchor_order.order_id,
        )

        if not intent:
            raise HTTPException(
                status_code=404,
                detail="Payment intent not found",
            )

        # ============================================================
        # 9. ALREADY PAID
        # ============================================================
        if intent.status == PaymentIntentStatus.SUCCEEDED.value:
            raise HTTPException(
                status_code=400,
                detail="Payment already completed",
            )

        # ============================================================
        # 10. REUSE ACTIVE PAYMENT ATTEMPT
        # ============================================================
        active_attempt = PaymentRepository.get_active_attempt(
            db,
            intent.intent_id,
        )

        if (
            active_attempt
            and active_attempt.response_payload
        ):
            logger.info(
                "Reusing active payment attempt %s",
                active_attempt.attempt_id,
            )

            return {
                "intent": intent,
                "checkout_url": (
                    active_attempt.response_payload.get(
                        "redirect_url"
                    )
                ),
            }

        # ============================================================
        # 11. CREATE PHONEPE ATTEMPT
        # ============================================================
        merchant_order_id = generate_merchant_order_id()

        attempt = PaymentRepository.create_attempt(
            db=db,
            intent_id=intent.intent_id,
            gateway=gateway,
            merchant_order_id=merchant_order_id,
            amount=float(intent.amount),
        )

        intent.status = PaymentIntentStatus.PROCESSING.value

        db.commit()
        db.refresh(intent)

        logger.info(
            "PAYMENT INITIATED | orders=%s intent=%s attempt=%s amount=%s",
            order_ids,
            intent.intent_id,
            attempt.attempt_id,
            intent.amount,
        )

        # ============================================================
        # 12. PHONEPE
        # ============================================================
        if gateway == PaymentGateway.PHONEPE:
            client = PhonePeClient()

            try:
                response = client.initiate_payment(
                    merchant_order_id=merchant_order_id,
                    # Anchor order used for redirect.
                    order_id=anchor_order.order_id,
                    # One combined amount.
                    amount=int(intent.amount * 100),
                    user_id=user_id,
                )

            except PhonePeException as e:
                logger.exception(
                    "PhonePe initiate payment failed: %s",
                    str(e),
                )

                attempt.status = PaymentAttemptStatus.FAILED.value
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

                intent.status = PaymentIntentStatus.FAILED.value

                # All linked orders failed payment.
                linked_order_ids = (
                    PaymentRepository.get_order_ids_for_intent(
                        db,
                        intent.intent_id,
                    )
                )

                for linked_order_id in linked_order_ids:
                    OrderPaymentService.sync_payment_status(
                        db=db,
                        order_id=linked_order_id,
                        payment_status=PaymentStatus.FAILED,
                        provider_reference=merchant_order_id,
                        commit=False,
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
                phonepe_order_id=response[
                    "phonepe_order_id"
                ],
                response=response,
            )

            db.commit()

            return {
                "intent": intent,
                "checkout_url": response[
                    "redirect_url"
                ],
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
            amount=float(intent.amount),
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

            PaymentService._sync_payment_status_to_linked_orders(
                db=db,
                intent=intent,
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

        db.commit()

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
        User-initiated refund.

        Refunds are always performed for the specific order.

        IMPORTANT:
        A PaymentIntent may contain multiple orders.
        Therefore:
            PaymentIntent.amount != Refund amount

        The refund amount is always: Order.total_amount
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

        # ------------------------------------------------------------
        # Order must be PAID or already awaiting refund
        # ------------------------------------------------------------
        if current_payment_status not in (
            PaymentStatus.PAID,
            PaymentStatus.REFUND_PENDING,
        ):
            raise HTTPException(
                status_code=400,
                detail="Order is not eligible for refund",
            )

        # ------------------------------------------------------------
        # Lock payment intent
        # ------------------------------------------------------------
        intent = PaymentRepository.get_intent_by_order_for_update(
            db,
            order_id,
        )

        if not intent:
            raise HTTPException(
                status_code=400,
                detail="Payment intent not found",
            )

        # ------------------------------------------------------------
        # Already refunded for this order
        # ------------------------------------------------------------
        existing_refund = (
            PaymentRepository.get_refund_attempt_for_order_for_update(
                db,
                intent.intent_id,
                order_id,
            )
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

            if existing_refund.status == (
                PaymentAttemptStatus.SUCCESS.value
            ):
                raise HTTPException(
                    status_code=400,
                    detail="Refund already completed",
                )

            # FAILED refund is retryable.

        # ------------------------------------------------------------
        # Intent state
        # ------------------------------------------------------------
        if intent.status not in (
            PaymentIntentStatus.SUCCEEDED.value,
            PaymentIntentStatus.REFUND_FAILED.value,
        ):
            raise HTTPException(
                status_code=400,
                detail="Payment is not eligible for refund",
            )

        # ------------------------------------------------------------
        # Find successful original payment
        # ------------------------------------------------------------
        payment_attempt = (
            PaymentRepository.get_latest_successful_payment_attempt(
                db,
                intent.intent_id,
            )
        )

        if not payment_attempt:
            raise HTTPException(
                status_code=400,
                detail="Successful payment attempt not found",
            )

        # ------------------------------------------------------------
        # Refund amount belongs to THIS order
        # ------------------------------------------------------------
        refund_amount = float(order.total_amount)

        if refund_amount <= 0:
            raise HTTPException(
                status_code=400,
                detail="Invalid refund amount",
            )

        # ------------------------------------------------------------
        # Create refund attempt
        # ------------------------------------------------------------
        refund_attempt = (
            PaymentRepository.create_refund_attempt(
                db=db,
                intent_id=intent.intent_id,
                parent_attempt_id=payment_attempt.attempt_id,
                gateway=payment_attempt.gateway,
                refund_order_id=order.order_id,
                amount=refund_amount,
            )
        )

        merchant_refund_id = generate_merchant_refund_id()

        refund_attempt.merchant_refund_id = merchant_refund_id

        # ------------------------------------------------------------
        # Mark intent as refund initiated
        # ------------------------------------------------------------
        intent.status = (
            PaymentIntentStatus.REFUND_INITIATED.value
        )

        db.commit()

        db.refresh(refund_attempt)
        db.refresh(intent)

        logger.info(
            "REFUND CREATED | order=%s intent=%s refund_attempt=%s merchant_refund_id=%s amount=%s",
            order_id,
            intent.intent_id,
            refund_attempt.attempt_id,
            merchant_refund_id,
            refund_amount,
        )

        # ------------------------------------------------------------
        # Call PhonePe
        # ------------------------------------------------------------
        client = PhonePeClient()

        try:
            response = client.initiate_refund(
                merchant_refund_id=merchant_refund_id,
                # IMPORTANT: Refund only this order's amount.
                amount=int(round(refund_amount * 100)),
                original_merchant_order_id=(
                    payment_attempt.merchant_order_id
                ),
            )

        except (ReadTimeout, ConnectionError) as e:
            logger.warning(
                "PhonePe refund request outcome unknown | order=%s merchant_refund_id=%s error=%s",
                order_id,
                merchant_refund_id,
                str(e),
            )

            # DO NOT create another refund attempt.
            # PhonePe may have received the request.
            # Keep: refund_attempt = INITIATED, intent = REFUND_INITIATED
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
                "amount": refund_amount,
            }

        except PhonePeException as e:
            logger.exception(
                "PhonePe refund failed: %s",
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

            # Order remains REFUND_PENDING.
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
                    "Unable to initiate refund with payment gateway. Please try again."
                ),
            )

        # ------------------------------------------------------------
        # Save PhonePe refund response
        # ------------------------------------------------------------
        PaymentRepository.save_phonepe_refund(
            db=db,
            attempt=refund_attempt,
            merchant_refund_id=merchant_refund_id,
            gateway_refund_id=response["refund_id"],
            response=response,
        )
        

        # ------------------------------------------------------------
        # PhonePe immediately completed refund
        # ------------------------------------------------------------
        if response["state"] == "COMPLETED":
            refund_attempt.status = (
                PaymentAttemptStatus.SUCCESS.value
            )

            refund_attempt.completed_at = (
                datetime.now(timezone.utc)
            )

            # Mark THIS order refunded.
            OrderPaymentService.mark_refunded(
                db=db,
                order_id=order_id,
                provider_reference=merchant_refund_id,
                provider_transaction_id=None,
                commit=False,
            )

            # Do NOT automatically assume the entire intent is refunded when this is a multi-order intent.
            if PaymentRepository.are_all_orders_refunded(
                db,
                intent.intent_id,
            ):
                intent.status = (
                    PaymentIntentStatus.REFUNDED.value
                )
            else:
                # Other orders still belong to the same successful payment intent.
                intent.status = (
                    PaymentIntentStatus.SUCCEEDED.value
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

        # ------------------------------------------------------------
        # PhonePe accepted refund / processing
        # ------------------------------------------------------------
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
    # SYNC PAYMENT STATUS TO ALL LINKED ORDERS
    # ============================================================

    @staticmethod
    def _sync_payment_status_to_linked_orders(
        db: Session,
        intent: PaymentIntent,
        payment_status: PaymentStatus,
        provider_reference: str | None = None,
        provider_transaction_id: str | None = None,
    ):
        """
        Apply one payment result to every order belonging
        to the PaymentIntent.

        For a single-order payment:

            PaymentIntent
                └── Order

        For a multi-order payment:

            PaymentIntent
                ├── Order 1
                ├── Order 2
                └── Order 3

        The gateway transaction is still ONE payment.
        """

        order_ids = (
            PaymentRepository.get_order_ids_for_intent(
                db,
                intent.intent_id,
            )
        )

        # --------------------------------------------------------
        # Backward compatibility
        #
        # Existing intents created before the
        # payment_intent_orders table may not have a link row.
        # --------------------------------------------------------

        if not order_ids:
            order_ids = [intent.order_id]

        for linked_order_id in order_ids:

            OrderPaymentService.sync_payment_status(
                db=db,
                order_id=linked_order_id,
                payment_status=payment_status,
                provider_reference=provider_reference,
                provider_transaction_id=provider_transaction_id,
                commit=False,
            )

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

                PaymentService._sync_payment_status_to_linked_orders(
                    db=db,
                    intent=intent,
                    payment_status=PaymentStatus.FAILED,
                    provider_reference=(
                        payment_attempt.merchant_order_id
                    ),
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

            PaymentService._sync_payment_status_to_linked_orders(
                db=db,
                intent=intent,
                payment_status=PaymentStatus.FAILED,
                provider_reference=(
                    payment_attempt.merchant_order_id
                ),
                provider_transaction_id=transaction_id,
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

            PaymentService._sync_payment_status_to_linked_orders(
                db=db,
                intent=intent,
                payment_status=PaymentStatus.PAID,
                provider_reference=(
                    payment_attempt.merchant_order_id
                ),
                provider_transaction_id=transaction_id,

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

            PaymentService._sync_payment_status_to_linked_orders(
                db=db,
                intent=intent,
                payment_status=PaymentStatus.FAILED,
                provider_reference=(
                    payment_attempt.merchant_order_id
                ),
                provider_transaction_id=transaction_id,
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

        Refund amount is ALWAYS based on the specific order being refunded.
        For a multi-order payment intent, this prevents accidentally refunding the entire payment.
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

        if (
            order.payment_status
            != PaymentStatus.REFUND_PENDING.value
        ):
            raise HTTPException(
                status_code=400,
                detail="Order is not awaiting refund",
            )

        # ------------------------------------------------------------
        # Lock intent
        # ------------------------------------------------------------
        intent = PaymentRepository.get_intent_by_order_for_update(
            db,
            order_id,
        )

        if not intent:
            raise HTTPException(
                status_code=400,
                detail="Payment intent not found",
            )

        # ------------------------------------------------------------
        # Already refunded for this order
        # ------------------------------------------------------------
        existing_refund = (
            PaymentRepository.get_refund_attempt_for_order_for_update(
                db,
                intent.intent_id,
                order_id,
            )
        )

        if existing_refund:
            if existing_refund.status in (
                PaymentAttemptStatus.INITIATED.value,
                PaymentAttemptStatus.REDIRECTED.value,
            ):
                return {
                    "status": "already_initiated",
                    "order_id": order_id,
                    "refund_attempt": existing_refund,
                    "merchant_refund_id": (
                        existing_refund.merchant_refund_id
                    ),
                }

            if existing_refund.status == (
                PaymentAttemptStatus.SUCCESS.value
            ):
                return {
                    "status": "already_refunded",
                    "order_id": order_id,
                }

            # FAILED refund is retryable.

        # ------------------------------------------------------------
        # Validate intent state
        # ------------------------------------------------------------
        if intent.status not in (
            PaymentIntentStatus.SUCCEEDED.value,
            PaymentIntentStatus.REFUND_FAILED.value,
        ):
            raise HTTPException(
                status_code=400,
                detail="Payment is not eligible for refund",
            )

        # ------------------------------------------------------------
        # Find successful original payment
        # ------------------------------------------------------------
        payment_attempt = (
            PaymentRepository.get_latest_successful_payment_attempt(
                db,
                intent.intent_id,
            )
        )

        if not payment_attempt:
            raise HTTPException(
                status_code=400,
                detail="Successful payment attempt not found",
            )

        # ------------------------------------------------------------
        # Refund THIS order only
        # ------------------------------------------------------------
        refund_amount = float(order.total_amount)

        if refund_amount <= 0:
            raise HTTPException(
                status_code=400,
                detail="Invalid refund amount",
            )

        # ------------------------------------------------------------
        # Create refund attempt
        # ------------------------------------------------------------
        refund_attempt = (
            PaymentRepository.create_refund_attempt(
                db=db,
                intent_id=intent.intent_id,
                parent_attempt_id=payment_attempt.attempt_id,
                gateway=payment_attempt.gateway,
                refund_order_id=order.order_id,
                amount=refund_amount,
            )
        )

        merchant_refund_id = generate_merchant_refund_id()

        refund_attempt.merchant_refund_id = merchant_refund_id

        intent.status = (
            PaymentIntentStatus.REFUND_INITIATED.value
        )

        db.commit()

        db.refresh(refund_attempt)
        db.refresh(intent)

        logger.info(
            "REFUND INITIATED | order=%s intent=%s attempt=%s merchant_refund_id=%s amount=%s",
            order_id,
            intent.intent_id,
            refund_attempt.attempt_id,
            merchant_refund_id,
            refund_amount,
        )

        # ------------------------------------------------------------
        # PhonePe
        # ------------------------------------------------------------
        client = PhonePeClient()

        try:
            response = client.initiate_refund(
                merchant_refund_id=merchant_refund_id,
                amount=int(round(refund_amount * 100)),
                original_merchant_order_id=(
                    payment_attempt.merchant_order_id
                ),
            )

        except (ReadTimeout, ConnectionError) as e:
            logger.warning(
                "PhonePe refund request outcome unknown | order=%s merchant_refund_id=%s error=%s",
                order_id,
                merchant_refund_id,
                str(e),
            )

            # DO NOT retry by creating another refund.
            # The processor will query the same merchant_refund_id.
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
                "amount": refund_amount,
            }

        except PhonePeException as e:
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

            # Keep order REFUND_PENDING.
            OrderPaymentService.mark_refund_failed(
                db=db,
                order_id=order_id,
                provider_reference=merchant_refund_id,
                commit=False,
            )

            db.commit()

            raise

        # ------------------------------------------------------------
        # Save gateway response
        # ------------------------------------------------------------
        PaymentRepository.save_phonepe_refund(
            db=db,
            attempt=refund_attempt,
            merchant_refund_id=merchant_refund_id,
            gateway_refund_id=response["refund_id"],
            response=response,
        )

        # ------------------------------------------------------------
        # Immediate completion
        # ------------------------------------------------------------
        if response["state"] == "COMPLETED":
            refund_attempt.status = (
                PaymentAttemptStatus.SUCCESS.value
            )

            refund_attempt.completed_at = (
                datetime.now(timezone.utc)
            )

            OrderPaymentService.mark_refunded(
                db=db,
                order_id=order_id,
                provider_reference=merchant_refund_id,
                provider_transaction_id=None,
                commit=False,
            )

            if PaymentRepository.are_all_orders_refunded(
                db,
                intent.intent_id,
            ):
                intent.status = (
                    PaymentIntentStatus.REFUNDED.value
                )
            else:
                intent.status = (
                    PaymentIntentStatus.SUCCEEDED.value
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

        # ------------------------------------------------------------
        # Processing
        # ------------------------------------------------------------
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

        Important:
        A PaymentIntent may contain multiple orders.
        Therefore the refund belongs to:
            RefundAttempt.refund_order_id
        and NOT necessarily:
            PaymentIntent.order_id

        Synchronization flow:
            PhonePe
                ↓
            Refund PaymentAttempt
                ↓
            Specific Order
                ↓
            OrderPaymentService
                ↓
            Order.payment_status

        PaymentIntent becomes REFUNDED only when all linked orders have been refunded.
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
        # 2. FIND PAYMENT INTENT
        # ============================================================
        intent = PaymentRepository.get_intent_by_order(
            db,
            order_id,
        )

        if not intent:
            raise HTTPException(
                status_code=404,
                detail="Payment intent not found",
            )

        # ============================================================
        # 3. FIND REFUND ATTEMPT FOR THIS ORDER
        # ============================================================
        refund_attempt = (
            PaymentRepository.get_refund_attempt_for_order_for_update(
                db=db,
                intent_id=intent.intent_id,
                order_id=order_id,
            )
        )

        if not refund_attempt:
            raise HTTPException(
                status_code=404,
                detail="Refund attempt not found for order",
            )

        # ============================================================
        # 4. VERIFY REFUND ATTEMPT BELONGS TO THIS ORDER
        # ============================================================
        if refund_attempt.refund_order_id != order_id:
            raise HTTPException(
                status_code=400,
                detail="Refund attempt does not belong to order",
            )

        # ============================================================
        # 5. ALREADY COMPLETED
        # ============================================================
        if (
            refund_attempt.status
            == PaymentAttemptStatus.SUCCESS.value
        ):
            return {
                "order_id": order_id,
                "intent_id": intent.intent_id,
                "refund_attempt_id": refund_attempt.attempt_id,
                "status": "already_refunded",
                "payment_status": order.payment_status,
                "intent_status": intent.status,
            }

        # ============================================================
        # 6. REFUND ID REQUIRED
        # ============================================================
        if not refund_attempt.merchant_refund_id:
            raise HTTPException(
                status_code=400,
                detail="Merchant refund ID not found",
            )

        # ============================================================
        # 7. INTENT MUST BE IN REFUND FLOW
        # ============================================================
        if intent.status not in (
            PaymentIntentStatus.REFUND_INITIATED.value,
            PaymentIntentStatus.REFUND_FAILED.value,
        ):
            raise HTTPException(
                status_code=400,
                detail="Refund is not currently active",
            )

        # ============================================================
        # 8. FETCH PHONEPE REFUND STATUS
        # ============================================================
        client = PhonePeClient()

        try:
            status = client.get_refund_status(
                merchant_refund_id=(
                    refund_attempt.merchant_refund_id
                ),
            )

        except (ReadTimeout, ConnectionError):
            logger.warning(
                "PhonePe refund status timed out | order=%s refund_attempt=%s",
                order_id,
                refund_attempt.attempt_id,
            )

            # Do not change any state.
            # We don't know the gateway result yet.
            # Processor/webhook can retry.
            return {
                "order_id": order_id,
                "intent_id": intent.intent_id,
                "refund_attempt_id": refund_attempt.attempt_id,
                "status": "processing",
                "payment_status": order.payment_status,
                "intent_status": intent.status,
            }

        except PhonePeException as e:
            logger.exception(
                "PhonePe refund status failed | order=%s error=%s",
                order_id,
                getattr(e, "message", str(e)),
            )

            raise HTTPException(
                status_code=502,
                detail="Unable to fetch refund status.",
            )

        # ============================================================
        # 9. SAVE RAW PHONEPE RESPONSE
        # ============================================================
        PaymentRepository.save_refund_status(
            db=db,
            attempt=refund_attempt,
            response=status,
        )

        gateway_state = status.get("state")

        logger.info(
            "REFUND STATUS | order=%s intent=%s refund_attempt=%s state=%s",
            order_id,
            intent.intent_id,
            refund_attempt.attempt_id,
            gateway_state,
        )

        # ============================================================
        # 10. EXTRACT REFUND TRANSACTION
        # ============================================================
        payment_details = status.get("payment_details") or []
        refund_transaction_id = None

        if payment_details:
            latest_detail = payment_details[-1]

            if latest_detail.get("transaction_id"):
                refund_transaction_id = latest_detail[
                    "transaction_id"
                ]
                refund_attempt.gateway_transaction_id = (
                    refund_transaction_id
                )

            # Some PhonePe responses expose the actual refund state inside payment_details.
            if latest_detail.get("state"):
                gateway_state = latest_detail["state"]

        # ============================================================
        # 11. VERIFY REFUND AMOUNT
        # ============================================================
        gateway_amount = status.get("amount")
        expected_amount = int(
            round(float(refund_attempt.amount) * 100)
        )

        if gateway_amount is not None:
            if int(gateway_amount) != expected_amount:
                logger.error(
                    "Refund amount mismatch | order=%s expected=%s gateway=%s",
                    order_id,
                    expected_amount,
                    gateway_amount,
                )

                refund_attempt.status = (
                    PaymentAttemptStatus.FAILED.value
                )

                refund_attempt.response_payload = {
                    **(
                        refund_attempt.response_payload
                        or {}
                    ),
                    "validation_error": (
                        "Refund amount mismatch"
                    ),
                    "expected_amount": expected_amount,
                    "gateway_amount": gateway_amount,
                }

                intent.status = (
                    PaymentIntentStatus.REFUND_FAILED.value
                )

                # IMPORTANT: Order remains REFUND_PENDING. We must NOT mark it refunded.
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

                raise HTTPException(
                    status_code=400,
                    detail="Refund amount verification failed",
                )

        # ============================================================
        # 12. REFUND COMPLETED
        # ============================================================
        if gateway_state == "COMPLETED":
            refund_attempt.status = (
                PaymentAttemptStatus.SUCCESS.value
            )

            refund_attempt.completed_at = datetime.now(
                timezone.utc
            )

            # Mark ONLY this order as refunded.
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

            # Check whether every order under this intent has now been refunded.
            all_refunded = (
                PaymentRepository.are_all_orders_refunded(
                    db=db,
                    intent_id=intent.intent_id,
                )
            )

            if all_refunded:
                intent.status = (
                    PaymentIntentStatus.REFUNDED.value
                )
            else:
                # Some orders under this payment intent are still paid/active.
                intent.status = (
                    PaymentIntentStatus.SUCCEEDED.value
                )

            db.commit()

            db.refresh(order)
            db.refresh(intent)
            db.refresh(refund_attempt)

            logger.info(
                "REFUND COMPLETED | order=%s refund_attempt=%s all_orders_refunded=%s",
                order_id,
                refund_attempt.attempt_id,
                all_refunded,
            )

            return {
                "order_id": order_id,
                "intent_id": intent.intent_id,
                "refund_attempt_id": refund_attempt.attempt_id,
                "status": "refunded",
                "payment_status": order.payment_status,
                "intent_status": intent.status,
                "refund_transaction_id": (
                    refund_transaction_id
                ),
            }

        # ============================================================
        # 13. REFUND FAILED
        # ============================================================
        if gateway_state == "FAILED":
            refund_attempt.status = (
                PaymentAttemptStatus.FAILED.value
            )

            refund_attempt.completed_at = datetime.now(
                timezone.utc
            )

            intent.status = (
                PaymentIntentStatus.REFUND_FAILED.value
            )

            # IMPORTANT: Order remains REFUND_PENDING. The refund processor can retry.
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
            db.refresh(refund_attempt)
            db.refresh(order)

            logger.warning(
                "REFUND FAILED | order=%s refund_attempt=%s",
                order_id,
                refund_attempt.attempt_id,
            )

            return {
                "order_id": order_id,
                "intent_id": intent.intent_id,
                "refund_attempt_id": refund_attempt.attempt_id,
                "status": "failed",
                "payment_status": order.payment_status,
                "intent_status": intent.status,
                "refund_transaction_id": (
                    refund_transaction_id
                ),
            }

        # ============================================================
        # 14. STILL PROCESSING
        # ============================================================
        db.commit()

        db.refresh(intent)
        db.refresh(refund_attempt)

        return {
            "order_id": order_id,
            "intent_id": intent.intent_id,
            "refund_attempt_id": refund_attempt.attempt_id,
            "status": "processing",
            "payment_status": order.payment_status,
            "intent_status": intent.status,
            "refund_transaction_id": refund_transaction_id,
        }