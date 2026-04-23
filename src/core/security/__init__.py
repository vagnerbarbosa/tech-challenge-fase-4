"""Core security module.

Provides security-related utilities, models, and sanitization.
"""

from src.core.security.auth import (
    APIKeyValidator,
    BOLAProtector,
    RBACValidator,
    get_api_key_validator,
    get_bola_protector,
    get_rbac_validator,
)
from src.core.security.log_sanitizer import LogSanitizer, PatientIdHasher, SecretMasker
from src.core.security.models import SecurityContext
from src.core.security.rate_limiter import (
    MemoryRateLimiterBackend,
    RateLimiterBackend,
    RateLimiters,
    RedisRateLimiterBackend,
    TokenBucketRateLimiter,
    check_rate_limit,
    create_rate_limiter,
    get_rate_limiters,
)

__all__ = [
    # Models
    "SecurityContext",
    # Auth (T014, T015, T017)
    "APIKeyValidator",
    "RBACValidator",
    "BOLAProtector",
    "get_api_key_validator",
    "get_rbac_validator",
    "get_bola_protector",
    # Sanitization
    "SecretMasker",
    "PatientIdHasher",
    "LogSanitizer",
    # Rate Limiting
    "TokenBucketRateLimiter",
    "MemoryRateLimiterBackend",
    "RedisRateLimiterBackend",
    "RateLimiterBackend",
    "RateLimiters",
    "check_rate_limit",
    "create_rate_limiter",
    "get_rate_limiters",
]
