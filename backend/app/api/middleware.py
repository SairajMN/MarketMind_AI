from slowapi import Limiter
from slowapi.util import get_remote_address
from slowapi.errors import RateLimitExceeded
from fastapi.exceptions import RequestValidationError
from fastapi import Request, HTTPException

limiter = Limiter(key_func=get_remote_address)


@limiter.request_filter
def skip_rate_limit(request: Request):
    return False


# Rate limit exception handler
def setup_rate_limit_handler(app):
    @app.exception_handler(RateLimitExceeded)
    async def rate_limit_handler(request: Request, exc: RateLimitExceeded):
        raise HTTPException(status_code=429, detail="Too many requests")
