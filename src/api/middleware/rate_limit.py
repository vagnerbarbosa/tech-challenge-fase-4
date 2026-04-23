"""Rate limiting middleware for FastAPI.

Adds X-RateLimit-* headers to all responses and handles rate limit exceptions.
"""

from collections.abc import Awaitable, Callable
from typing import Any

from fastapi import Request, Response
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.responses import JSONResponse
from structlog import get_logger

from src.core.exceptions import RateLimitExceeded
from src.core.security.rate_limiter import (
    RateLimiters,
    check_rate_limit,
    get_rate_limiters,
)

logger = get_logger(__name__)


class RateLimitMiddleware(BaseHTTPMiddleware):
    """Middleware to add rate limiting headers to responses.

    Adds the following headers to all responses:
    - X-RateLimit-Limit: Maximum requests allowed
    - X-RateLimit-Remaining: Remaining requests in window
    - X-RateLimit-Reset: Seconds until rate limit resets
    """

    def __init__(
        self,
        app: Any,
        limiter_type: str = "general",
        skip_paths: list[str] | None = None,
    ) -> None:
        """Initialize rate limit middleware.

        Args:
            app: FastAPI application
            limiter_type: Type of rate limiter (general, auth, analyze, health)
            skip_paths: List of paths to skip rate limiting
        """
        super().__init__(app)
        self.limiter_type = limiter_type
        self.skip_paths = skip_paths or ["/health", "/docs", "/openapi.json", "/redoc"]
        self._limiters: RateLimiters | None = None

    async def dispatch(
        self,
        request: Request,
        call_next: Callable[[Request], Awaitable[Response]],
    ) -> Response:
        """Process request and add rate limit headers.

        Args:
            request: FastAPI request
            call_next: Next middleware/handler

        Returns:
            Response with rate limit headers
        """
        # Skip rate limiting for certain paths
        path = request.url.path
        if any(path.startswith(skip) for skip in self.skip_paths):
            return await call_next(request)

        # Get client identifier
        identifier = self._get_client_identifier(request)

        try:
            # Check rate limit and get info
            is_allowed, info = await check_rate_limit(identifier, self.limiter_type)

            # Process request
            response = await call_next(request)

            # Add rate limit headers
            response.headers["X-RateLimit-Limit"] = str(info["limit"])
            response.headers["X-RateLimit-Remaining"] = str(info["remaining"])
            response.headers["X-RateLimit-Reset"] = str(info["reset_after"])

            return response

        except RateLimitExceeded as exc:
            # Return 429 with retry-after header
            retry_after = exc.retry_after or 60

            logger.warning(
                "rate_limit_exceeded",
                path=path,
                identifier=identifier[:8] + "...",  # Partial identifier for privacy
                retry_after=retry_after,
            )

            return JSONResponse(
                status_code=429,
                content={
                    "error": "RateLimitExceeded",
                    "message": exc.message,
                    "retry_after": retry_after,
                },
                headers={
                    "Retry-After": str(retry_after),
                    "X-RateLimit-Limit": str(exc.details.get("limit", 60)),
                    "X-RateLimit-Remaining": "0",
                },
            )

    def _get_client_identifier(self, request: Request) -> str:
        """Extract client identifier from request.

        Priority:
        1. X-API-Key header (hashed)
        2. X-Forwarded-For header (first IP)
        3. X-Real-IP header
        4. Remote address

        Args:
            request: FastAPI request

        Returns:
            Client identifier string
        """
        # Check for API key first
        api_key = request.headers.get("X-API-Key")
        if api_key:
            return f"api:{api_key}"

        # Get IP address
        forwarded_for = request.headers.get("X-Forwarded-For")
        if forwarded_for:
            # First IP in X-Forwarded-For is the client
            return forwarded_for.split(",")[0].strip()

        real_ip = request.headers.get("X-Real-IP")
        if real_ip:
            return real_ip

        # Fall back to remote address
        if request.client:
            return str(request.client.host)

        return "unknown"


class AuthRateLimitMiddleware(BaseHTTPMiddleware):
    """Stricter rate limiting for authentication endpoints.

    Applies stricter rate limits (5/min) to auth-related endpoints
    to protect against brute force attacks.
    """

    def __init__(
        self,
        app: Any,
        protected_paths: list[str] | None = None,
    ) -> None:
        """Initialize auth rate limit middleware.

        Args:
            app: FastAPI application
            protected_paths: Paths that require stricter rate limiting
        """
        super().__init__(app)
        self.protected_paths = protected_paths or [
            "/auth",
            "/login",
            "/token",
            "/api-key",
        ]

    async def dispatch(
        self,
        request: Request,
        call_next: Callable[[Request], Awaitable[Response]],
    ) -> Response:
        """Process request with auth-specific rate limiting.

        Args:
            request: FastAPI request
            call_next: Next middleware/handler

        Returns:
            Response with rate limit headers
        """
        path = request.url.path

        # Only apply to auth paths
        if not any(path.startswith(p) for p in self.protected_paths):
            return await call_next(request)

        identifier = self._get_client_identifier(request)

        try:
            # Use auth rate limiter (5/min)
            is_allowed, info = await check_rate_limit(identifier, "auth")

            response = await call_next(request)

            # Add rate limit headers
            response.headers["X-RateLimit-Limit"] = str(info["limit"])
            response.headers["X-RateLimit-Remaining"] = str(info["remaining"])
            response.headers["X-RateLimit-Reset"] = str(info["reset_after"])

            return response

        except RateLimitExceeded as exc:
            retry_after = exc.retry_after or 60

            logger.warning(
                "auth_rate_limit_exceeded",
                path=path,
                identifier=identifier[:8] + "...",
                retry_after=retry_after,
            )

            return JSONResponse(
                status_code=429,
                content={
                    "error": "RateLimitExceeded",
                    "message": "Too many authentication attempts. Please try again later.",
                    "retry_after": retry_after,
                },
                headers={
                    "Retry-After": str(retry_after),
                    "X-RateLimit-Limit": str(exc.details.get("limit", 5)),
                    "X-RateLimit-Remaining": "0",
                },
            )

    def _get_client_identifier(self, request: Request) -> str:
        """Extract client identifier from request.

        For auth endpoints, use IP + path combination to prevent
        distributed attacks on the same endpoint.
        """
        # Get IP address
        forwarded_for = request.headers.get("X-Forwarded-For")
        if forwarded_for:
            ip = forwarded_for.split(",")[0].strip()
        else:
            real_ip = request.headers.get("X-Real-IP")
            ip = real_ip or (request.client.host if request.client else "unknown")

        # Include path in identifier to rate limit per endpoint
        return f"{ip}:{request.url.path}"


# Helper functions for manual rate limit checks

async def add_rate_limit_headers(
    response: Response,
    identifier: str,
    limiter_type: str = "general",
) -> Response:
    """Add rate limit headers to a response.

    Args:
        response: FastAPI response
        identifier: Client identifier
        limiter_type: Type of rate limiter

    Returns:
        Response with headers added
    """
    limiters = get_rate_limiters()

    limiter_map = {
        "general": limiters.general,
        "auth": limiters.auth,
        "analyze": limiters.analyze,
        "health": limiters.health,
    }

    limiter = limiter_map.get(limiter_type, limiters.general)
    info = await limiter.get_rate_limit_info(identifier)

    response.headers["X-RateLimit-Limit"] = str(info["limit"])
    response.headers["X-RateLimit-Remaining"] = str(info["remaining"])
    response.headers["X-RateLimit-Reset"] = str(info["reset_after"])

    return response
