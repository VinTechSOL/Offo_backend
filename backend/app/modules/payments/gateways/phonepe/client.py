from uuid import uuid4

from phonepe.sdk.pg.payments.v2.models.request.standard_checkout_pay_request import (
    StandardCheckoutPayRequest,
)
from phonepe.sdk.pg.common.models.request.meta_info import MetaInfo
from phonepe.sdk.pg.common.exceptions import PhonePeException

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

        request = StandardCheckoutPayRequest.build_request(
            merchant_order_id=merchant_order_id,
            amount=amount,
            redirect_url = redirect_url,
            meta_info=meta_info,
            expire_after=3600,
            disable_payment_retry=False,
        )

        response = self.client.pay(request)

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
                }
                for p in response.payment_details
            ]

        return {
            "phonepe_order_id": response.order_id,
            "state": response.state,
            "amount": response.amount,
            "expire_at": response.expire_at,
            "payment_details": payment_details,
        }