"""Exceções customizadas para a aplicação.

Fornece classes de exceção padronizadas para diferentes cenários de erro
na API.
"""

from typing import Any, Optional


class AppException(Exception):
    """Exceção base para erros da aplicação."""

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
    """Exceção para erros do serviço Azure AI."""

    def __init__(
        self,
        message: str = "Erro no serviço Azure",
        status_code: int = 502,
        service: Optional[str] = None,
        details: Optional[dict[str, Any]] = None,
    ):
        super().__init__(message, status_code, details)
        self.service = service


class ValidationException(AppException):
    """Exceção para erros de validação de input."""

    def __init__(
        self,
        message: str = "Erro de validação",
        field: Optional[str] = None,
        details: Optional[dict[str, Any]] = None,
    ):
        super().__init__(message, 400, details)
        self.field = field


class RateLimitException(AppException):
    """Exceção para erros de rate limiting."""

    def __init__(
        self,
        message: str = "Limite de requisições excedido",
        service: Optional[str] = None,
        retry_after: Optional[int] = None,
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
        details: Optional[dict[str, Any]] = None,
    ):
        super().__init__(message, status_code, details)


class AuthenticationException(SecurityException):
    """Exceção para erros de autenticação."""

    def __init__(
        self,
        message: str = "Falha na autenticação",
        details: Optional[dict[str, Any]] = None,
    ):
        super().__init__(message, 401, details)


class QuotaExceededException(AppException):
    """Exceção para erros de quota excedida no Azure."""

    def __init__(
        self,
        message: str = "Quota do Azure excedida",
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
