from sqlalchemy.orm import Session
from fastapi import HTTPException

from app.modules.orders.repository import OrderRepository
from app.modules.payments.repository import PaymentRepository
from app.modules.payments.constants import (
    PaymentGateway,
    PaymentIntentStatus,
    PaymentAttemptStatus
)
from app.modules.payments.gateways.phonepe.client import PhonePeClient


class PaymentService:

    @staticmethod
    def initiate_payment(db: Session, user_id: int, order_id: int, gateway: str):
        order = OrderRepository.get_order(db, order_id)

        if not order or order.user_id != user_id:
            raise HTTPException(404, "Order not found")

        if order.payment_status == "PAID":
            raise HTTPException(400, "Order already paid")

        intent = PaymentRepository.get_intent_by_order(db, order_id)

        if not intent:
            intent = PaymentRepository.create_intent(
                db,
                order_id=order.order_id,
                amount=order.total_amount,
            )

        attempt = PaymentRepository.create_attempt(
            db,
            intent_id=intent.intent_id,
            gateway=gateway,
        )

        intent.status = PaymentIntentStatus.PROCESSING.value
        db.commit()
        db.refresh(intent)

        print(
            f"💳 PAYMENT INITIATED | "
            f"order={order_id} intent={intent.intent_id} attempt={attempt.attempt_id}"
        )

        if gateway == PaymentGateway.PHONEPE:
            client = PhonePeClient()
            response = client.initiate_payment(
                merchant_txn_id=str(attempt.attempt_id),
                amount=int(intent.amount * 100),  # INR → paise
                user_id=user_id,
            )

            PaymentRepository.mark_attempt_redirected(db, attempt, response)

        return intent
    

    
    
    @staticmethod
    def initiate_refund(db: Session, order_id: int, user_id: int):
      order = OrderRepository.get_order(db, order_id)

      if not order or order.user_id != user_id:
        raise HTTPException(404, "Order not found")

      if order.payment_status != "PAID":
        raise HTTPException(400, "Order not paid")

      intent = PaymentRepository.get_intent_by_order(db, order_id)

      if not intent or intent.status != PaymentIntentStatus.SUCCEEDED:
        raise HTTPException(400, "Payment not eligible for refund")

      payment_attempt = next(
        (a for a in intent.attempts if a.status == PaymentAttemptStatus.SUCCESS),
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

      intent.status = PaymentIntentStatus.REFUND_INITIATED
      db.commit()

      print(
        f"🔄 REFUND INITIATED | "
        f"order={order_id} refund_attempt={refund_attempt.attempt_id}"
      )

      return refund_attempt

