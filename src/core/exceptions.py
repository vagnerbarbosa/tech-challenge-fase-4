"""Exceções customizadas para a aplicação.

Fornece classes de exceção padronizadas para diferentes cenários de erro
na API.
"""

from typing import Any


class AppException(Exception):
    """Exceção base para erros da aplicação."""

    def __init__(
        self,
        message: str,
        status_code: int = 500,
        details: dict[str, Any] | None = None,
    ):
        super().__init__(message)
        self.message = message
        self.status_code = status_code
        self.details = details or {}


class AzureServiceException(AppException):
    """Exceção para erros do serviço Azure AI."""

    def __init__(
        self,
        message: str = "Erro no serviço Azure",
        status_code: int = 502,
        service: str | None = None,
        details: dict[str, Any] | None = None,
    ):
        super().__init__(message, status_code, details)
        self.service = service


class ValidationException(AppException):
    """Exceção para erros de validação de input."""

    def __init__(
        self,
        message: str = "Erro de validação",
        field: str | None = None,
        details: dict[str, Any] | None = None,
    ):
        super().__init__(message, 400, details)
        self.field = field


class RateLimitException(AppException):
    """Exceção para erros de rate limiting."""

    def __init__(
        self,
        message: str = "Limite de requisições excedido",
        service: str | None = None,
        retry_after: int | None = None,
    ):
        super().__init__(message, 429, {"retry_after": retry_after})
        self.service = service
        self.retry_after = retry_after


class SecurityException(AppException):
    """Exceção para erros relacionados a segurança."""

    def __init__(
        self,
        message: str = "Erro de segurança",
        status_code: int = 403,
        details: dict[str, Any] | None = None,
    ):
        super().__init__(message, status_code, details)


class AuthenticationException(SecurityException):
    """Exceção para erros de autenticação."""

    def __init__(
        self,
        message: str = "Falha na autenticação",
        details: dict[str, Any] | None = None,
    ):
        super().__init__(message, 401, details)


class QuotaExceededException(AppException):
    """Exceção para erros de quota excedida no Azure."""

    def __init__(
        self,
        message: str = "Quota do Azure excedida",
        service: str | None = None,
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


# T005: Security Exceptions

class UnauthorizedException(SecurityException):
    """Exceção para acesso não autorizado (401)."""

    def __init__(
        self,
        message: str = "Acesso não autorizado",
        details: dict[str, Any] | None = None,
    ):
        super().__init__(message, 401, details)


class ForbiddenException(SecurityException):
    """Exceção para acesso proibido (403)."""

    def __init__(
        self,
        message: str = "Acesso proibido",
        details: dict[str, Any] | None = None,
    ):
        super().__init__(message, 403, details)


class RateLimitExceeded(AppException):
    """Exceção para limite de requisições excedido (429)."""

    def __init__(
        self,
        message: str = "Limite de requisições excedido",
        retry_after: int | None = None,
        details: dict[str, Any] | None = None,
    ):
        super().__init__(
            message,
            429,
            {"retry_after": retry_after, **(details or {})},
        )
        self.retry_after = retry_after


# Aliases para compatibilidade com azure_speech_client
AzureServiceError = AzureServiceException
AzureAuthenticationError = AuthenticationException
AzureQuotaExceededError = QuotaExceededException
AzureConnectionError = AzureServiceException
