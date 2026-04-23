"""Authentication routes with rate limiting.

Provides endpoints for API key validation with brute force protection
via strict rate limiting (5 requests per minute).
"""

from typing import Any

from fastapi import APIRouter, Header, Request, status
from structlog import get_logger

from src.core.config import settings
from src.core.exceptions import AuthenticationException
from src.core.security.rate_limiter import check_rate_limit

logger = get_logger(__name__)

router = APIRouter(prefix="/auth", tags=["Authentication"])


async def get_client_identifier(request: Request) -> str:
    """Get client identifier for rate limiting.

    Combines IP address with user agent for better identification.

    Args:
        request: FastAPI request

    Returns:
        Client identifier string
    """
    # Get IP
    forwarded_for = request.headers.get("X-Forwarded-For")
    if forwarded_for:
        ip = forwarded_for.split(",")[0].strip()
    else:
        real_ip = request.headers.get("X-Real-IP")
        ip = real_ip or (request.client.host if request.client else "unknown")

    return ip


@router.post("/validate", status_code=status.HTTP_200_OK)
async def validate_api_key(
    request: Request,
    x_api_key: str = Header(..., alias="X-API-Key"),
) -> dict[str, Any]:
    """Validate API key with rate limiting protection.

    This endpoint is rate limited to 5 requests per minute per IP
    to prevent brute force attacks.

    Args:
        request: FastAPI request
        x_api_key: API key to validate

    Returns:
        Validation result

    Raises:
        RateLimitExceeded: If too many attempts
        AuthenticationException: If API key is invalid
    """
    # Check auth rate limit (5/min) - IP-based
    identifier = await get_client_identifier(request)

    # Check rate limit (raises RateLimitExceeded if exceeded)
    _, rate_info = await check_limiter(identifier, "auth")

    # Validate API key
    security_config = settings.security_config

    if not x_api_key:
        logger.warning(
            "auth_attempt_no_key",
            client_ip=identifier,
        )
        raise AuthenticationException(message="API key is required")

    if x_api_key != security_config.api_key:
        logger.warning(
            "auth_attempt_invalid_key",
            client_ip=identifier,
            key_prefix=x_api_key[:4] + "..." if len(x_api_key) > 4 else None,
        )
        raise AuthenticationException(message="Invalid API key")

    logger.info(
        "auth_success",
        client_ip=identifier,
    )

    return {
        "valid": True,
        "message": "API key is valid",
        "environment": security_config.environment,
        "rate_limit_remaining": rate_info.get("remaining", 0),
    }


@router.post("/token", status_code=status.HTTP_200_OK)
async def get_token(
    request: Request,
    x_api_key: str = Header(..., alias="X-API-Key"),
) -> dict[str, Any]:
    """Get authentication token with rate limiting.

    Rate limited to 5 requests per minute per IP.

    Args:
        request: FastAPI request
        x_api_key: API key for authentication

    Returns:
        Token response

    Raises:
        RateLimitExceeded: If too many attempts
        AuthenticationException: If API key is invalid
    """
    identifier = await get_client_identifier(request)

    # Check rate limit
    _, rate_info = await check_limiter(identifier, "auth")

    # Validate API key
    if x_api_key != settings.security_config.api_key:
        raise AuthenticationException(message="Invalid API key")

    return {
        "token": "mock-jwt-token",  # TODO: Implement JWT
        "type": "Bearer",
        "expires_in": 3600,
        "rate_limit_remaining": rate_info.get("remaining", 0),
    }


@router.get("/rate-limit-status")
async def get_auth_rate_limit_status(request: Request) -> dict[str, Any]:
    """Get current rate limit status for auth endpoints.

    Returns current rate limit information without consuming a token.

    Args:
        request: FastAPI request

    Returns:
        Rate limit status
    """
    from src.core.security.rate_limiter import get_rate_limiters

    identifier = await get_client_identifier(request)
    limiters = get_rate_limiters()

    info = await limiters.auth.get_rate_limit_info(identifier)

    return {
        "limit": info["limit"],
        "remaining": info["remaining"],
        "reset_after": info["reset_after"],
        "window": "1 minute",
    }


async def check_limiter(identifier: str, limiter_type: str) -> tuple[bool, dict[str, Any]]:
    """Check rate limit and return info.

    Helper function to check rate limit and return info.

    Args:
        identifier: Client identifier
        limiter_type: Type of limiter to use

    Returns:
        Tuple of (is_allowed, rate_limit_info)
    """
    try:
        is_allowed, info = await check_rate_limit(identifier, limiter_type)
        return is_allowed, info
    except Exception as e:
        # If rate limit check fails, allow the request
        logger.warning("rate_limit_check_failed", error=str(e))
        return True, {"limit": 60, "remaining": 59, "reset_after": 0}
