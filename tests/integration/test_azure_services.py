"""Testes de integração para serviços Azure."""

from unittest.mock import MagicMock, patch

import pytest
from azure.core.exceptions import HttpResponseError, ServiceRequestError

from src.infrastructure.azure_clients import (
    AuthenticationError,
    AzureConfigurationError,
    AzureConnectionError,
    AzureServiceError,
    QuotaExceededError,
    get_azure_text_credentials,
    safe_azure_call,
)


class TestAzureTextCredentials:
    """Testes para obtenção de credenciais Azure."""

    @patch.dict("os.environ", {
        "AZURE_TEXT_ENDPOINT": "https://test-resource.cognitiveservices.azure.com/",
        "AZURE_TEXT_KEY": "test-key-123",
    })
    def test_retorna_endpoint_e_key(self):
        """Deve retornar endpoint e key quando configurados."""
        endpoint, key = get_azure_text_credentials()

        assert endpoint == "https://test-resource.cognitiveservices.azure.com/"
        assert key == "test-key-123"

    @patch.dict("os.environ", {}, clear=True)
    def test_erro_quando_credenciais_ausentes(self):
        """Deve lançar erro quando credenciais não estão configuradas."""
        with pytest.raises(AzureConfigurationError) as exc_info:
            get_azure_text_credentials()

        assert "não configuradas" in str(exc_info.value)

    @patch.dict("os.environ", {
        "AZURE_TEXT_ENDPOINT": "invalid-endpoint-without-protocol.com",
        "AZURE_TEXT_KEY": "test-key",
    })
    def test_erro_quando_endpoint_invalido(self):
        """Deve lançar erro quando endpoint não começa com http:// ou https://."""
        with pytest.raises(AzureConfigurationError) as exc_info:
            get_azure_text_credentials()

        assert "inválido" in str(exc_info.value)


class TestSafeAzureCall:
    """Testes para o wrapper de chamadas seguras ao Azure."""

    def test_retorna_resultado_quando_sucesso(self):
        """Deve retornar resultado quando a chamada é bem-sucedida."""
        mock_func = MagicMock(return_value={"sentiment": "positive"})

        result = safe_azure_call(mock_func, "arg1", key="value")

        assert result == {"sentiment": "positive"}
        mock_func.assert_called_once_with("arg1", key="value")

    def test_quota_exceeded_error_429(self):
        """Deve lançar QuotaExceededError para HTTP 429."""
        error = HttpResponseError(message="Too many requests")
        error.status_code = 429
        mock_func = MagicMock(side_effect=error)

        with pytest.raises(QuotaExceededError) as exc_info:
            safe_azure_call(mock_func)

        assert "excedida" in str(exc_info.value)

    def test_authentication_error_401(self):
        """Deve lançar AuthenticationError para HTTP 401."""
        error = HttpResponseError(message="Unauthorized")
        error.status_code = 401
        mock_func = MagicMock(side_effect=error)

        with pytest.raises(AuthenticationError) as exc_info:
            safe_azure_call(mock_func)

        assert "Autenticação" in str(exc_info.value)

    def test_authentication_error_403(self):
        """Deve lançar AuthenticationError para HTTP 403."""
        error = HttpResponseError(message="Forbidden")
        error.status_code = 403
        mock_func = MagicMock(side_effect=error)

        with pytest.raises(AuthenticationError) as exc_info:
            safe_azure_call(mock_func)

        assert "Autorização" in str(exc_info.value)

    def test_azure_service_error_outros_status(self):
        """Deve lançar AzureServiceError para outros códigos HTTP."""
        error = HttpResponseError(message="Server Error")
        error.status_code = 500
        mock_func = MagicMock(side_effect=error)

        with pytest.raises(AzureServiceError) as exc_info:
            safe_azure_call(mock_func)

        assert "Erro no serviço Azure" in str(exc_info.value)

    def test_azure_connection_error(self):
        """Deve lançar AzureConnectionError para falhas de conexão."""
        mock_func = MagicMock(side_effect=ServiceRequestError("Connection failed"))

        with pytest.raises(AzureConnectionError) as exc_info:
            safe_azure_call(mock_func)

        assert "conectar" in str(exc_info.value)


class TestTextAnalyticsClient:
    """Testes para o cliente Text Analytics."""

    @patch("src.infrastructure.azure_clients.get_azure_text_credentials")
    @patch("src.infrastructure.azure_clients.TextAnalyticsClient")
    def test_cliente_criado_com_retry_policy(self, mock_client_class, mock_credentials):
        """Deve criar cliente com retry policy configurada."""
        mock_credentials.return_value = (
            "https://test.cognitiveservices.azure.com/",
            "test-key",
        )

        from src.infrastructure.azure_clients import get_text_analytics_client

        # Limpa cache para garantir nova instância
        get_text_analytics_client.cache_clear()

        client = get_text_analytics_client()

        # Verifica que o cliente foi criado
        assert client is not None
        assert mock_client_class.called
        call_kwargs = mock_client_class.call_args[1]

        assert "retry_policy" in call_kwargs
        assert call_kwargs["endpoint"] == "https://test.cognitiveservices.azure.com/"

    @patch("src.infrastructure.azure_clients.get_azure_text_credentials")
    def test_singleton_retorna_mesma_instancia(self, mock_credentials):
        """Deve retornar mesma instância (singleton)."""
        mock_credentials.return_value = (
            "https://test.cognitiveservices.azure.com/",
            "test-key",
        )

        from src.infrastructure.azure_clients import get_text_analytics_client

        # Limpa cache
        get_text_analytics_client.cache_clear()

        client1 = get_text_analytics_client()
        client2 = get_text_analytics_client()

        assert client1 is client2
