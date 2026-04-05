"""Custom exceptions for the application.

Provides standardized exception classes for different error scenarios
in the API.
"""

from typing import Any, Optional


class AppException(Exception):
    """Base exception for application errors."""

    def __init__(
        self,
        message: str,
        status_code: int = 500,
        details: Optional[dict[str, Any]] = None,
    ):
        super().__init__(message)
        self.message = message
        self.status_code = status_code
        self.details = details or {}


class AzureServiceException(AppException):
    """Exception for Azure AI service errors."""

    def __init__(
        self,
        message: str = "Azure service error",
        status_code: int = 502,
        service: Optional[str] = None,
        details: Optional[dict[str, Any]] = None,
    ):
        super().__init__(message, status_code, details)
        self.service = service


class ValidationException(AppException):
    """Exception for input validation errors."""

    def __init__(
        self,
        message: str = "Validation error",
        field: Optional[str] = None,
        details: Optional[dict[str, Any]] = None,
    ):
        super().__init__(message, 400, details)
        self.field = field


class RateLimitException(AppException):
    """Exception for rate limiting errors."""

    def __init__(
        self,
        message: str = "Rate limit exceeded",
        service: Optional[str] = None,
        retry_after: Optional[int] = None,
    ):
        super().__init__(message, 429, {"retry_after": retry_after})
        self.service = service
        self.retry_after = retry_after


class SecurityException(AppException):
    """Exception for security-related errors."""

    def __init__(
        self,
        message: str = "Security error",
        status_code: int = 403,
        details: Optional[dict[str, Any]] = None,
    ):
        super().__init__(message, status_code, details)


class AuthenticationException(SecurityException):
    """Exception for authentication errors."""

    def __init__(
        self,
        message: str = "Authentication failed",
        details: Optional[dict[str, Any]] = None,
    ):
        super().__init__(message, 401, details)


class QuotaExceededException(AppException):
    """Exception for Azure quota exceeded errors."""

    def __init__(
        self,
        message: str = "Azure quota exceeded",
        service: Optional[str] = None,
    ):
        super().__init__(
            message,
            503,
            {
                "service": service,
                "solution": "Aguarde até meia-noite UTC ou upgrade para tier pago",
            },
        )
        self.service = service
