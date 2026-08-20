from sqlalchemy.orm import Session

from app.modules.payments.models import (
    PaymentIntent,
    PaymentAttempt,
)

from app.modules.payments.constants import (
    PaymentIntentStatus,
    PaymentAttemptStatus,
)


class PaymentRepository:

    # ============================================================
    # PAYMENT INTENT
    # ============================================================

    @staticmethod
    def get_intent_by_order(
        db: Session,
        order_id: int,
    ):
        return (
            db.query(PaymentIntent)
            .filter(
                PaymentIntent.order_id == order_id
            )
            .first()
        )


    @staticmethod
    def get_intent_by_order_for_update(
        db: Session,
        order_id: int,
    ):
        """
        Fetch the payment intent while locking its row.

        Used during payment initiation to prevent two
        simultaneous requests from creating multiple
        active payment attempts for the same order.

        PostgreSQL SELECT ... FOR UPDATE ensures that
        concurrent requests serialize on this intent row.
        """

        return (
            db.query(PaymentIntent)
            .filter(
                PaymentIntent.order_id == order_id
            )
            .with_for_update()
            .first()
        )

    @staticmethod
    def create_intent(
        db: Session,
        order_id: int,
        amount: float,
    ):
        intent = PaymentIntent(
            order_id=order_id,
            amount=amount,
            status=PaymentIntentStatus.CREATED.value,
        )

        db.add(intent)
        db.flush()

        return intent

    # ============================================================
    # PAYMENT ATTEMPTS
    # ============================================================

    @staticmethod
    def create_attempt(
        db: Session,
        intent_id: int,
        gateway: str,
        merchant_order_id: str,
    ):
        """
        Create a normal/original payment attempt.

        parent_payment_id MUST remain NULL.

        Refund attempts are created separately using
        create_refund_attempt().
        """

        attempt_number = (
            PaymentRepository.get_next_attempt_number(
                db,
                intent_id,
            )
        )

        attempt = PaymentAttempt(
            intent_id=intent_id,
            gateway=gateway,
            merchant_order_id=merchant_order_id,
            attempt_number=attempt_number,
            status=PaymentAttemptStatus.INITIATED.value,
            parent_payment_id=None,
        )

        db.add(attempt)
        db.flush()

        return attempt

    @staticmethod
    def get_attempts_for_intent(
        db: Session,
        intent_id: int,
    ):
        """
        Return ALL attempts belonging to an intent.

        This includes:

            - payment attempts
            - refund attempts

        Use the specialized methods below when you need
        only payment or refund attempts.
        """

        return (
            db.query(PaymentAttempt)
            .filter(
                PaymentAttempt.intent_id == intent_id
            )
            .order_by(
                PaymentAttempt.attempt_number.asc()
            )
            .all()
        )

    @staticmethod
    def get_payment_attempts_for_intent(
        db: Session,
        intent_id: int,
    ):
        """
        Return ONLY original payment attempts.

        Refund attempts have parent_payment_id set,
        therefore they are excluded.
        """

        return (
            db.query(PaymentAttempt)
            .filter(
                PaymentAttempt.intent_id == intent_id,
                PaymentAttempt.parent_payment_id.is_(None),
            )
            .order_by(
                PaymentAttempt.attempt_number.asc()
            )
            .all()
        )

    @staticmethod
    def get_refund_attempts_for_intent(
        db: Session,
        intent_id: int,
    ):
        """
        Return ONLY refund attempts.
        """

        return (
            db.query(PaymentAttempt)
            .filter(
                PaymentAttempt.intent_id == intent_id,
                PaymentAttempt.parent_payment_id.isnot(None),
            )
            .order_by(
                PaymentAttempt.attempt_number.asc()
            )
            .all()
        )

    # ============================================================
    # ATTEMPT LOOKUPS
    # ============================================================

    @staticmethod
    def get_attempt_by_merchant_order_id(
        db: Session,
        merchant_order_id: str,
    ):
        """
        Find an original PhonePe payment attempt using
        OFFO merchant order ID.

        Refund attempts are deliberately excluded.
        """

        return (
            db.query(PaymentAttempt)
            .filter(
                PaymentAttempt.merchant_order_id
                == merchant_order_id,
                PaymentAttempt.parent_payment_id.is_(None),
            )
            .first()
        )

    @staticmethod
    def get_latest_attempt(
        db: Session,
        intent_id: int,
    ):
        """
        Return the latest ORIGINAL PAYMENT attempt.

        IMPORTANT:

        This does NOT return refund attempts.
        """

        return (
            db.query(PaymentAttempt)
            .filter(
                PaymentAttempt.intent_id == intent_id,
                PaymentAttempt.parent_payment_id.is_(None),
            )
            .order_by(
                PaymentAttempt.attempt_number.desc()
            )
            .first()
        )

    @staticmethod
    def get_latest_payment_attempt(
        db: Session,
        intent_id: int,
    ):
        """
        Explicit alias for callers that need the latest
        original payment attempt.
        """

        return PaymentRepository.get_latest_attempt(
            db,
            intent_id,
        )

    @staticmethod
    def get_latest_successful_payment_attempt(
        db: Session,
        intent_id: int,
    ):
        """
        Return the latest successful ORIGINAL payment.

        Used by refund flow.
        """

        return (
            db.query(PaymentAttempt)
            .filter(
                PaymentAttempt.intent_id == intent_id,
                PaymentAttempt.parent_payment_id.is_(None),
                PaymentAttempt.status
                == PaymentAttemptStatus.SUCCESS.value,
                PaymentAttempt.merchant_order_id.isnot(None),
            )
            .order_by(
                PaymentAttempt.attempt_number.desc()
            )
            .first()
        )

    @staticmethod
    def get_active_attempt(
        db: Session,
        intent_id: int,
    ):
        """
        Return the latest active ORIGINAL payment attempt.

        Active payment states:

            INITIATED
            REDIRECTED

        Refund attempts are excluded.
        """

        return (
            db.query(PaymentAttempt)
            .filter(
                PaymentAttempt.intent_id == intent_id,

                # IMPORTANT:
                # Only original payment attempts.
                PaymentAttempt.parent_payment_id.is_(None),

                PaymentAttempt.status.in_([
                    PaymentAttemptStatus.INITIATED.value,
                    PaymentAttemptStatus.REDIRECTED.value,
                ]),
            )
            .order_by(
                PaymentAttempt.attempt_number.desc()
            )
            .first()
        )

    # ============================================================
    # ATTEMPT NUMBER
    # ============================================================

    @staticmethod
    def get_next_attempt_number(
        db: Session,
        intent_id: int,
    ):
        """
        Get the next attempt number.

        Both payment and refund attempts share the same
        attempt_number sequence for an intent.
        """

        latest = (
            db.query(PaymentAttempt)
            .filter(
                PaymentAttempt.intent_id == intent_id
            )
            .order_by(
                PaymentAttempt.attempt_number.desc()
            )
            .first()
        )

        if not latest:
            return 1

        return latest.attempt_number + 1

    # ============================================================
    # PAYMENT ATTEMPT STATE
    # ============================================================

    @staticmethod
    def mark_attempt_redirected(
        db: Session,
        attempt: PaymentAttempt,
        payload: dict,
    ):
        attempt.status = (
            PaymentAttemptStatus.REDIRECTED.value
        )

        attempt.response_payload = payload

        db.commit()
        db.refresh(attempt)

        return attempt

    @staticmethod
    def mark_attempt_success(
        db: Session,
        attempt: PaymentAttempt,
        payload: dict,
    ):
        attempt.status = (
            PaymentAttemptStatus.SUCCESS.value
        )

        attempt.response_payload = payload

        db.commit()
        db.refresh(attempt)

        return attempt

    @staticmethod
    def mark_attempt_failed(
        db: Session,
        attempt: PaymentAttempt,
        payload: dict,
    ):
        attempt.status = (
            PaymentAttemptStatus.FAILED.value
        )

        attempt.response_payload = payload

        db.commit()
        db.refresh(attempt)

        return attempt

    @staticmethod
    def mark_attempt_cancelled(
        db: Session,
        attempt: PaymentAttempt,
    ):
        attempt.status = (
            PaymentAttemptStatus.CANCELLED.value
        )

        db.commit()
        db.refresh(attempt)

        return attempt

    # ============================================================
    # PHONEPE PAYMENT
    # ============================================================

    @staticmethod
    def save_phonepe_order(
        db: Session,
        attempt: PaymentAttempt,
        phonepe_order_id: str,
        response: dict,
    ):
        """
        Save PhonePe's generated order ID and checkout response.

        This method is ONLY for normal payment attempts.
        """

        attempt.phonepe_order_id = phonepe_order_id

        attempt.response_payload = response

        attempt.status = (
            PaymentAttemptStatus.REDIRECTED.value
        )

        db.commit()
        db.refresh(attempt)

        return attempt

    # ============================================================
    # REFUND ATTEMPTS
    # ============================================================

    @staticmethod
    def create_refund_attempt(
        db: Session,
        intent_id: int,
        parent_attempt_id: int,
        gateway: str,
    ):
        """
        Create a refund attempt linked to the original
        successful payment attempt.
        """

        attempt_number = (
            PaymentRepository.get_next_attempt_number(
                db,
                intent_id,
            )
        )

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
    def get_refund_attempt(
        db: Session,
        intent_id: int,
    ):
        """
        Return the latest refund attempt.
        """

        return (
            db.query(PaymentAttempt)
            .filter(
                PaymentAttempt.intent_id == intent_id,
                PaymentAttempt.parent_payment_id.isnot(None),
            )
            .order_by(
                PaymentAttempt.attempt_number.desc()
            )
            .first()
        )


    @staticmethod
    def get_refund_attempt_for_update(
        db: Session,
        intent_id: int,
    ):
        """
        Return the latest refund attempt while locking it.

        Used when a refund operation needs to safely inspect
        and modify an existing refund attempt.
        """

        return (
            db.query(PaymentAttempt)
            .filter(
                PaymentAttempt.intent_id == intent_id,
                PaymentAttempt.parent_payment_id.isnot(None),
            )
            .order_by(
                PaymentAttempt.attempt_number.desc()
            )
            .with_for_update()
            .first()
        )

    # ============================================================
    # REFUND ATTEMPT HELPERS
    # ============================================================

    @staticmethod
    def get_latest_refund_attempt(
        db: Session,
        intent_id: int,
    ):
        """
        Return the latest refund attempt for an intent.
        """

        return (
            db.query(PaymentAttempt)
            .filter(
                PaymentAttempt.intent_id == intent_id,
                PaymentAttempt.parent_payment_id.isnot(None),
            )
            .order_by(
                PaymentAttempt.attempt_number.desc()
            )
            .first()
        )

    @staticmethod
    def get_active_refund_attempt(
        db: Session,
        intent_id: int,
    ):
        """
        Return an active refund attempt that is currently
        being processed.

        An active refund must NOT be duplicated.
        """

        return (
            db.query(PaymentAttempt)
            .filter(
                PaymentAttempt.intent_id == intent_id,
                PaymentAttempt.parent_payment_id.isnot(None),
                PaymentAttempt.status.in_([
                    PaymentAttemptStatus.INITIATED.value,
                    PaymentAttemptStatus.REDIRECTED.value,
                ]),
            )
            .order_by(
                PaymentAttempt.attempt_number.desc()
            )
            .first()
        )

    @staticmethod
    def get_failed_refund_attempt(
        db: Session,
        intent_id: int,
    ):
        """
        Return the latest failed refund attempt.
        """

        return (
            db.query(PaymentAttempt)
            .filter(
                PaymentAttempt.intent_id == intent_id,
                PaymentAttempt.parent_payment_id.isnot(None),
                PaymentAttempt.status
                == PaymentAttemptStatus.FAILED.value,
            )
            .order_by(
                PaymentAttempt.attempt_number.desc()
            )
            .first()
        )



    # ============================================================
    # PHONEPE REFUND
    # ============================================================

    @staticmethod
    def save_phonepe_refund(
        db: Session,
        attempt: PaymentAttempt,
        merchant_refund_id: str,
        gateway_refund_id: str,
        response: dict,
    ):
        """
        Save PhonePe refund response.

        Existing schema does not have a dedicated
        phonepe_refund_id column.

        Therefore:

            merchant_order_id = OFFO merchant refund ID
            phonepe_order_id  = PhonePe refund ID

        This preserves the current schema while keeping
        the two identifiers distinguishable.
        """

        attempt.merchant_refund_id = merchant_refund_id
        attempt.gateway_refund_id = gateway_refund_id

        attempt.response_payload = response

        attempt.status = (
            PaymentAttemptStatus.INITIATED.value
        )

        db.commit()
        db.refresh(attempt)

        return attempt

    @staticmethod
    def save_refund_status(
        db: Session,
        attempt: PaymentAttempt,
        response: dict,
    ):
        """
        Save the latest PhonePe refund status.
        """

        attempt.response_payload = response

        db.commit()
        db.refresh(attempt)

        return attempt

    # ============================================================
    # REFUND IDENTIFIERS
    # ============================================================

    @staticmethod
    def get_refund_attempt_by_merchant_refund_id(
        db: Session,
        merchant_refund_id: str,
    ):
        """
        Find a refund attempt using OFFO's merchant refund ID.
        """

        return (
            db.query(PaymentAttempt)
            .filter(
                PaymentAttempt.merchant_refund_id
                == merchant_refund_id
            )
            .first()
        )

    # ============================================================
    # TRANSACTION HELPERS
    # ============================================================

    @staticmethod
    def save_attempt_response(
        db: Session,
        attempt: PaymentAttempt,
        response: dict,
    ):
        """
        Save gateway response without changing the attempt state.

        Useful when the service needs to control the state
        transition itself.
        """

        attempt.response_payload = response

        db.flush()

        return attempt