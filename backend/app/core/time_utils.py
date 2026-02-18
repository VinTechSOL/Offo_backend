from datetime import datetime, timezone
from pytz import timezone as pytz_timezone

IST = pytz_timezone("Asia/Kolkata")


# Always use this inside backend logic
def now_utc():
    return datetime.now(timezone.utc)


# Convert DB UTC → IST (for API responses)
def to_ist(dt):
    if not dt:
        return None
    return dt.astimezone(IST)


# Convert IST → UTC (for incoming scheduled orders)
def ist_to_utc(dt):
    if not dt:
        return None
    return IST.localize(dt).astimezone(timezone.utc)
