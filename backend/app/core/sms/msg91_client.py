import requests
from fastapi import HTTPException
from app.core.config import settings


class MSG91Client:

    BASE_URL = "https://control.msg91.com/api/v5/otp"

    @staticmethod
    def send_otp(mobile: str, otp: str, name: str):

        # Ensure 10 digit number only
        mobile = mobile.strip()

        if not mobile.isdigit() or len(mobile) != 10:
            raise HTTPException(
                status_code=400,
                detail="Invalid mobile number format"
            )

        payload = {
            "template_id": settings.MSG91_TEMPLATE_ID,
            "mobile": f"91{mobile}",
            "authkey": settings.MSG91_AUTH_KEY,
            "otp": otp,
            "VAR1": name
        }

        headers = {
            "Content-Type": "application/json"
        }

        try:
            response = requests.post(
                MSG91Client.BASE_URL,
                json=payload,
                headers=headers,
                timeout=10
            )
        except requests.RequestException:
            raise HTTPException(
                status_code=500,
                detail="MSG91 connection failed"
            )

        print("MSG91 STATUS:", response.status_code)
        print("MSG91 RESPONSE:", response.text)

        if response.status_code != 200:
            raise HTTPException(
                status_code=500,
                detail="Failed to send OTP via MSG91"
            )

        return response.json()