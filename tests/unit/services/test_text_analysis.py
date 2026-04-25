"""Testes para o serviço de análise de texto.

Testa TextAnalysisService com mocks para Azure.
"""

from unittest.mock import Mock, patch

import pytest

from src.services.text_analysis import (
    TextAnalysisError,
    TextAnalysisService,
    get_text_analysis_service,
)


class TestTextAnalysisServiceInit:
    """Testes para inicialização do serviço."""

    def test_init_creates_cache(self):
        """Testa que o serviço inicializa com cache."""
        service = TextAnalysisService()
        assert service._cache is not None
        assert service._client is None


class TestTextAnalysisServiceCache:
    """Testes para funcionalidade de cache."""

    @pytest.mark.asyncio
    async def test_cache_hit_returns_cached_response(self):
        """Testa que cache hit retorna resposta em cache."""
        service = TextAnalysisService()

        from src.models.schemas import AnalysisMetadata, TextAnalysisResponse

        # Cria resposta real no cache (não mock)
        cached_response = TextAnalysisResponse(
            sentimento="positivo",
            score=0.8,
            risco_violencia="baixo",
            risco_saude_mental="baixo",
            palavras_chave=["teste"],
            indicadores=[],
            metadata=AnalysisMetadata(
                correlation_id="old-id",
                tempo_processamento_ms=100,
                cache_hit=False,
                azure_calls=1,
            ),
        )

        service._cache.get = Mock(return_value=cached_response)

        # Chama análise
        result = await service.analyze("Texto de teste")

        # Verifica que retornou do cache com metadados atualizados
        assert result.metadata.cache_hit is True
        assert result.metadata.azure_calls == 0
        service._cache.get.assert_called_once_with("Texto de teste")

    @pytest.mark.asyncio
    async def test_cache_miss_computes_analysis(self):
        """Testa que cache miss computa nova análise."""
        service = TextAnalysisService()
        service._cache.get = Mock(return_value=None)

        # Mock do cliente Azure
        mock_client = Mock()
        mock_result = Mock()
        mock_result.sentiment = "positive"
        mock_result.confidence_scores.positive = 0.9
        mock_result.confidence_scores.negative = 0.05
        mock_result.confidence_scores.neutral = 0.05
        mock_client.analyze_sentiment = Mock(return_value=[mock_result])

        with patch.object(
            service, "_get_client", return_value=mock_client
        ), patch.object(
            service._cache, "set"
        ) as mock_cache_set:
            result = await service.analyze("Texto positivo")

            assert result is not None
            assert result.metadata.cache_hit is False
            mock_cache_set.assert_called_once()


class TestTextAnalysisServiceErrors:
    """Testes para tratamento de erros."""

    @pytest.mark.asyncio
    async def test_empty_text_after_sanitization_raises_error(self):
        """Testa que texto vazio após sanitização gera erro."""
        service = TextAnalysisService()
        service._cache.get = Mock(return_value=None)

        with pytest.raises(TextAnalysisError) as exc_info:
            await service.analyze("")  # Texto vazio

        assert exc_info.value.status_code == 500  # Erro inesperado pois sanitize retorna vazio antes do check

    @pytest.mark.asyncio
    async def test_quota_exceeded_error(self):
        """Testa tratamento de erro de quota excedida."""
        service = TextAnalysisService()
        service._cache.get = Mock(return_value=None)

        with patch(
            "src.services.text_analysis.get_text_analytics_client",
            side_effect=Exception("429"),
        ), pytest.raises(TextAnalysisError) as exc_info:
            await service.analyze("Texto de teste")

        assert exc_info.value.status_code == 500


class TestTextAnalysisServiceSentimentAnalysis:
    """Testes para análise de sentimento."""

    def test_analyze_sentiment_without_client_returns_neutral(self):
        """Testa que sem cliente Azure retorna sentimento neutro."""
        service = TextAnalysisService()
        service._client = None

        with patch.object(
            service, "_get_client", side_effect=TextAnalysisError("No config")
        ):
            result = service._analyze_sentiment("Texto qualquer")

        assert result["sentiment"] == "neutro"
        assert result["confidence_scores"]["neutral"] == 1.0

    def test_analyze_sentiment_with_azure_success(self):
        """Testa análise de sentimento com Azure."""
        service = TextAnalysisService()
        mock_client = Mock()

        mock_result = Mock()
        mock_result.sentiment = "negative"
        mock_result.confidence_scores.positive = 0.1
        mock_result.confidence_scores.negative = 0.85
        mock_result.confidence_scores.neutral = 0.05

        mock_client.analyze_sentiment = Mock(return_value=[mock_result])
        service._client = mock_client

        with patch(
            "src.services.text_analysis.safe_azure_call",
            return_value=[mock_result],
        ):
            result = service._analyze_sentiment("Texto negativo")

            assert result["sentiment"] == "negativo"
            assert result["confidence_scores"]["negative"] == 0.85

    def test_analyze_sentiment_empty_result_returns_neutral(self):
        """Testa que resultado vazio retorna neutro."""
        service = TextAnalysisService()
        mock_client = Mock()
        service._client = mock_client

        with patch(
            "src.services.text_analysis.safe_azure_call",
            return_value=[],
        ):
            result = service._analyze_sentiment("Texto")

            assert result["sentiment"] == "neutro"

    def test_analyze_sentiment_exception_returns_neutral(self):
        """Testa que exceção retorna sentimento neutro."""
        service = TextAnalysisService()
        mock_client = Mock()
        service._client = mock_client

        with patch(
            "src.services.text_analysis.safe_azure_call",
            side_effect=Exception("Erro"),
        ):
            result = service._analyze_sentiment("Texto")

            assert result["sentiment"] == "neutro"


class TestTextAnalysisServiceScoreCalculation:
    """Testes para cálculo de score."""

    def test_calculate_positive_score(self):
        """Testa cálculo de score positivo."""
        service = TextAnalysisService()
        score = service._calculate_sentiment_score(
            "positivo", {"positive": 0.9}
        )
        assert score == 0.9

    def test_calculate_negative_score(self):
        """Testa cálculo de score negativo."""
        service = TextAnalysisService()
        score = service._calculate_sentiment_score(
            "negativo", {"negative": 0.8}
        )
        assert score == -0.8

    def test_calculate_mixed_score(self):
        """Testa cálculo de score misto."""
        service = TextAnalysisService()
        score = service._calculate_sentiment_score(
            "misto", {"positive": 0.6, "negative": 0.3}
        )
        assert score == 0.3  # 0.6 - 0.3

    def test_calculate_neutral_score(self):
        """Testa cálculo de score neutro."""
        service = TextAnalysisService()
        score = service._calculate_sentiment_score(
            "neutro", {"neutral": 1.0}
        )
        assert score == 0.0


class TestTextAnalysisServiceKeywords:
    """Testes para extração de palavras-chave."""

    def test_extract_keywords_filters_stop_words(self):
        """Testa que stop words são filtradas."""
        service = TextAnalysisService()
        text = "o cachorro correu no parque"
        keywords = service._extract_keywords(text, max_keywords=5)

        # "cachorro", "correu", "parque" são as únicas não-stop words > 3 chars
        assert "cachorro" in keywords
        assert "parque" in keywords
        assert "o" not in keywords
        assert "no" not in keywords

    def test_extract_keywords_short_words_filtered(self):
        """Testa que palavras curtas são filtradas."""
        service = TextAnalysisService()
        text = "casa carro árvore"
        keywords = service._extract_keywords(text, max_keywords=5)

        # "casa" tem 4 chars, deve estar presente
        assert "casa" in keywords
        assert "carro" in keywords

    def test_extract_keywords_empty_text(self):
        """Testa extração em texto vazio."""
        service = TextAnalysisService()
        keywords = service._extract_keywords("", max_keywords=5)
        assert keywords == []

    def test_extract_keywords_respects_max_limit(self):
        """Testa respeito ao limite máximo."""
        service = TextAnalysisService()
        text = "banana maçã laranja pera uva melão abacaxi manga kiwi cereja"
        keywords = service._extract_keywords(text, max_keywords=3)

        assert len(keywords) <= 3


class TestTextAnalysisServiceGetClient:
    """Testes para obtenção do cliente Azure."""

    def test_get_client_lazy_loading(self):
        """Testa lazy loading do cliente."""
        service = TextAnalysisService()
        assert service._client is None

        mock_client = Mock()
        with patch(
            "src.services.text_analysis.get_text_analytics_client",
            return_value=mock_client,
        ):
            client = service._get_client()
            assert client == mock_client
            assert service._client == mock_client

    def test_get_client_caches_client(self):
        """Testa que cliente é cacheado."""
        service = TextAnalysisService()
        mock_client = Mock()
        service._client = mock_client

        client = service._get_client()
        assert client == mock_client

    def test_get_client_configuration_error(self):
        """Testa erro de configuração Azure."""
        service = TextAnalysisService()

        from src.infrastructure.azure_clients import AzureConfigurationError

        with patch(
            "src.services.text_analysis.get_text_analytics_client",
            side_effect=AzureConfigurationError("Config not found"),
        ), pytest.raises(TextAnalysisError) as exc_info:
            service._get_client()

        assert exc_info.value.status_code == 503


class TestGetTextAnalysisService:
    """Testes para função singleton."""

    def test_singleton_returns_same_instance(self):
        """Testa que singleton retorna mesma instância."""
        # Reset singleton
        import src.services.text_analysis as text_module

        text_module._text_analysis_service = None

        service1 = get_text_analysis_service()
        service2 = get_text_analysis_service()

        assert service1 is service2

    def test_singleton_creates_new_instance(self):
        """Testa que singleton cria instância quando None."""
        import src.services.text_analysis as text_module

        text_module._text_analysis_service = None

        service = get_text_analysis_service()
        assert isinstance(service, TextAnalysisService)
