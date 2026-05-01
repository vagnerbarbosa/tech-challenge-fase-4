"""Testes unitários para Azure AI Content Safety client."""

from unittest.mock import Mock, patch

import pytest
import requests

from src.infrastructure.azure_clients import (
    AuthenticationError,
    AzureConfigurationError,
    AzureConnectionError,
    QuotaExceededError,
)
from src.infrastructure.content_safety_client import (
    ContentSafetyClient,
    ContentSafetyResult,
    get_content_safety_client,
)


class TestContentSafetyResult:
    """Testes para ContentSafetyResult dataclass."""

    def test_is_harmful_with_high_severity(self):
        """Deve retornar True quando severidade é alta."""
        result = ContentSafetyResult(
            self_harm_severity=5,
            violence_severity=0,
            hate_severity=0,
            sexual_severity=0,
        )
        assert result.is_harmful is True

    def test_is_harmful_with_low_severity(self):
        """Deve retornar False quando severidade é baixa."""
        result = ContentSafetyResult(
            self_harm_severity=2,
            violence_severity=1,
            hate_severity=0,
            sexual_severity=0,
        )
        assert result.is_harmful is False

    def test_highest_category_self_harm(self):
        """Deve retornar SelfHarm como categoria mais alta."""
        result = ContentSafetyResult(
            self_harm_severity=6,
            violence_severity=3,
            hate_severity=1,
            sexual_severity=0,
        )
        assert result.highest_category == "SelfHarm"
        assert result.highest_severity == 6

    def test_highest_category_violence(self):
        """Deve retornar Violence como categoria mais alta."""
        result = ContentSafetyResult(
            self_harm_severity=0,
            violence_severity=5,
            hate_severity=2,
            sexual_severity=1,
        )
        assert result.highest_category == "Violence"

    def test_to_dict(self):
        """Deve converter resultado para dicionário."""
        result = ContentSafetyResult(
            self_harm_severity=4,
            violence_severity=2,
            hate_severity=1,
            sexual_severity=0,
        )
        data = result.to_dict()
        assert data["self_harm_severity"] == 4
        assert data["violence_severity"] == 2
        assert data["hate_severity"] == 1
        assert data["sexual_severity"] == 0
        assert data["is_harmful"] is True
        assert data["highest_category"] == "SelfHarm"
        assert data["highest_severity"] == 4


class TestContentSafetyClient:
    """Testes para ContentSafetyClient."""

    def test_init_missing_credentials(self):
        """Deve levantar erro quando credenciais estão ausentes."""
        with pytest.raises(AzureConfigurationError):
            ContentSafetyClient(endpoint=None, key=None)

    def test_init_with_explicit_credentials(self):
        """Deve inicializar com credenciais explícitas."""
        client = ContentSafetyClient(
            endpoint="https://test.cognitiveservices.azure.com",
            key="test-key",
        )
        assert client.endpoint == "https://test.cognitiveservices.azure.com"

    def test_init_with_env_variables(self, monkeypatch):
        """Deve inicializar com variáveis de ambiente."""
        monkeypatch.setenv("AZURE_CONTENT_SAFETY_ENDPOINT", "https://env.cognitiveservices.azure.com")
        monkeypatch.setenv("AZURE_CONTENT_SAFETY_KEY", "env-key")

        client = ContentSafetyClient()
        assert client.endpoint == "https://env.cognitiveservices.azure.com"

    def test_init_removes_trailing_slash(self):
        """Deve remover trailing slash do endpoint."""
        client = ContentSafetyClient(
            endpoint="https://test.cognitiveservices.azure.com/",
            key="test-key",
        )
        assert client.endpoint == "https://test.cognitiveservices.azure.com"

    @patch("src.infrastructure.content_safety_client.requests.post")
    def test_analyze_text_success(self, mock_post):
        """Deve analisar texto com sucesso."""
        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
            "categoriesAnalysis": [
                {"category": "SelfHarm", "severity": 5},
                {"category": "Violence", "severity": 2},
                {"category": "Hate", "severity": 0},
                {"category": "Sexual", "severity": 0},
            ]
        }
        mock_response.raise_for_status = Mock()
        mock_post.return_value = mock_response

        client = ContentSafetyClient(
            endpoint="https://test.cognitiveservices.azure.com",
            key="test-key",
        )
        result = client.analyze_text("I want to hurt myself")

        assert result.self_harm_severity == 5
        assert result.violence_severity == 2
        assert result.hate_severity == 0
        assert result.sexual_severity == 0

    @patch("src.infrastructure.content_safety_client.requests.post")
    def test_analyze_text_quota_exceeded(self, mock_post):
        """Deve levantar QuotaExceededError em 429."""
        mock_response = Mock()
        mock_response.status_code = 429
        mock_response.raise_for_status.side_effect = requests.exceptions.HTTPError(response=mock_response)
        mock_post.return_value = mock_response

        client = ContentSafetyClient(
            endpoint="https://test.cognitiveservices.azure.com",
            key="test-key",
        )

        with pytest.raises(QuotaExceededError):
            client.analyze_text("test text")

    @patch("src.infrastructure.content_safety_client.requests.post")
    def test_analyze_text_authentication_error(self, mock_post):
        """Deve levantar AuthenticationError em 401/403."""
        mock_response = Mock()
        mock_response.status_code = 401
        mock_response.raise_for_status.side_effect = requests.exceptions.HTTPError(response=mock_response)
        mock_post.return_value = mock_response

        client = ContentSafetyClient(
            endpoint="https://test.cognitiveservices.azure.com",
            key="test-key",
        )

        with pytest.raises(AuthenticationError):
            client.analyze_text("test text")

    @patch("src.infrastructure.content_safety_client.requests.post")
    def test_analyze_text_connection_error(self, mock_post):
        """Deve levantar AzureConnectionError em falha de conexão."""
        mock_post.side_effect = requests.exceptions.ConnectionError("Connection failed")

        client = ContentSafetyClient(
            endpoint="https://test.cognitiveservices.azure.com",
            key="test-key",
        )

        with pytest.raises(AzureConnectionError):
            client.analyze_text("test text")

    @patch("src.infrastructure.content_safety_client.requests.post")
    def test_analyze_text_custom_categories(self, mock_post):
        """Deve aceitar categorias customizadas."""
        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
            "categoriesAnalysis": [
                {"category": "SelfHarm", "severity": 3},
            ]
        }
        mock_response.raise_for_status = Mock()
        mock_post.return_value = mock_response

        client = ContentSafetyClient(
            endpoint="https://test.cognitiveservices.azure.com",
            key="test-key",
        )
        result = client.analyze_text(
            "test text",
            categories=["SelfHarm"],
        )

        assert result.self_harm_severity == 3

    def test_analyze_batch(self):
        """Deve analisar múltiplos textos."""
        client = ContentSafetyClient(
            endpoint="https://test.cognitiveservices.azure.com",
            key="test-key",
        )

        with patch.object(client, "analyze_text") as mock_analyze:
            mock_analyze.return_value = ContentSafetyResult(
                self_harm_severity=2,
                violence_severity=0,
                hate_severity=0,
                sexual_severity=0,
            )

            texts = ["text 1", "text 2", "text 3"]
            results = client.analyze_batch(texts)

            assert len(results) == 3
            assert mock_analyze.call_count == 3


class TestGetContentSafetyClient:
    """Testes para função get_content_safety_client."""

    def test_returns_singleton(self, monkeypatch):
        """Deve retornar instância singleton."""
        monkeypatch.setenv("AZURE_CONTENT_SAFETY_ENDPOINT", "https://test.cognitiveservices.azure.com")
        monkeypatch.setenv("AZURE_CONTENT_SAFETY_KEY", "test-key")

        # Limpa cache
        get_content_safety_client.cache_clear()

        client1 = get_content_safety_client()
        client2 = get_content_safety_client()

        assert client1 is client2
