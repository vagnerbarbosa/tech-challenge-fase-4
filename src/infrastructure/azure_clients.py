"""Clientes Azure AI com padrão singleton para uso eficiente de recursos."""

import os
from functools import lru_cache
from typing import Any, Callable, TypeVar

from azure.ai.textanalytics import TextAnalyticsClient
from azure.core.credentials import AzureKeyCredential
from azure.core.pipeline.policies import RetryPolicy


class AzureClientError(Exception):
    """Exceção base para erros de cliente Azure."""
    pass


class AzureConfigurationError(AzureClientError):
    """Levantada quando a configuração Azure está ausente ou inválida."""
    pass


class AzureServiceError(AzureClientError):
    """Levantada quando o serviço Azure retorna um erro."""
    pass


class AzureConnectionError(AzureClientError):
    """Levantada quando a conexão com Azure falha."""
    pass


class QuotaExceededError(AzureClientError):
    """Levantada quando a quota Azure é excedida."""
    pass


class AuthenticationError(AzureClientError):
    """Levantada quando a autenticação Azure falha."""
    pass


def get_azure_text_credentials() -> tuple[str, str]:
    """Obtém credenciais do Azure Text Analytics das variáveis de ambiente.

    Returns:
        Tupla de (endpoint, key)

    Raises:
        AzureConfigurationError: Se as credenciais não estiverem configuradas
    """
    endpoint = os.getenv("AZURE_TEXT_ENDPOINT")
    key = os.getenv("AZURE_TEXT_KEY")

    if not endpoint or not key:
        raise AzureConfigurationError(
            "Credenciais do Azure Text Analytics não configuradas. "
            "Configure as variáveis de ambiente AZURE_TEXT_ENDPOINT e AZURE_TEXT_KEY."
        )

    # Valida formato do endpoint (permite http:// em dev para mocks)
    if not endpoint.startswith(("https://", "http://")):
        raise AzureConfigurationError(
            f"AZURE_TEXT_ENDPOINT inválido: {endpoint}. Deve começar com http:// ou https://"
        )

    return endpoint, key


@lru_cache
def get_text_analytics_client() -> TextAnalyticsClient:
    """Obtém cliente TextAnalyticsClient singleton com política de retry.

    Usa lru_cache para garantir que o mesmo cliente seja reutilizado entre requisições,
    melhorando performance e reduzindo overhead de conexão.

    Returns:
        Instância configurada de TextAnalyticsClient

    Raises:
        AzureConfigurationError: Se as credenciais não estiverem configuradas
    """
    endpoint, key = get_azure_text_credentials()

    # Configura política de retry
    retry_policy = RetryPolicy(
        retry_total=3,
        retry_connect=3,
        retry_read=3,
        retry_status=3,
        backoff_factor=0.3,
        status_forcelist=[500, 502, 503, 504],
    )

    credential = AzureKeyCredential(key)
    client = TextAnalyticsClient(
        endpoint=endpoint,
        credential=credential,
        retry_policy=retry_policy,
    )

    return client


T = TypeVar("T")

def safe_azure_call(func: Callable[..., T], *args: Any, **kwargs: Any) -> T:
    """Wrapper para chamadas seguras à API Azure com tratamento de erros.

    Args:
        func: Função do SDK Azure para chamar
        *args: Argumentos posicionais
        **kwargs: Argumentos nomeados

    Returns:
        Resultado da função do SDK Azure

    Raises:
        QuotaExceededError: Quando a quota Azure é excedida (HTTP 429)
        AuthenticationError: Quando a autenticação falha (HTTP 401)
        AzureServiceError: Para outros erros do serviço Azure
        AzureConnectionError: Quando a conexão falha
    """
    from azure.core.exceptions import HttpResponseError, ServiceRequestError

    try:
        return func(*args, **kwargs)
    except HttpResponseError as e:
        if e.status_code == 429:
            raise QuotaExceededError(
                "Quota do Azure excedida. Por favor, tente novamente após algum tempo."
            ) from e
        elif e.status_code == 401:
            raise AuthenticationError(
                "Autenticação Azure falhou. Verifique suas credenciais."
            ) from e
        elif e.status_code == 403:
            raise AuthenticationError(
                "Autorização Azure falhou. Verifique suas permissões."
            ) from e
        else:
            raise AzureServiceError(
                f"Erro no serviço Azure: {e.message} (Status: {e.status_code})"
            ) from e
    except ServiceRequestError as e:
        raise AzureConnectionError(
            f"Falha ao conectar ao serviço Azure: {e}"
        ) from e
