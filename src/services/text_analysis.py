"""Serviço de análise de texto integrando Azure Text Analytics e detecção de risco."""

import time
import uuid
from typing import Any

from azure.ai.textanalytics import TextAnalyticsClient

from src.core.cache import get_cache
from src.infrastructure.azure_clients import (
    AuthenticationError,
    AzureConfigurationError,
    AzureConnectionError,
    AzureServiceError,
    QuotaExceededError,
    get_text_analytics_client,
    safe_azure_call,
)
from src.models.schemas import AnalysisMetadata, TextAnalysisResponse
from src.services.risk_detector import calculate_risk
from src.utils.text_utils import sanitize_text_input


class TextAnalysisError(Exception):
    """Erro na análise de texto."""

    def __init__(self, message: str, status_code: int = 500):
        self.message = message
        self.status_code = status_code
        super().__init__(message)


class TextAnalysisService:
    """Serviço para análise de texto com Azure Text Analytics.

    Este serviço integra:
    - Cache em memória para otimização
    - Azure Text Analytics para análise de sentimento
    - Detecção de risco baseada em palavras-chave
    - Logging estruturado
    """

    def __init__(self) -> None:
        """Inicializa o serviço de análise de texto."""
        self._cache = get_cache()
        self._client: TextAnalyticsClient | None = None

    def _get_client(self) -> TextAnalyticsClient:
        """Obtém cliente Azure com lazy loading."""
        if self._client is None:
            try:
                self._client = get_text_analytics_client()
            except AzureConfigurationError as e:
                raise TextAnalysisError(
                    f"Configuração Azure não encontrada: {e}",
                    status_code=503
                ) from e
        return self._client

    async def analyze(
        self, text: str, tipo: str = "geral", patient_id: str | None = None
    ) -> TextAnalysisResponse:
        """Analisa texto e retorna resultado completo.

        Fluxo:
        1. Verifica cache
        2. Sanitiza entrada
        3. Chama Azure Text Analytics
        4. Detecta riscos
        5. Armazena no cache
        6. Retorna resposta formatada

        Args:
            text: Texto para análise
            tipo: Tipo de texto (diario, prontuario, relato, geral)
            patient_id: ID anônimo do paciente (não armazenado)

        Returns:
            TextAnalysisResponse com análise completa

        Raises:
            TextAnalysisError: Se houver erro na análise
        """
        start_time = time.time()
        correlation_id = str(uuid.uuid4())[:8]
        azure_calls = 0

        # Verifica cache
        cached_result = self._cache.get(text)
        if cached_result and isinstance(cached_result, TextAnalysisResponse):
            tempo_processamento_ms = int((time.time() - start_time) * 1000)
            cached_result.metadata.correlation_id = correlation_id
            cached_result.metadata.tempo_processamento_ms = tempo_processamento_ms
            cached_result.metadata.cache_hit = True
            cached_result.metadata.azure_calls = 0
            return cached_result

        try:
            # Sanitiza entrada
            sanitized_text = sanitize_text_input(text)

            if not sanitized_text:
                raise TextAnalysisError(
                    "Texto vazio após sanitização",
                    status_code=400
                )

            # Análise Azure (com fallback para modo sem credenciais)
            sentiment_result = self._analyze_sentiment(sanitized_text)
            if sentiment_result.get("_azure_used", True):
                azure_calls += 1

            # Extrai informações do resultado Azure
            sentiment = sentiment_result.get("sentiment", "neutro")
            confidence_scores = sentiment_result.get("confidence_scores", {})

            # Calcula score geral
            score = self._calculate_sentiment_score(sentiment, confidence_scores)

            # Detecção de risco
            risk_result = calculate_risk(sanitized_text, sentiment, confidence_scores)

            # Extração simples de palavras-chave (pode ser melhorada)
            palavras_chave = self._extract_keywords(sanitized_text)

            # Calcula tempo de processamento
            tempo_processamento_ms = int((time.time() - start_time) * 1000)

            # Cria resposta
            response = TextAnalysisResponse(
                sentimento=sentiment,
                score=score,
                risco_violencia=risk_result["risco_violencia"],
                risco_saude_mental=risk_result["risco_saude_mental"],
                palavras_chave=palavras_chave,
                indicadores=risk_result["indicadores"],
                metadata=AnalysisMetadata(
                    correlation_id=correlation_id,
                    tempo_processamento_ms=tempo_processamento_ms,
                    cache_hit=False,
                    azure_calls=azure_calls,
                ),
            )

            # Armazena no cache
            self._cache.set(text, response)

            return response

        except QuotaExceededError:
            raise TextAnalysisError(
                "Limite de requisições Azure excedido. Tente novamente mais tarde.",
                status_code=429
            ) from None
        except AuthenticationError:
            raise TextAnalysisError(
                "Erro de autenticação com Azure. Verifique as credenciais.",
                status_code=503
            ) from None
        except AzureConnectionError:
            raise TextAnalysisError(
                "Não foi possível conectar ao serviço Azure. Verifique a conexão.",
                status_code=502
            ) from None
        except AzureServiceError as e:
            raise TextAnalysisError(
                f"Erro no serviço Azure: {e}",
                status_code=502
            ) from e
        except Exception as e:
            raise TextAnalysisError(
                f"Erro inesperado na análise: {e}",
                status_code=500
            ) from e

    def _analyze_sentiment(self, text: str) -> dict[str, Any]:
        """Chama Azure Text Analytics para análise de sentimento.

        Args:
            text: Texto para análise

        Returns:
            Dicionário com sentimento e scores de confiança
        """
        try:
            client = self._get_client()
        except TextAnalysisError:
            # Sem credenciais Azure, retorna análise baseada apenas em palavras-chave
            # Detecta sentimento baseado em palavras de risco
            risk_result = calculate_risk(text, "neutro", {})
            sentiment = "negativo" if risk_result["indicadores"] else "neutro"
            return {
                "sentiment": sentiment,
                "confidence_scores": {
                    "positive": 0.0,
                    "negative": 0.7 if risk_result["indicadores"] else 0.0,
                    "neutral": 0.3 if risk_result["indicadores"] else 1.0,
                },
                "_azure_used": False,
            }

        try:
            result = safe_azure_call(
                client.analyze_sentiment,
                documents=[text],
                language="pt"
            )

            if result and len(result) > 0:
                doc_result = result[0]

                # Mapeia sentimento do Azure para nosso formato
                azure_sentiment = doc_result.sentiment.lower()
                sentiment_map = {
                    "positive": "positivo",
                    "negative": "negativo",
                    "neutral": "neutro",
                    "mixed": "misto",
                }
                sentiment = sentiment_map.get(azure_sentiment, "neutro")

                # Extrai scores de confiança
                confidence_scores = {
                    "positive": getattr(doc_result.confidence_scores, "positive", 0.0),
                    "negative": getattr(doc_result.confidence_scores, "negative", 0.0),
                    "neutral": getattr(doc_result.confidence_scores, "neutral", 0.0),
                }

                return {
                    "sentiment": sentiment,
                    "confidence_scores": confidence_scores,
                    "_azure_used": True,
                }

            return {
                "sentiment": "neutro",
                "confidence_scores": {
                    "positive": 0.0,
                    "negative": 0.0,
                    "neutral": 1.0,
                },
                "_azure_used": True,
            }

        except Exception:
            # Se falhar, retorna sentimento neutro
            return {
                "sentiment": "neutro",
                "confidence_scores": {
                    "positive": 0.0,
                    "negative": 0.0,
                    "neutral": 1.0,
                },
                "_azure_used": False,
            }

    def _calculate_sentiment_score(
        self, sentiment: str, confidence_scores: dict[str, float]
    ) -> float:
        """Calcula score numérico a partir do sentimento.

        Args:
            sentiment: Tipo de sentimento
            confidence_scores: Scores de confiança

        Returns:
            Score entre -1.0 e 1.0
        """
        if sentiment == "positivo":
            return confidence_scores.get("positive", 0.5)
        elif sentiment == "negativo":
            return -confidence_scores.get("negative", 0.5)
        elif sentiment == "misto":
            # Para misto, calcula balanço
            pos = confidence_scores.get("positive", 0.0)
            neg = confidence_scores.get("negative", 0.0)
            return pos - neg
        else:
            return 0.0

    def _extract_keywords(self, text: str, max_keywords: int = 10) -> list[str]:
        """Extrai palavras-chave relevantes do texto.

        Implementação simples baseada em frequência de palavras
        relevantes (substantivos, verbos) excluindo stop words.

        Args:
            text: Texto para extração
            max_keywords: Número máximo de palavras-chave

        Returns:
            Lista de palavras-chave
        """
        # Stop words em português
        stop_words = {
            "de", "a", "o", "que", "e", "do", "da", "em", "um", "para",
            "é", "com", "não", "uma", "os", "no", "se", "na", "por", "mais",
            "as", "dos", "como", "mas", "ao", "ele", "das", "à", "seu", "sua",
            "ou", "ser", "quando", "muito", "já", "está", "também", "só",
            "pelo", "pela", "até", "isso", "ela", "entre", "depois", "sem",
            "mesmo", "aos", "seus", "quem", "nas", "me", "esse", "eles",
            "você", "essa", "num", "nem", "suas", "meu", "às", "minha",
            "têm", "numa", "pelos", "essas", "esses", "pelas", "este",
            "dele", "tu", "te", "vocês", "vos", "lhe", "lhes", "meus",
            "minhas", "teu", "tua", "teus", "tuas", "nosso", "nossa",
            "nossos", "nossas", "dela", "delas", "esta", "estes", "estas",
            "aquele", "aquela", "aqueles", "aquelas", "isto", "aquilo",
        }

        # Limpa e tokeniza
        import re
        words = re.findall(r'\b[a-zA-ZÀ-ÿ]+\b', text.lower())

        # Filtra stop words e palavras muito curtas
        filtered = [w for w in words if w not in stop_words and len(w) > 3]

        # Conta frequência
        from collections import Counter
        word_counts = Counter(filtered)

        # Retorna as mais frequentes
        most_common = word_counts.most_common(max_keywords)
        return [word for word, count in most_common]


# Instância singleton do serviço
_text_analysis_service: TextAnalysisService | None = None


def get_text_analysis_service() -> TextAnalysisService:
    """Obtém instância singleton do serviço de análise de texto.

    Returns:
        Instância de TextAnalysisService
    """
    global _text_analysis_service
    if _text_analysis_service is None:
        _text_analysis_service = TextAnalysisService()
    return _text_analysis_service
