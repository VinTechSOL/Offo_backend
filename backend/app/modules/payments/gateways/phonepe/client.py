import uuid
from datetime import datetime


class PhonePeClient:
    """
    DEV MODE MOCK CLIENT
    """

    def initiate_payment(
        self,
        *,
        merchant_txn_id: str,
        amount: int,
        user_id: int,
    ):
        print(
            f"📡 PhonePe INITIATE | txn={merchant_txn_id} amount={amount}"
        )

        # Simulated PhonePe redirect payload
        return {
            "merchantTransactionId": merchant_txn_id,
            "redirectUrl": f"https://phonepe.mock/redirect/{uuid.uuid4()}",
            "amount": amount,
            "status": "REDIRECTED",
            "createdAt": datetime.utcnow().isoformat(),
        }
