from sqlalchemy.orm import Session
from fastapi import HTTPException
from datetime import datetime, timezone
import logging
from app.modules.orders.repository import OrderRepository
from app.modules.payments.repository import PaymentRepository
from app.modules.payments.constants import (
    PaymentGateway,
    PaymentIntentStatus,
    PaymentAttemptStatus
)
from app.modules.payments.gateways.phonepe.client import PhonePeClient
from app.modules.payments.utils import generate_merchant_order_id
from phonepe.sdk.pg.common.exceptions import PhonePeException

logger = logging.getLogger(__name__)
class PaymentService:

    @staticmethod
    def initiate_payment(db: Session, user_id: int, order_id: int, gateway: str):
        order = OrderRepository.get_order(db, order_id)

        if not order or order.user_id != user_id:
            raise HTTPException(404, "Order not found")

        if order.payment_status in [ "PAID" , "REFUNDED"]:
            raise HTTPException(400, "Order already paid")

        intent = PaymentRepository.get_intent_by_order(db, order_id)

        if not intent:
            intent = PaymentRepository.create_intent(
                db,
                order_id=order.order_id,
                amount=order.total_amount,
            )

        active_attempt = PaymentRepository.get_active_attempt(
            db,
            intent.intent_id,
        )

        if (
            active_attempt
            and active_attempt.response_payload
        ):
            logger.info(
            f"♻️ Reusing active payment attempt "
            f"{active_attempt.attempt_id}"
        )

            return {
                "intent": intent,
                "checkout_url": active_attempt.response_payload.get(
                    "redirect_url"
                ),
            }

        merchant_order_id = generate_merchant_order_id()

        attempt = PaymentRepository.create_attempt(
            db,
            intent_id=intent.intent_id,
            gateway=gateway,
            merchant_order_id=merchant_order_id,
        )

        intent.status = PaymentIntentStatus.PROCESSING.value
        db.commit()
        db.refresh(intent)

        logger.info(
            f"💳 PAYMENT INITIATED | "
            f"order={order_id} intent={intent.intent_id} attempt={attempt.attempt_id}"
        )

        if gateway == PaymentGateway.PHONEPE:
            client = PhonePeClient()
            try:
                response = client.initiate_payment(
                    merchant_order_id=merchant_order_id,
                    order_id=order.order_id,
                    amount=int(intent.amount * 100),  # INR → paise
                    user_id=user_id,
                )
                
            except PhonePeException as e:
                logger.exception(
                    "Phonepe initiate payment failed: %s", str(e),
                )

                db.rollback()

                attempt.status = PaymentAttemptStatus.FAILED.value

                attempt.response_payload = {
                    "error": e.message,
                    "http_status": e.http_status_code,
                }

                intent.status = PaymentIntentStatus.FAILED.value

                order.payment_status = "FAILED"

                db.commit()

                raise HTTPException(
                    status_code=502,
                    detail="Unable to connect to payment gateway. Please try again."
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


    @staticmethod
    def retry_payment(
        db: Session,
        user_id: int,
        order_id: int,
    ):
        """
        Retry payment for an existing order.

        Creates a new PaymentAttempt under the
        existing PaymentIntent and generates a new
        PhonePe checkout URL.
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
            "PAID",
            "REFUNDED",
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
            f"🔁 PAYMENT RETRY | "
            f"order={order.order_id} "
            f"intent={intent.intent_id} "
            f"attempt={attempt.attempt_id}"
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
                "Phonepe retry payment failed: %s", str(e),
            )

            db.rollback()

            attempt.status = PaymentAttemptStatus.FAILED.value

            attempt.response_payload = {
                "error": e.message,
                "http_status": e.http_status_code,
            }

            intent.status = PaymentIntentStatus.FAILED.value

            order.payment_status = "FAILED"

            db.commit()
        
            raise HTTPException(
                status_code=502,
                detail="Unable to connect to payment gateway. Please try again."
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


    
    @staticmethod
    def initiate_refund(db: Session, order_id: int, user_id: int):
      order = OrderRepository.get_order(db, order_id)

      if not order or order.user_id != user_id:
        raise HTTPException(404, "Order not found")

      if order.payment_status != "PAID":
        raise HTTPException(400, "Order not paid")

      intent = PaymentRepository.get_intent_by_order(db, order_id)

      if intent and intent.status in [
         PaymentIntentStatus.REFUND_INITIATED.value, PaymentIntentStatus.REFUNDED.value,
      ]:
         raise HTTPException(400, "Refund already initiated")

      if not intent or intent.status != PaymentIntentStatus.SUCCEEDED.value:
        raise HTTPException(400, "Payment not eligible for refund")

      payment_attempt = next(
        (a for a in intent.attempts if a.status == PaymentAttemptStatus.SUCCESS.value and a.parent_payment_id is None),
        None,
      )

      if not payment_attempt:
        raise HTTPException(400, "No successful payment found")

      refund_attempt = PaymentRepository.create_refund_attempt(
        db=db,
        intent_id=intent.intent_id,
        parent_attempt_id=payment_attempt.attempt_id,
        gateway=payment_attempt.gateway,
      )

      intent.status = PaymentIntentStatus.REFUND_INITIATED.value
      db.commit()

      logger.info(
        f"🔄 REFUND INITIATED | "
        f"order={order_id} refund_attempt={refund_attempt.attempt_id}"
      )

      return refund_attempt


    @staticmethod
    def sync_payment_status(
        db: Session,
        order_id: int,
    ):

        intent = PaymentRepository.get_intent_by_order(
            db,
            order_id,
        )

        if not intent:
            raise HTTPException(
                404,
                "Payment not found",
            )

        if intent.status in (
            PaymentIntentStatus.SUCCEEDED.value,
            PaymentIntentStatus.FAILED.value,
            PaymentIntentStatus.REFUNDED.value,
        ):
            return intent

        attempts = PaymentRepository.get_attempts_for_intent(
            db,
            intent.intent_id,
        )

        if not attempts:
            return intent

        payment_attempt = attempts[-1]

        client = PhonePeClient()

        try:
            status = client.get_order_status(
                payment_attempt.merchant_order_id,
            )

        except PhonePeException as e:
            logger.exception(
                "Phonepe sync failed: %s", e.message,
            )
        
            raise HTTPException(
                status_code=502,
                detail="Unable to fetch payment status."
            )

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
            and status["state"] == "PENDING"
        ):
            payment_attempt.status = (
                PaymentAttemptStatus.EXPIRED.value
            )

            intent.status = (
                PaymentIntentStatus.FAILED.value
            )

            order = OrderRepository.get_order(
               db,
               order_id,
            )

            order.payment_status = "FAILED"

            db.commit()
   
            db.refresh(intent)

            logger.info(
                f"⏰ PAYMENT EXPIRED | "
                f"order={order.order_id}"
            )

            return intent   

        

        payment_attempt.phonepe_order_id = status["phonepe_order_id"]

        payment_attempt.response_payload = status

        if status["payment_details"]:
          payment_attempt.gateway_transaction_id = (
          status["payment_details"][-1]["transaction_id"]
        )

        if status["state"] == "COMPLETED":

          payment_attempt.status = (
              PaymentAttemptStatus.SUCCESS.value
          )

          payment_attempt.gateway_transaction_id = (
            status["payment_details"][-1]["transaction_id"]
            if status["payment_details"]
            else None
          )

          intent.status = (
            PaymentIntentStatus.SUCCEEDED.value
          )

          order = OrderRepository.get_order(
            db,
            order_id,
          )

          order.payment_status = "PAID"

          db.commit()

          db.refresh(intent)

          return intent

        if status["state"] == "FAILED":

          payment_attempt.status = (
            PaymentAttemptStatus.FAILED.value
          )

          intent.status = (
            PaymentIntentStatus.FAILED.value
          )

          order = OrderRepository.get_order(
              db,
              order_id,
          )

          order.payment_status= "FAILED"

          db.commit()

          db.refresh(intent)

          return intent

        return intent


    @staticmethod
    def get_payment_status(
        db: Session,
        user_id: int,
        order_id: int,
    ):
        """
        Returns latest payment status.

        If payment is still PROCESSING,
        automatically sync with PhonePe first.
        """

        order = OrderRepository.get_order(
            db,
            order_id,
        )

        if not order:
            raise HTTPException(
                404,
                "Order not found",
            )

        if order.user_id != user_id:
            raise HTTPException(
                403,
                "Unauthorized",
            )

        intent = PaymentRepository.get_intent_by_order(
            db,
            order_id,
        )

        if not intent:
            raise HTTPException(
                404,
                "Payment not found",
            )

        if intent.status == PaymentIntentStatus.PROCESSING.value:
            PaymentService.sync_payment_status(
                db=db,
                order_id=order_id,
            )

            db.refresh(intent)

        attempt = PaymentRepository.get_latest_attempt(
            db,
            intent.intent_id,
        )

        redirect_url = None

        if (
           attempt
           and attempt.response_payload
        ):
           redirect_url = attempt.response_payload.get(
                "redirect_url"
              )

        return {
            "order_id": order.order_id,
            "payment_status": order.payment_status,
            "intent_status": intent.status,
            "attempt_status": (
                attempt.status if attempt else None
            ),
            "redirect_url": redirect_url,
            "transaction_id": (
                attempt.gateway_transaction_id
                if attempt
                else None
            ),
        }


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
            raise HTTPException(404, "Order not found")

        if order.user_id != user_id:
            raise HTTPException(403, "Unauthorized")

        intent = PaymentRepository.get_intent_by_order(
            db,
            order_id,
        )

        if not intent:
            raise HTTPException(404, "Payment not found")

        latest_attempt = PaymentRepository.get_latest_attempt(
            db,
            intent.intent_id,
        )

        if not latest_attempt:
            raise HTTPException(404, "Payment attempt not found")

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

        intent.status = PaymentIntentStatus.CANCELLED.value

        db.commit()

        return {
            "message": "Payment cancelled",
        }
      
