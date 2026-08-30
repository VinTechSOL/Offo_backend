
import logging

from phonepe.sdk.pg.payments.v2.models.request.standard_checkout_pay_request import (
    StandardCheckoutPayRequest,
)


from phonepe.sdk.pg.common.models.request.refund_request import (
    RefundRequest,
)
from phonepe.sdk.pg.common.models.request.meta_info import MetaInfo

from phonepe.sdk.pg.common.models.request.payment_mode_constraints.upi_intent_payment_mode import (
    UpiIntentPaymentModeConstraint,
)
from phonepe.sdk.pg.common.models.request.payment_mode_constraints.upi_qr_payment_mode import (
    UpiQrPaymentModeConstraint,
)
from phonepe.sdk.pg.common.models.request.pg_v2_instrument_type import (
    PgV2InstrumentType,
)
from phonepe.sdk.pg.payments.v2.models.request.payment_mode_config import (
    PaymentModeConfig,
)
from app.core.config import settings
from app.modules.payments.gateways.phonepe.sdk_client import PhonePeSDK
from urllib.parse import urlencode

class PhonePeClient:

    def __init__(self):
        self.client = PhonePeSDK.get_client()

    def validate_callback(
        self,
        *,
        authorization: str,
        body: str,
    ):
        return self.client.validate_callback(
            username=settings.PHONEPE_CALLBACK_USERNAME,
            password=settings.PHONEPE_CALLBACK_PASSWORD,
            callback_header_data=authorization,
            callback_response_data=body,
        )

    def initiate_payment(
        self,
        *,
        merchant_order_id: str,
        order_id: int,
        amount: int,
        user_id: int,
    ):
        """
        amount -> paisa
        """

        meta_info = MetaInfo(
            udf1=str(user_id),
        )

        redirect_url = (
           settings.PHONEPE_REDIRECT_URL
           + "?"
           + urlencode(
               {
                    "order_id": order_id,
               }
            )
        )

        logger = logging.getLogger(__name__)
        logger.info("Redirect URL: %s", redirect_url)

        payment_mode_config = PaymentModeConfig(
            enabled_payment_modes=[
                UpiIntentPaymentModeConstraint(),
                UpiQrPaymentModeConstraint(),
            ]
        )

        request = StandardCheckoutPayRequest.build_request(
            merchant_order_id=merchant_order_id,
            amount=amount,
            redirect_url = redirect_url,
            meta_info=meta_info,
            payment_mode_config=payment_mode_config,
            message=f"Order #{order_id}",
            expire_after=3600,
            disable_payment_retry=False,
        )

        response = self.client.pay(request)
        logger.info(
            "PhonePe Pay Response | "
            "merchant_order_id=%s "
            "phonepe_order_id=%s "
            "state=%s "
            "expire_at=%s",
            merchant_order_id,
            response.order_id,
            response.state,
            response.expire_at,
        )

        return {
            "merchant_order_id": merchant_order_id,
            "phonepe_order_id": response.order_id,
            "redirect_url": response.redirect_url,
            "state": response.state,
            "expire_at": response.expire_at,
        }


    def get_order_status(
        self,
        merchant_order_id: str,
    ):

        response = self.client.get_order_status(
            merchant_order_id=merchant_order_id,
            details=True,
        )

        logger = logging.getLogger(__name__)
        logger.info(
            "Phonepe Status Response: %s",
            response,
        )

        logger.info(
           "========== PHONEPE ORDER STATUS =========="
        )
        logger.info("Merchant Order Id : %s", merchant_order_id)
        logger.info("PhonePe Order Id  : %s", response.order_id)
        logger.info("State             : %s", response.state)
        logger.info("Amount            : %s", response.amount)
        logger.info("Expire At         : %s", response.expire_at)
        logger.info("Payment Details   : %s", response.payment_details)
        logger.info(
          "=========================================="
        )

        payment_details = []

        if response.payment_details:

            payment_details = [
                {
                    "transaction_id": p.transaction_id,
                    "payment_mode": p.payment_mode,
                    "state": p.state,
                    "amount": p.amount,
                    "error_code": getattr(
                        p,
                        "error_code",
                        None,
                    ),
                    "detailed_error_code": getattr(
                        p,
                        "detailed_error_code",
                        None,
                    ),
                }
                for p in response.payment_details
            ]

        for p in response.payment_details or []:
            logger.info(
               "Txn=%s Mode=%s State=%s Amount=%s Error=%s",
                p.transaction_id,
                p.payment_mode,
                p.state,
                p.amount,
                getattr(p, "error_code", None),
                getattr(p, "detailed_error_code", None)
            )

        return {
            "phonepe_order_id": response.order_id,
            "state": response.state,
            "amount": response.amount,
            "expire_at": response.expire_at,
            "error_code": getattr(response,"error_code",None),
            "detailed_error_code": getattr(response,"detailed_error_code",None),
            "payment_details": payment_details,
        }



    def initiate_refund(
        self,
        *,
        merchant_refund_id: str,
        amount: int,
        original_merchant_order_id: str,
    ):
        """
        Initiate a PhonePe refund.

        amount -> paisa

        original_merchant_order_id:
            The merchant order ID used for the
            original successful payment.
        """

        logger = logging.getLogger(__name__)

        refund_request = RefundRequest.build_refund_request(
            merchant_refund_id=merchant_refund_id,
            amount=amount,
            original_merchant_order_id=original_merchant_order_id,
        )

        logger.info(
            "========== PHONEPE REFUND INITIATED =========="
        )
        logger.info(
            "Merchant Refund ID       : %s",
            merchant_refund_id,
        )
        logger.info(
            "Original Merchant Order : %s",
            original_merchant_order_id,
        )
        logger.info(
            "Refund Amount (paise)    : %s",
            amount,
        )

        response = self.client.refund(refund_request)

        logger.info(
            "PhonePe Refund Response | "
            "refund_id=%s state=%s amount=%s",
            response.refund_id,
            response.state,
            response.amount,
        )

        return {
            "merchant_refund_id": merchant_refund_id,
            "refund_id": response.refund_id,
            "amount": response.amount,
            "state": response.state,
        }


    def get_refund_status(
        self,
        merchant_refund_id: str,
    ):
        """
        Fetch the latest refund status from PhonePe.
        """

        logger = logging.getLogger(__name__)

        response = self.client.get_refund_status(
            merchant_refund_id=merchant_refund_id,
        )

        payment_details = []

        for detail in response.payment_details or []:
            payment_details.append(
                {
                    "transaction_id": detail.transaction_id,
                    "payment_mode": (
                        detail.payment_mode.value
                        if hasattr(detail.payment_mode, "value")
                        else str(detail.payment_mode)
                        if detail.payment_mode
                        else None
                    ),
                    "timestamp": detail.timestamp,
                    "amount": detail.amount,
                    "state": detail.state,
                    "error_code": detail.error_code,
                    "detailed_error_code": detail.detailed_error_code,
                }
            )

        result = {
            "merchant_id": response.merchant_id,
            "merchant_refund_id": response.merchant_refund_id,
            "original_merchant_order_id": (
                response.original_merchant_order_id
            ),
            "amount": response.amount,
            "state": response.state,
            "payment_details": payment_details,
        }

        logger.info(
            "========== PHONEPE REFUND STATUS =========="
        )
        logger.info(
            "Merchant Refund ID : %s",
            response.merchant_refund_id,
        )
        logger.info(
            "Original Order     : %s",
            response.original_merchant_order_id,
        )
        logger.info(
            "State              : %s",
            response.state,
        )
        logger.info(
            "Amount             : %s",
            response.amount,
        )
        logger.info(
            "Payment Details    : %s",
            payment_details,
        )
        logger.info(
            "============================================"
        )

        return result