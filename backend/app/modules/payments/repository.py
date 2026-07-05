from sqlalchemy.orm import Session
from sqlalchemy import func

from app.modules.payments.models import PaymentIntent, PaymentAttempt
from app.modules.payments.constants import (
    PaymentIntentStatus,
    PaymentAttemptStatus,
)


class PaymentRepository:

    @staticmethod
    def get_intent_by_order(db: Session, order_id: int):
        return (
            db.query(PaymentIntent)
            .filter(PaymentIntent.order_id == order_id)
            .first()
        )

    @staticmethod
    def create_intent(db: Session, order_id: int, amount: float):
        intent = PaymentIntent(
            order_id=order_id,
            amount=amount,
            status=PaymentIntentStatus.CREATED.value,
        )
        db.add(intent)
        db.flush()
        return intent

    @staticmethod
    def create_attempt(db: Session, intent_id: int, gateway: str):
        attempt_number = (
            db.query(func.count(PaymentAttempt.attempt_id))
            .filter(PaymentAttempt.intent_id == intent_id)
            .scalar()
            or 0
        ) + 1

        attempt = PaymentAttempt(
            intent_id=intent_id,
            gateway=gateway,
            attempt_number=attempt_number,
            status=PaymentAttemptStatus.INITIATED.value,
        )
        db.add(attempt)
        db.flush()
        return attempt

    @staticmethod
    def mark_attempt_redirected(db: Session, attempt: PaymentAttempt, payload: dict):
        attempt.status = PaymentAttemptStatus.REDIRECTED.value
        attempt.response_payload = payload
        db.commit()

    @staticmethod
    def mark_attempt_success(db: Session, attempt: PaymentAttempt, payload: dict):
        attempt.status = PaymentAttemptStatus.SUCCESS.value
        attempt.response_payload = payload
        db.commit()

    @staticmethod
    def mark_attempt_failed(db: Session, attempt: PaymentAttempt, payload: dict):
        attempt.status = PaymentAttemptStatus.FAILED.value
        attempt.response_payload = payload
        db.commit()

    @staticmethod
    def create_refund_attempt(
      db: Session,
      intent_id: int,
      parent_attempt_id: int,
      gateway: str,
    ):
      attempt_number = (
        db.query(func.count(PaymentAttempt.attempt_id))
        .filter(PaymentAttempt.intent_id == intent_id)
        .scalar()
        or 0
      ) + 1

      refund = PaymentAttempt(
        intent_id=intent_id,
        gateway=gateway,
        attempt_number=attempt_number,
        status=PaymentAttemptStatus.INITIATED.value,
        parent_payment_id=parent_attempt_id,
      )

      db.add(refund)
      db.flush()
      return refund
    
    @staticmethod
    def get_attempts_for_intent(
        db: Session,
        intent_id: int,
    ):
        return (
            db.query(PaymentAttempt)
            .filter(
                PaymentAttempt.intent_id == intent_id
            )
            .order_by(
                PaymentAttempt.created_at.asc()
            )
            .all()
        )

