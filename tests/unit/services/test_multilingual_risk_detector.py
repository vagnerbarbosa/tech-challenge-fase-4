"""Testes unitários para Multilingual Risk Detector."""

from unittest.mock import Mock, patch, MagicMock

import pytest

from src.services.multilingual_risk_detector import (
    MultilingualRiskDetector,
    RiskAssessmentResult,
    get_risk_detector,
)
from src.infrastructure.content_safety_client import ContentSafetyResult


class TestRiskAssessmentResult:
    """Testes para RiskAssessmentResult."""

    def test_overall_risk_with_content_safety(self):
        """Deve calcular risco geral combinando Content Safety."""
        cs_result = ContentSafetyResult(
            self_harm_severity=6,
            violence_severity=3,
            hate_severity=0,
            sexual_severity=0,
        )
        result = RiskAssessmentResult(
            violence_risk=0.2,
            mental_health_risk=0.3,
            content_safety=cs_result,
            keywords_detected=[],
        )

        # CS self_harm: 6/6 = 1.0, CS violence: 3/6 = 0.5
        # max(0.2, 0.5) = 0.5 for violence
        # max(0.3, 1.0) = 1.0 for mental
        # max(0.5, 1.0) = 1.0 overall
        assert result.overall_risk == 1.0

    def test_overall_risk_without_content_safety(self):
        """Deve calcular risco geral usando apenas keywords."""
        result = RiskAssessmentResult(
            violence_risk=0.7,
            mental_health_risk=0.5,
            content_safety=None,
            keywords_detected=["hit", "hurt"],
        )

        assert result.overall_risk == 0.7

    def test_risk_level_critical(self):
        """Deve retornar nível critical."""
        result = RiskAssessmentResult(
            violence_risk=0.9,
            mental_health_risk=0.8,
            content_safety=None,
            keywords_detected=[],
        )
        assert result.risk_level == "critical"

    def test_risk_level_high(self):
        """Deve retornar nível high."""
        result = RiskAssessmentResult(
            violence_risk=0.7,
            mental_health_risk=0.5,
            content_safety=None,
            keywords_detected=[],
        )
        assert result.risk_level == "high"

    def test_risk_level_medium(self):
        """Deve retornar nível medium."""
        result = RiskAssessmentResult(
            violence_risk=0.5,
            mental_health_risk=0.3,
            content_safety=None,
            keywords_detected=[],
        )
        assert result.risk_level == "medium"

    def test_risk_level_low(self):
        """Deve retornar nível low."""
        result = RiskAssessmentResult(
            violence_risk=0.3,
            mental_health_risk=0.1,
            content_safety=None,
            keywords_detected=[],
        )
        assert result.risk_level == "low"

    def test_risk_level_none(self):
        """Deve retornar nível none."""
        result = RiskAssessmentResult(
            violence_risk=0.0,
            mental_health_risk=0.1,
            content_safety=None,
            keywords_detected=[],
        )
        assert result.risk_level == "none"

    def test_to_dict(self):
        """Deve converter para dicionário."""
        cs_result = ContentSafetyResult(
            self_harm_severity=4,
            violence_severity=2,
            hate_severity=0,
            sexual_severity=0,
        )
        result = RiskAssessmentResult(
            violence_risk=0.5,
            mental_health_risk=0.7,
            content_safety=cs_result,
            keywords_detected=["kill myself", "hurt"],
        )

        data = result.to_dict()
        assert data["violence_risk"] == 0.5
        assert data["mental_health_risk"] == 0.7
        assert data["overall_risk"] == 0.7
        assert data["risk_level"] == "high"
        assert data["keywords_detected"] == ["kill myself", "hurt"]
        assert "content_safety" in data


class TestMultilingualRiskDetector:
    """Testes para MultilingualRiskDetector."""

    @patch("src.services.multilingual_risk_detector.settings")
    def test_init_with_content_safety_disabled(self, mock_settings):
        """Deve inicializar com Content Safety desabilitado."""
        mock_settings.content_safety_enabled = False

        detector = MultilingualRiskDetector()
        assert detector.content_safety_enabled is False
        assert detector._cs_client is None

    @patch("src.services.multilingual_risk_detector.settings")
    def test_init_with_content_safety_enabled(self, mock_settings):
        """Deve inicializar com Content Safety habilitado."""
        mock_settings.content_safety_enabled = True

        with patch.object(
            MultilingualRiskDetector,
            "__init__",
            lambda self: setattr(self, "content_safety_enabled", True),
        ):
            detector = MultilingualRiskDetector()
            assert detector.content_safety_enabled is True

    @patch("src.services.multilingual_risk_detector.settings")
    def test_analyze_text_with_content_safety(self, mock_settings):
        """Deve usar Content Safety quando habilitado."""
        mock_settings.content_safety_enabled = False

        detector = MultilingualRiskDetector()
        detector.content_safety_enabled = True
        detector._cs_client = Mock()
        detector._cs_client.analyze_text.return_value = ContentSafetyResult(
            self_harm_severity=6,
            violence_severity=2,
            hate_severity=0,
            sexual_severity=0,
        )

        result = detector.analyze_text("I want to end my life")

        assert result.content_safety is not None
        assert result.content_safety.self_harm_severity == 6
        detector._cs_client.analyze_text.assert_called_once()

    @patch("src.services.multilingual_risk_detector.settings")
    def test_analyze_text_with_keywords_only(self, mock_settings):
        """Deve usar apenas keywords quando Content Safety desabilitado."""
        mock_settings.content_safety_enabled = False

        detector = MultilingualRiskDetector()
        result = detector.analyze_text("Estou com muita ansiedade e depressão")

        # Deve detectar keywords em português
        assert len(result.keywords_detected) > 0
        assert result.content_safety is None

    @patch("src.services.multilingual_risk_detector.settings")
    def test_analyze_text_english_keywords(self, mock_settings):
        """Deve detectar keywords em inglês."""
        mock_settings.content_safety_enabled = False

        detector = MultilingualRiskDetector()
        result = detector.analyze_text("I have anxiety and depression")

        assert len(result.keywords_detected) > 0

    @patch("src.services.multilingual_risk_detector.settings")
    def test_analyze_text_violence_keywords(self, mock_settings):
        """Deve detectar keywords de violência."""
        mock_settings.content_safety_enabled = False

        detector = MultilingualRiskDetector()
        result = detector.analyze_text("He hit me and I am afraid")

        assert result.violence_risk > 0
        assert len(result.keywords_detected) > 0

    @patch("src.services.multilingual_risk_detector.settings")
    def test_analyze_text_no_risk(self, mock_settings):
        """Deve retornar baixo risco para texto neutro."""
        mock_settings.content_safety_enabled = False

        detector = MultilingualRiskDetector()
        result = detector.analyze_text("Hoje está um dia bonito e ensolarado")

        assert result.violence_risk == 0.0
        assert result.mental_health_risk == 0.0
        assert result.overall_risk == 0.0
        assert result.risk_level == "none"

    @patch("src.services.multilingual_risk_detector.settings")
    def test_analyze_text_content_safety_failure(self, mock_settings):
        """Deve fazer fallback para keywords quando CS falha."""
        mock_settings.content_safety_enabled = True

        from src.infrastructure.azure_clients import AzureClientError

        detector = MultilingualRiskDetector()
        detector._cs_client = Mock()
        detector._cs_client.analyze_text.side_effect = AzureClientError("API Error")

        result = detector.analyze_text("suicidal thoughts")

        # Deve ter usado keywords como fallback
        assert len(result.keywords_detected) > 0

    @patch("src.services.multilingual_risk_detector.settings")
    def test_analyze_batch(self, mock_settings):
        """Deve analisar múltiplos textos."""
        mock_settings.content_safety_enabled = False

        detector = MultilingualRiskDetector()
        texts = [
            "Estou feliz hoje",
            "Estou triste e ansioso",
            "He hit me",
        ]

        results = detector.analyze_batch(texts)

        assert len(results) == 3
        assert results[0].risk_level == "none"  # feliz
        assert results[1].risk_level in ["low", "medium"]  # triste/ansioso
        assert results[2].risk_level in ["medium", "high"]  # violência

    @patch("src.services.multilingual_risk_detector.settings")
    def test_combined_risk_calculation(self, mock_settings):
        """Deve combinar riscos de CS e keywords."""
        mock_settings.content_safety_enabled = True

        detector = MultilingualRiskDetector()
        detector._cs_client = Mock()
        detector._cs_client.analyze_text.return_value = ContentSafetyResult(
            self_harm_severity=4,  # 4/6 = 0.67
            violence_severity=2,   # 2/6 = 0.33
            hate_severity=0,
            sexual_severity=0,
        )

        # Texto com keywords de risco
        result = detector.analyze_text("kill myself now")

        # Deve usar o máximo entre CS e keywords
        assert result.mental_health_risk >= 0.67


class TestGetRiskDetector:
    """Testes para função get_risk_detector."""

    def test_returns_singleton(self):
        """Deve retornar instância singleton."""
        # Limpa singleton
        import src.services.multilingual_risk_detector as mrd
        mrd._risk_detector = None

        detector1 = get_risk_detector()
        detector2 = get_risk_detector()

        assert detector1 is detector2
