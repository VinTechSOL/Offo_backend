import requests
from fastapi import HTTPException
from app.core.config import settings


class MSG91Client:

    BASE_URL = "https://control.msg91.com/api/v5/flow"

    @staticmethod
    def send_otp(mobile: str, otp: str, name: str):

        payload = {
            "template_id": settings.MSG91_TEMPLATE_ID,
            "short_url": "0",
            "realTimeResponse": "1",
            "recipients": [
                {
                    "mobiles": f"91{mobile}",
                    "alphanumeric": name,   # matches ##alphanumeric##
                    "numeric": otp          # matches ##numeric##
                }
            ]
        }

        headers = {
            "accept": "application/json",
            "authkey": settings.MSG91_AUTH_KEY,
            "content-type": "application/json"
        }

        response = requests.post(
            MSG91Client.BASE_URL,
            json=payload,
            headers=headers,
            timeout=10
        )

        print("MSG91 STATUS:", response.status_code)
        print("MSG91 RESPONSE:", response.text)

        if response.status_code != 200:
            raise HTTPException(status_code=500, detail=response.text)

        return response.json()