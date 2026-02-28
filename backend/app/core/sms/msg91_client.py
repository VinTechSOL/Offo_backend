import requests
from app.core.config import settings
from fastapi import HTTPException

class MSG91Client:

    BASE_URL = "https://control.msg91.com/api/v5/otp"

    @staticmethod
    def send_otp(mobile: str, otp: str, name: str):
        """
        mobile -> 10 digit number
        otp -> generated OTP
        name -> first name
        """

        payload = {
            "template_id": settings.MSG91_WIDGET_ID,
            "mobile": f"91{mobile}",
            "otp": otp,
            "VAR1": name,
        }

        headers = {
            "authkey": settings.MSG91_AUTH_KEY,
            "Content-Type": "application/json",
        }

        response = requests.post(
            MSG91Client.BASE_URL,
            json=payload,
            headers=headers,
            timeout=10,
        )

        data = response.json()

        if response.status_code != 200:
            raise HTTPException(status_code=500,detail="failed to send otp via sms")

        return data