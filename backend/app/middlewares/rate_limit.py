from fastapi import Request, HTTPException
from starlette.middleware.base import BaseHTTPMiddleware
from app.core.redis import redis_client
from app.core.config import settings

REQUEST_LIMIT = 120        # requests
WINDOW_SECONDS = 60        # per minute


class RateLimitMiddleware(BaseHTTPMiddleware):

    async def dispatch(self, request: Request, call_next):

        #skip cors preflight requests
        if request.method == "OPTIONS":
            return await call_next(request)

        # -------------------------
        # Get Real IP (behind nginx / load balancer)
        # -------------------------
        forwarded = request.headers.get("x-forwarded-for")
        if forwarded:
            ip = forwarded.split(",")[0].strip()
        else:
            ip = request.client.host

        # Optional: Skip internal health checks
        if request.url.path.startswith("/docs") or request.url.path.startswith("/openapi"):
            return await call_next(request)

        key = f"rate_limit:{ip}"

        try:
            # Atomic increment
            current = redis_client.incr(key)

            # Set expiry only when first request
            if current == 1:
                redis_client.expire(key, WINDOW_SECONDS)

            if current > REQUEST_LIMIT:
                raise HTTPException(
                    status_code=429,
                    detail="Too many requests. Please slow down."
                )

        except Exception:
            # Fail open (do not block app if Redis fails)
            pass

        response = await call_next(request)
        return response