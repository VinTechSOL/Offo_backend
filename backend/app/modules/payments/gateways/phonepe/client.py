
import logging

from phonepe.sdk.pg.payments.v2.models.request.standard_checkout_pay_request import (
    StandardCheckoutPayRequest,
)
from phonepe.sdk.pg.common.models.request.meta_info import MetaInfo


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

        request = StandardCheckoutPayRequest.build_request(
            merchant_order_id=merchant_order_id,
            amount=amount,
            redirect_url = redirect_url,
            meta_info=meta_info,
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