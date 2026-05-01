"""Serviço de detecção de risco multilíngue usando Azure Content Safety.

Este serviço combina análise de palavras-chave (fallback) com Azure AI Content Safety
para detecção robusta de risco em múltiplos idiomas.
"""

import logging
from typing import Any

from src.core.config import settings
from src.infrastructure.azure_clients import (
    AzureClientError,
)
from src.infrastructure.content_safety_client import (
    ContentSafetyClient,
    ContentSafetyResult,
)

logger = logging.getLogger(__name__)


class RiskAssessmentResult:
    """Resultado combinado da avaliação de risco.

    Combina análise de Content Safety (multilíngue) com
    palavras-chave (português/inglês).
    """

    def __init__(
        self,
        violence_risk: float,
        mental_health_risk: float,
        content_safety: ContentSafetyResult | None = None,
        keywords_detected: list[str] | None = None,
    ):
        self.violence_risk = violence_risk
        self.mental_health_risk = mental_health_risk
        self.content_safety = content_safety
        self.keywords_detected = keywords_detected or []

    @property
    def overall_risk(self) -> float:
        """Calcula risco geral combinando todos os fatores."""
        # Content Safety tem peso maior pois é mais preciso
        if self.content_safety:
            cs_violence = min(self.content_safety.violence_severity / 6, 1.0)
            cs_self_harm = min(self.content_safety.self_harm_severity / 6, 1.0)

            # Máximo entre Content Safety e keywords
            violence = max(self.violence_risk, cs_violence)
            mental = max(self.mental_health_risk, cs_self_harm)

            return max(violence, mental)

        return max(self.violence_risk, self.mental_health_risk)

    @property
    def risk_level(self) -> str:
        """Retorna nível de risco em string."""
        risk = self.overall_risk
        if risk >= 0.8:
            return "critical"
        elif risk >= 0.6:
            return "high"
        elif risk >= 0.4:
            return "medium"
        elif risk >= 0.2:
            return "low"
        return "none"

    def to_dict(self) -> dict[str, Any]:
        """Converte resultado para dicionário."""
        result = {
            "violence_risk": round(self.violence_risk, 2),
            "mental_health_risk": round(self.mental_health_risk, 2),
            "overall_risk": round(self.overall_risk, 2),
            "risk_level": self.risk_level,
            "keywords_detected": self.keywords_detected,
        }

        if self.content_safety:
            result["content_safety"] = self.content_safety.to_dict()

        return result


class MultilingualRiskDetector:
    """Detector de risco multilíngue usando Content Safety + Keywords.

    Esta classe combina:
    1. Azure AI Content Safety (multilíngue, ML-based)
    2. Palavras-chave (PT/EN para fallback)

    Prioriza Content Safety quando disponível, mas mantém
    keywords como fallback e para contexto específico.
    """

    def __init__(self) -> None:
        self.content_safety_enabled = settings.content_safety_enabled
        self._cs_client: ContentSafetyClient | None = None

        if self.content_safety_enabled:
            try:
                self._cs_client = ContentSafetyClient()
                logger.info("Content Safety client inicializado")
            except Exception as e:
                logger.warning(
                    f"Falha ao inicializar Content Safety: {e}. Usando fallback de keywords",
                )
                self.content_safety_enabled = False

    def analyze_text(
        self,
        text: str,
        use_keywords: bool = True,
    ) -> RiskAssessmentResult:
        """Analisa texto para risco de violência e saúde mental.

        Args:
            text: Texto para analisar
            use_keywords: Se deve usar palavras-chave como complemento

        Returns:
            RiskAssessmentResult combinando Content Safety e keywords
        """
        # Inicializa resultados
        violence_risk = 0.0
        mental_health_risk = 0.0
        keywords_detected: list[str] = []
        cs_result: ContentSafetyResult | None = None

        # 1. Análise Content Safety (se habilitado)
        if self.content_safety_enabled and self._cs_client:
            try:
                cs_result = self._cs_client.analyze_text(text)

                # Converte severidades (0-6) para scores (0.0-1.0)
                violence_risk = cs_result.violence_severity / 6.0
                mental_health_risk = cs_result.self_harm_severity / 6.0

                logger.debug(
                    f"Content Safety: violence={cs_result.violence_severity}, self_harm={cs_result.self_harm_severity}",
                )

            except AzureClientError as e:
                logger.warning(
                    f"Content Safety failed: {e}. Fallback to keywords",
                )

        # 2. Análise por palavras-chave (fallback ou complemento)
        if use_keywords:
            from src.core.config import RISK_KEYWORDS

            text_lower = text.lower()

            # Verifica violência (PT)
            violence_keywords = [
                kw for kw in RISK_KEYWORDS.get("violencia", [])
                if kw.lower() in text_lower
            ]

            # Verifica saúde mental (PT)
            mental_keywords = [
                kw for kw in RISK_KEYWORDS.get("saude_mental", [])
                if kw.lower() in text_lower
            ]

            # Verifica violência (EN)
            violence_en_keywords = [
                kw for kw in RISK_KEYWORDS.get("violence_en", [])
                if kw.lower() in text_lower
            ]

            # Verifica saúde mental (EN)
            mental_en_keywords = [
                kw for kw in RISK_KEYWORDS.get("mental_health_en", [])
                if kw.lower() in text_lower
            ]

            # Combina todos os keywords
            all_violence = violence_keywords + violence_en_keywords
            all_mental = mental_keywords + mental_en_keywords

            # Calcula scores baseado em número de matches
            if all_violence:
                # Mais keywords = maior risco (max 1.0)
                violence_risk = max(
                    violence_risk,
                    min(len(all_violence) * 0.15, 1.0)
                )

            if all_mental:
                mental_health_risk = max(
                    mental_health_risk,
                    min(len(all_mental) * 0.1, 1.0)
                )

            keywords_detected = all_violence + all_mental

            logger.debug(
                f"Keywords: violence={len(all_violence)}, mental={len(all_mental)}",
            )

        return RiskAssessmentResult(
            violence_risk=violence_risk,
            mental_health_risk=mental_health_risk,
            content_safety=cs_result,
            keywords_detected=keywords_detected,
        )

    def analyze_batch(
        self,
        texts: list[str],
    ) -> list[RiskAssessmentResult]:
        """Analisa múltiplos textos em batch.

        Args:
            texts: Lista de textos para analisar

        Returns:
            Lista de RiskAssessmentResult
        """
        return [self.analyze_text(text) for text in texts if text.strip()]


# Singleton para uso em toda a aplicação
_risk_detector: MultilingualRiskDetector | None = None


def get_risk_detector() -> MultilingualRiskDetector:
    """Obtém detector de risco singleton."""
    global _risk_detector
    if _risk_detector is None:
        _risk_detector = MultilingualRiskDetector()
    return _risk_detector
