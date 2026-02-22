from datetime import datetime, timedelta, timezone
from fastapi import HTTPException, Request
from app.core.redis import redis_client

# -------------------------
# CONFIG
# -------------------------

OTP_REQUEST_LIMIT = 3
OTP_REQUEST_WINDOW = 300  # 5 minutes

OTP_VERIFY_LIMIT = 5
OTP_VERIFY_WINDOW = 300  # 5 minutes

NAME_MAX_LENGTH = 50

# -------------------------
# RATE LIMIT OTP REQUEST
# -------------------------

def rate_limit_otp_request(mobile: str):
    key = f"otp:req:{mobile}"

    count = redis_client.get(key)

    if count and int(count) >= OTP_REQUEST_LIMIT:
        raise HTTPException(
            status_code=429,
            detail="Too many OTP requests. Please try later."
        )

    redis_client.incr(key)
    redis_client.expire(key, OTP_REQUEST_WINDOW)


# -------------------------
# RATE LIMIT OTP VERIFY
# -------------------------

def rate_limit_otp_verify(mobile: str):
    key = f"otp:verify:{mobile}"

    count = redis_client.get(key)

    if count and int(count) >= OTP_VERIFY_LIMIT:
        raise HTTPException(
            status_code=429,
            detail="Too many failed attempts. Try again later."
        )

    redis_client.incr(key)
    redis_client.expire(key, OTP_VERIFY_WINDOW)


def reset_otp_verify_limit(mobile: str):
    redis_client.delete(f"otp:verify:{mobile}")


# -------------------------
# GENERIC RESPONSE HELPER
# -------------------------

def generic_otp_response():
    # Always same message to prevent enumeration
    return {"message": "If this number is valid, you will receive an OTP."}


# -------------------------
# NAME VALIDATION
# -------------------------

def validate_name(name: str, field: str):
    if not name:
        raise HTTPException(status_code=400, detail=f"{field} is required")

    if len(name) > NAME_MAX_LENGTH:
        raise HTTPException(status_code=400, detail=f"{field} too long")

    if not name.replace(" ", "").isalpha():
        raise HTTPException(status_code=400, detail=f"{field} must contain only letters")


# -------------------------
# CLEANUP EXPIRED SIGNUP SESSIONS
# -------------------------

def is_signup_session_expired(session):
    if not session:
        return True

    return session.expires_at < datetime.now(timezone.utc)