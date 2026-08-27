from sqlalchemy.orm import Session

from app.modules.payments.models import (
    PaymentIntent,
    PaymentIntentOrder,
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
        """
        Find the payment intent associated with an order.

        Supports:

        1. Legacy/single-order intents
           PaymentIntent.order_id = order_id

        2. Multi-order intents
           PaymentIntentOrder links the order to the intent.
        """

        intent = (
            db.query(PaymentIntent)
            .filter(
                PaymentIntent.order_id == order_id
            )
            .first()
        )

        if intent:
            return intent

        return PaymentRepository.get_intent_for_order(
            db=db,
            order_id=order_id,
        )

    @staticmethod
    def create_intent(
        db: Session,
        order_id: int,
        amount: float,
        platform_fee: float = 0,
        gst: float = 0,
        checkout_fee: float = 0,
    ):
        intent = PaymentIntent(
            order_id=order_id,
            amount=amount,
            platform_fee=platform_fee,
            gst=gst,
            checkout_fee=checkout_fee,
            status=PaymentIntentStatus.CREATED.value,
        )

        db.add(intent)
        db.flush()

        return intent

    # ============================================================
    # PAYMENT INTENT ↔ ORDERS
    # ============================================================

    @staticmethod
    def add_order_to_intent(
        db: Session,
        intent_id: int,
        order_id: int,
    ):
        """
        Associate one order with a payment intent.

        payment_intent_orders.order_id is UNIQUE, so an order
        cannot belong to multiple payment intents.
        """

        link = PaymentIntentOrder(
            intent_id=intent_id,
            order_id=order_id,
        )

        db.add(link)
        db.flush()

        return link

    @staticmethod
    def add_orders_to_intent(
        db: Session,
        intent_id: int,
        order_ids: list[int],
    ):
        """
        Associate multiple orders with one payment intent.
        """

        links = []

        for order_id in order_ids:
            link = PaymentIntentOrder(
                intent_id=intent_id,
                order_id=order_id,
            )

            db.add(link)
            links.append(link)

        db.flush()

        return links

    @staticmethod
    def get_orders_for_intent(
        db: Session,
        intent_id: int,
    ):
        """
        Return all order-link rows associated with a payment intent.
        """

        return (
            db.query(PaymentIntentOrder)
            .filter(
                PaymentIntentOrder.intent_id == intent_id
            )
            .order_by(
                PaymentIntentOrder.id.asc()
            )
            .all()
        )

    @staticmethod
    def get_order_ids_for_intent(
        db: Session,
        intent_id: int,
    ):
        """
        Return only order IDs associated with a payment intent.
        """

        rows = (
            db.query(PaymentIntentOrder.order_id)
            .filter(
                PaymentIntentOrder.intent_id == intent_id
            )
            .order_by(
                PaymentIntentOrder.id.asc()
            )
            .all()
        )

        return [
            row.order_id
            for row in rows
        ]

    @staticmethod
    def get_intent_for_order(
        db: Session,
        order_id: int,
    ):
        """
        Find the payment intent associated with an order
        through PaymentIntentOrder.
        """

        return (
            db.query(PaymentIntent)
            .join(
                PaymentIntentOrder,
                PaymentIntentOrder.intent_id
                == PaymentIntent.intent_id,
            )
            .filter(
                PaymentIntentOrder.order_id == order_id
            )
            .first()
        )

    @staticmethod
    def get_intent_for_order_for_update(
        db: Session,
        order_id: int,
    ):
        """
        Find and lock the payment intent associated with
        an order through PaymentIntentOrder.
        """

        return (
            db.query(PaymentIntent)
            .join(
                PaymentIntentOrder,
                PaymentIntentOrder.intent_id
                == PaymentIntent.intent_id,
            )
            .filter(
                PaymentIntentOrder.order_id == order_id
            )
            .with_for_update()
            .first()
        )

    @staticmethod
    def get_intent_by_order_for_update(
        db: Session,
        order_id: int,
    ):
        """
        Fetch and lock the payment intent associated
        with an order.

        Supports:

        1. Legacy/single-order intents
        2. Multi-order intents
        """

        intent = (
            db.query(PaymentIntent)
            .filter(
                PaymentIntent.order_id == order_id
            )
            .with_for_update()
            .first()
        )

        if intent:
            return intent

        return PaymentRepository.get_intent_for_order_for_update(
            db=db,
            order_id=order_id,
        )

    @staticmethod
    def is_order_linked_to_intent(
        db: Session,
        intent_id: int,
        order_id: int,
    ):
        """
        Check whether an order already belongs to
        a payment intent.
        """

        return (
            db.query(PaymentIntentOrder)
            .filter(
                PaymentIntentOrder.intent_id == intent_id,
                PaymentIntentOrder.order_id == order_id,
            )
            .first()
            is not None
        )

    # ============================================================
    # PAYMENT ATTEMPTS
    # ============================================================

    @staticmethod
    def create_attempt(
        db: Session,
        intent_id: int,
        gateway: str,
        merchant_order_id: str,
        amount: float,
    ):
        """
        Create an original payment attempt.

        amount represents the total amount of this payment attempt.

        Example:

            PaymentIntent = ₹954
            PaymentAttempt = ₹954

        Refund attempts are created separately.
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
            amount=amount,
            attempt_number=attempt_number,
            status=PaymentAttemptStatus.INITIATED.value,
            parent_payment_id=None,
            refund_order_id=None,
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

        Includes:

        - original payment attempts
        - refund attempts
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
    # PAYMENT ATTEMPT LOOKUPS
    # ============================================================

    @staticmethod
    def get_attempt_by_merchant_order_id(
        db: Session,
        merchant_order_id: str,
    ):
        """
        Find an original PhonePe payment attempt.
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
        Explicit alias for the latest original payment attempt.
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
        Return the latest successful original payment attempt.
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

        Active states:

            INITIATED
            REDIRECTED
        """

        return (
            db.query(PaymentAttempt)
            .filter(
                PaymentAttempt.intent_id == intent_id,
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
        Payment and refund attempts share the same
        attempt number sequence.
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

        db.flush()

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

        db.flush()

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

        db.flush()

        return attempt

    @staticmethod
    def mark_attempt_cancelled(
        db: Session,
        attempt: PaymentAttempt,
    ):
        attempt.status = (
            PaymentAttemptStatus.CANCELLED.value
        )

        db.flush()

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

        ONLY for normal payment attempts.
        """

        attempt.phonepe_order_id = phonepe_order_id

        attempt.response_payload = response

        attempt.status = (
            PaymentAttemptStatus.REDIRECTED.value
        )

        db.flush()

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
        refund_order_id: int,
        amount: float,
    ):
        """
        Create a refund attempt for ONE specific order.

        Example:

            PaymentIntent = ₹954

            Refund attempt:
                refund_order_id = 102
                amount = ₹318
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
            amount=amount,
            attempt_number=attempt_number,
            status=PaymentAttemptStatus.INITIATED.value,
            parent_payment_id=parent_attempt_id,
            refund_order_id=refund_order_id,
        )

        db.add(refund)
        db.flush()

        return refund

    # ============================================================
    # REFUND ATTEMPT LOOKUPS
    # ============================================================

    @staticmethod
    def get_refund_attempt(
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
    def get_refund_attempt_for_update(
        db: Session,
        intent_id: int,
    ):
        """
        Return the latest refund attempt for an intent
        while locking the row.
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

    @staticmethod
    def get_latest_refund_attempt_for_order(
        db: Session,
        intent_id: int,
        order_id: int,
    ):
        """
        Return the latest refund attempt for one specific order.
        """

        return (
            db.query(PaymentAttempt)
            .filter(
                PaymentAttempt.intent_id == intent_id,
                PaymentAttempt.refund_order_id == order_id,
                PaymentAttempt.parent_payment_id.isnot(None),
            )
            .order_by(
                PaymentAttempt.attempt_number.desc()
            )
            .first()
        )

    @staticmethod
    def get_latest_refund_attempt_for_order_for_update(
        db: Session,
        intent_id: int,
        order_id: int,
    ):
        """
        Return and lock the latest refund attempt
        for one specific order.
        """

        return (
            db.query(PaymentAttempt)
            .filter(
                PaymentAttempt.intent_id == intent_id,
                PaymentAttempt.refund_order_id == order_id,
                PaymentAttempt.parent_payment_id.isnot(None),
            )
            .order_by(
                PaymentAttempt.attempt_number.desc()
            )
            .with_for_update()
            .first()
        )

    @staticmethod
    def get_active_refund_attempt(
        db: Session,
        intent_id: int,
    ):
        """
        Return any active refund attempt for the intent.
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
    def get_active_refund_attempt_for_order(
        db: Session,
        intent_id: int,
        order_id: int,
    ):
        """
        Return an active refund attempt for one specific order.

        Prevents duplicate refunds for the same order.
        """

        return (
            db.query(PaymentAttempt)
            .filter(
                PaymentAttempt.intent_id == intent_id,
                PaymentAttempt.parent_payment_id.isnot(None),
                PaymentAttempt.refund_order_id == order_id,
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

    @staticmethod
    def get_failed_refund_attempt_for_order(
        db: Session,
        intent_id: int,
        order_id: int,
    ):
        """
        Return the latest failed refund attempt for one order.
        """

        return (
            db.query(PaymentAttempt)
            .filter(
                PaymentAttempt.intent_id == intent_id,
                PaymentAttempt.parent_payment_id.isnot(None),
                PaymentAttempt.refund_order_id == order_id,
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
        """

        attempt.merchant_refund_id = merchant_refund_id
        attempt.gateway_refund_id = gateway_refund_id

        attempt.response_payload = response

        attempt.status = (
            PaymentAttemptStatus.INITIATED.value
        )

        db.flush()

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

        db.flush()

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
    # REFUND AGGREGATE STATE
    # ============================================================

    @staticmethod
    def are_all_orders_refunded(
        db: Session,
        intent_id: int,
    ) -> bool:
        """
        Return True only when every order linked to the
        payment intent is REFUNDED.

        Used to determine whether the entire PaymentIntent
        can become REFUNDED.
        """

        from app.modules.orders.models import Order
        from app.modules.orders.constants import PaymentStatus

        order_ids = (
            PaymentRepository.get_order_ids_for_intent(
                db,
                intent_id,
            )
        )

        # Backward compatibility for legacy intents.
        if not order_ids:
            intent = db.get(
                PaymentIntent,
                intent_id,
            )

            if not intent:
                return False

            order_ids = [intent.order_id]

        refunded_count = (
            db.query(Order)
            .filter(
                Order.order_id.in_(order_ids),
                Order.payment_status
                == PaymentStatus.REFUNDED.value,
            )
            .count()
        )

        return refunded_count == len(order_ids)

    # ============================================================
    # REFUND / INTENT AGGREGATE STATE
    # ============================================================

    @staticmethod
    def calculate_intent_refund_status(
        db: Session,
        intent: PaymentIntent,
    ):
        """
        Calculate the aggregate refund state of a PaymentIntent.

        Rules:

            ALL linked orders REFUNDED
                -> REFUNDED

            At least one refund is active
                -> REFUND_INITIATED

            No active refund, but at least one refund failed
                -> REFUND_FAILED

            Otherwise
                -> current intent status

        Does NOT modify the database.
        """

        from app.modules.orders.models import Order
        from app.modules.orders.constants import PaymentStatus

        orders = (
            db.query(Order)
            .join(
                PaymentIntentOrder,
                PaymentIntentOrder.order_id
                == Order.order_id,
            )
            .filter(
                PaymentIntentOrder.intent_id
                == intent.intent_id,
            )
            .all()
        )

        # --------------------------------------------------------
        # Backward compatibility
        # --------------------------------------------------------

        if not orders:

            anchor_order = db.get(
                Order,
                intent.order_id,
            )

            if anchor_order:
                orders = [anchor_order]

        if not orders:
            return intent.status

        # ========================================================
        # ALL ORDERS REFUNDED
        # ========================================================

        if all(
            order.payment_status
            == PaymentStatus.REFUNDED.value
            for order in orders
        ):
            return PaymentIntentStatus.REFUNDED.value

        # ========================================================
        # ACTIVE REFUND
        # ========================================================

        active_refund_exists = (
            db.query(PaymentAttempt)
            .filter(
                PaymentAttempt.intent_id
                == intent.intent_id,
                PaymentAttempt.parent_payment_id
                .isnot(None),
                PaymentAttempt.status.in_([
                    PaymentAttemptStatus.INITIATED.value,
                    PaymentAttemptStatus.REDIRECTED.value,
                ]),
            )
            .first()
            is not None
        )

        if active_refund_exists:
            return PaymentIntentStatus.REFUND_INITIATED.value

        # ========================================================
        # FAILED REFUND
        # ========================================================

        failed_refund_exists = (
            db.query(PaymentAttempt)
            .filter(
                PaymentAttempt.intent_id
                == intent.intent_id,
                PaymentAttempt.parent_payment_id
                .isnot(None),
                PaymentAttempt.status
                == PaymentAttemptStatus.FAILED.value,
            )
            .first()
            is not None
        )

        if failed_refund_exists:
            return PaymentIntentStatus.REFUND_FAILED.value

        return intent.status

    @staticmethod
    def refresh_intent_refund_status(
        db: Session,
        intent: PaymentIntent,
    ):
        """
        Recalculate and update the aggregate refund state.

        Does not commit.
        Caller controls the transaction.
        """

        new_status = (
            PaymentRepository.calculate_intent_refund_status(
                db=db,
                intent=intent,
            )
        )

        if intent.status != new_status:
            intent.status = new_status
            db.flush()

        return intent

    # ============================================================
    # RELATED ORDERS
    # ============================================================

    @staticmethod
    def get_orders_for_intent_with_orders(
        db: Session,
        intent_id: int,
    ):
        """
        Return all Order objects belonging to a PaymentIntent.
        """

        from app.modules.orders.models import Order

        return (
            db.query(Order)
            .join(
                PaymentIntentOrder,
                PaymentIntentOrder.order_id
                == Order.order_id,
            )
            .filter(
                PaymentIntentOrder.intent_id == intent_id
            )
            .order_by(
                PaymentIntentOrder.id.asc()
            )
            .all()
        )

    @staticmethod
    def get_latest_refund_attempt_for_order(
        db: Session,
        intent_id: int,
        order_id: int,
    ):
        """
        Return the latest refund attempt for one specific order.
        """

        return (
            db.query(PaymentAttempt)
            .filter(
                PaymentAttempt.intent_id == intent_id,
                PaymentAttempt.refund_order_id == order_id,
                PaymentAttempt.parent_payment_id.isnot(None),
            )
            .order_by(
                PaymentAttempt.attempt_number.desc()
            )
            .first()
        )

    @staticmethod
    def get_latest_refund_attempt_for_order_for_update(
        db: Session,
        intent_id: int,
        order_id: int,
    ):
        """
        Return the latest refund attempt for one order
        while locking the row.
        """

        return (
            db.query(PaymentAttempt)
            .filter(
                PaymentAttempt.intent_id == intent_id,
                PaymentAttempt.refund_order_id == order_id,
                PaymentAttempt.parent_payment_id.isnot(None),
            )
            .order_by(
                PaymentAttempt.attempt_number.desc()
            )
            .with_for_update()
            .first()
        )

    @staticmethod
    def get_refund_attempts_for_order(
        db: Session,
        intent_id: int,
        order_id: int,
    ):
        """
        Return all refund attempts for one specific order.
        """

        return (
            db.query(PaymentAttempt)
            .filter(
                PaymentAttempt.intent_id == intent_id,
                PaymentAttempt.refund_order_id == order_id,
                PaymentAttempt.parent_payment_id.isnot(None),
            )
            .order_by(
                PaymentAttempt.attempt_number.asc()
            )
            .all()
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
        Save gateway response without changing state.
        """

        attempt.response_payload = response

        db.flush()

        return attempt


    @staticmethod
    def get_refund_attempt_for_order_for_update(
        db: Session,
        intent_id: int,
        order_id: int,
    ):
        """
        Return the latest refund attempt for a specific order while locking the row.
        """
        return (
            db.query(PaymentAttempt)
            .filter(
                PaymentAttempt.intent_id == intent_id,
                PaymentAttempt.parent_payment_id.isnot(None),
                PaymentAttempt.refund_order_id == order_id,
            )
            .order_by(
                PaymentAttempt.attempt_number.desc()
            )
            .with_for_update()
            .first()
        )