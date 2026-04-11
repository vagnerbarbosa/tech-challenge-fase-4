"""Clientes e infraestrutura para serviços Azure."""

from src.infrastructure.azure_clients import (
    AuthenticationError,
    AzureClientError,
    AzureConfigurationError,
    AzureConnectionError,
    AzureServiceError,
    QuotaExceededError,
    get_text_analytics_client,
    safe_azure_call,
)

__all__ = [
    "AzureClientError",
    "AzureConfigurationError",
    "AzureServiceError",
    "AzureConnectionError",
    "QuotaExceededError",
    "AuthenticationError",
    "get_text_analytics_client",
    "safe_azure_call",
]
