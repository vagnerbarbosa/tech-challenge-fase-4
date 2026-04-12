"""Testes para AudioAnalysisService.

Valida extração de features prosódicas, integração com Azure Speech,
e análise de risco combinada.
"""

from pathlib import Path
from unittest.mock import AsyncMock, Mock, patch

import numpy as np
import pytest

from src.services.audio_analysis import (
    AudioAnalysisService,
    ProsodicFeatureExtractor,
    ProsodicFeatures,
)


class TestProsodicFeatures:
    """Testes para dataclass ProsodicFeatures."""

    def test_creation(self):
        """Testa criação de ProsodicFeatures."""
        features = ProsodicFeatures(
            voz_tremida=True,
            pausas_suspeitas=3,
            entonacao="hesitante",
            variacao_pitch=55.0,
            variacao_energia=0.12,
            duracao_segundos=45.5,
        )

        assert features.voz_tremida is True
        assert features.pausas_suspeitas == 3
        assert features.entonacao == "hesitante"
        assert features.variacao_pitch == 55.0


class TestProsodicFeatureExtractor:
    """Testes para ProsodicFeatureExtractor."""

    @pytest.fixture
    def extractor(self):
        """Fixture para ProsodicFeatureExtractor."""
        return ProsodicFeatureExtractor(sample_rate=16000)

    @pytest.mark.asyncio
    @patch("src.services.audio_analysis.librosa.load")
    @patch("src.services.audio_analysis.librosa.get_duration")
    @patch("src.services.audio_analysis.librosa.piptrack")
    @patch("src.services.audio_analysis.librosa.feature.rms")
    @patch("src.services.audio_analysis.librosa.effects.split")
    async def test_extract_normal_voice(
        self, mock_split, mock_rms, mock_piptrack, mock_duration, mock_load, extractor
    ):
        """Testa extração com voz normal (calma)."""
        # Arrange
        mock_load.return_value = (np.array([0.1, 0.2]), 16000)
        mock_duration.return_value = 10.0

        # Pitch normal (baixa variação)
        mock_piptrack.return_value = (
            np.full((100, 10), 100.0),  # pitches
            np.full((100, 10), 0.5),  # magnitudes
        )

        # Energia calma
        mock_rms.return_value = np.array([[0.03, 0.04]])

        # Poucas pausas
        mock_split.return_value = np.array([[0, 1000], [2000, 3000]])

        # Act
        result = await extractor.extract(Path("/tmp/test.wav"))

        # Assert
        assert isinstance(result, ProsodicFeatures)
        assert result.voz_tremida is False  # pitch std < 50
        assert result.entonacao == "calmo"  # mean < 0.05
        assert result.duracao_segundos == 10.0

    @pytest.mark.asyncio
    @patch("src.services.audio_analysis.librosa.load")
    @patch("src.services.audio_analysis.librosa.get_duration")
    @patch("src.services.audio_analysis.librosa.piptrack")
    @patch("src.services.audio_analysis.librosa.feature.rms")
    @patch("src.services.audio_analysis.librosa.effects.split")
    async def test_extract_trembling_voice(
        self, mock_split, mock_rms, mock_piptrack, mock_duration, mock_load, extractor
    ):
        """Testa detecção de voz tremida (alta variação de pitch)."""
        # Arrange
        mock_load.return_value = (np.array([0.1, 0.2]), 16000)
        mock_duration.return_value = 5.0

        # Pitch com alta variação (tremor) - std deve ser > 50
        # Usando valores extremos para garantir std > 50
        pitches = np.concatenate([
            np.full((50, 10), 50.0),   # Metade com valor baixo
            np.full((50, 10), 250.0),  # Metade com valor alto
        ])
        magnitudes = np.full((100, 10), 1.0)  # Magnitudes altas para serem selecionadas
        mock_piptrack.return_value = (pitches, magnitudes)

        mock_rms.return_value = np.array([[0.05, 0.06]])
        mock_split.return_value = np.array([[0, 1000]])

        # Act
        result = await extractor.extract(Path("/tmp/test.wav"))

        # Assert
        assert result.voz_tremida is True  # pitch std > 50

    @pytest.mark.asyncio
    @patch("src.services.audio_analysis.librosa.load")
    @patch("src.services.audio_analysis.librosa.get_duration")
    @patch("src.services.audio_analysis.librosa.piptrack")
    @patch("src.services.audio_analysis.librosa.feature.rms")
    @patch("src.services.audio_analysis.librosa.effects.split")
    async def test_extract_agitated_voice(
        self, mock_split, mock_rms, mock_piptrack, mock_duration, mock_load, extractor
    ):
        """Testa detecção de voz agitada (alta variação de energia)."""
        # Arrange
        mock_load.return_value = (np.array([0.1, 0.2]), 16000)
        mock_duration.return_value = 8.0

        mock_piptrack.return_value = (
            np.full((100, 10), 150.0),
            np.full((100, 10), 0.5),
        )

        # Alta variação de energia (> 0.15) - cria array com std > 0.15
        rms_values = np.zeros(100)
        rms_values[:50] = 0.01  # Metade com valor baixo
        rms_values[50:] = 0.5   # Metade com valor alto
        mock_rms.return_value = rms_values.reshape(1, -1)

        mock_split.return_value = np.array([[0, 1000]])

        # Act
        result = await extractor.extract(Path("/tmp/test.wav"))

        # Assert
        assert result.entonacao == "agitado"

    @pytest.mark.asyncio
    @patch("src.services.audio_analysis.librosa.load")
    async def test_extract_error_handling(self, mock_load, extractor):
        """Testa tratamento de erro na extração."""
        # Arrange
        mock_load.side_effect = Exception("Librosa error")

        # Act
        result = await extractor.extract(Path("/tmp/test.wav"))

        # Assert - retorna valores padrão
        assert result.voz_tremida is False
        assert result.entonacao == "normal"
        assert result.pausas_suspeitas == 0
        assert result.duracao_segundos == 0.0


class TestAudioAnalysisService:
    """Testes para AudioAnalysisService."""

    @pytest.fixture
    def service(self):
        """Fixture para AudioAnalysisService."""
        with patch(
            "src.services.audio_analysis.AzureSpeechClient"
        ) as mock_client_class:
            mock_client = Mock()
            mock_client_class.return_value = mock_client
            service = AudioAnalysisService()
            service.speech_client = mock_client
            return service

    @pytest.mark.asyncio
    @patch("src.services.audio_analysis.calculate_risk")
    @patch(
        "src.services.audio_analysis.ProsodicFeatureExtractor.extract"
    )
    async def test_analyze_success(self, mock_extract, mock_risk, service):
        """Testa análise completa bem-sucedida."""
        # Arrange
        mock_extract.return_value = ProsodicFeatures(
            voz_tremida=False,
            pausas_suspeitas=2,
            entonacao="normal",
            variacao_pitch=30.0,
            variacao_energia=0.05,
            duracao_segundos=30.0,
        )

        service.speech_client.transcribe_with_retry = AsyncMock(
            return_value={
                "transcricao": "Estou me sentindo ansiosa",
                "confiança": 0.92,
                "idioma_detectado": "pt-BR",
                "sucesso": True,
            }
        )

        mock_risk.return_value = {
            "sentimento": "negativo",
            "risco_violencia": "baixo",
            "risco_saude_mental": "medio",
        }

        # Act
        result = await service.analyze(Path("/tmp/test.wav"), "patient-123")

        # Assert
        assert result["transcricao"] == "Estou me sentindo ansiosa"
        assert result["sentimento"] == "negativo"
        assert result["risco_violencia"] == "baixo"
        assert result["risco_saude_mental"] == "medio"
        assert result["entonação"] == "normal"
        assert result["voz_tremida"] is False
        assert result["pausas_suspeitas"] == 2

    @pytest.mark.asyncio
    @patch(
        "src.services.audio_analysis.ProsodicFeatureExtractor.extract"
    )
    async def test_analyze_no_transcription(self, mock_extract, service):
        """Testa análise quando não há transcrição."""
        # Arrange
        mock_extract.return_value = ProsodicFeatures(
            voz_tremida=True,
            pausas_suspeitas=5,
            entonacao="hesitante",
            variacao_pitch=60.0,
            variacao_energia=0.1,
            duracao_segundos=45.0,
        )

        service.speech_client.transcribe_with_retry = AsyncMock(
            return_value={
                "transcricao": "",
                "confiança": 0.0,
                "idioma_detectado": "pt-BR",
                "sucesso": False,
            }
        )

        # Act
        result = await service.analyze(Path("/tmp/test.wav"))

        # Assert - risco baseado apenas em prosódia
        assert result["transcricao"] == ""
        assert result["sentimento"] == "neutro"
        assert result["risco_violencia"] == "baixo"
        assert result["risco_saude_mental"] == "baixo"
        assert result["voz_tremida"] is True

    @pytest.mark.asyncio
    @patch("src.services.audio_analysis.calculate_risk")
    @patch(
        "src.services.audio_analysis.ProsodicFeatureExtractor.extract"
    )
    async def test_analyze_risk_escalation(self, mock_extract, mock_risk, service):
        """Testa escalonamento de risco baseado em features prosódicas."""
        # Arrange
        mock_extract.return_value = ProsodicFeatures(
            voz_tremida=True,  # +1 nível
            pausas_suspeitas=8,  # +1 nível (> 5)
            entonacao="hesitante",  # +1 nível
            variacao_pitch=70.0,
            variacao_energia=0.12,
            duracao_segundos=60.0,
        )

        service.speech_client.transcribe_with_retry = AsyncMock(
            return_value={
                "transcricao": "Texto de teste",
                "confiança": 0.9,
                "idioma_detectado": "pt-BR",
                "sucesso": True,
            }
        )

        # Risco base = baixo
        mock_risk.return_value = {
            "sentimento": "negativo",
            "risco_violencia": "baixo",
            "risco_saude_mental": "baixo",
        }

        # Act
        result = await service.analyze(Path("/tmp/test.wav"))

        # Assert - risco ajustado para alto (baixo + 3 fatores = alto)
        assert result["risco_violencia"] == "alto"
        assert result["risco_saude_mental"] == "alto"

    def test_adjust_risk_increments(self, service):
        """Testa lógica de incremento de risco."""
        features = ProsodicFeatures(
            voz_tremida=True,
            pausas_suspeitas=6,
            entonacao="hesitante",
            variacao_pitch=60.0,
            variacao_energia=0.12,
            duracao_segundos=30.0,
        )

        # Testa escalonamento de baixo
        assert service._adjust_risk("baixo", features, "violencia") == "alto"
        # Testa escalonamento de medio
        assert service._adjust_risk("medio", features, "saude_mental") == "alto"
        # Testa cap em alto
        assert service._adjust_risk("alto", features, "violencia") == "alto"

    def test_adjust_risk_no_factors(self, service):
        """Testa que risco não muda sem fatores."""
        features = ProsodicFeatures(
            voz_tremida=False,
            pausas_suspeitas=2,
            entonacao="calmo",
            variacao_pitch=30.0,
            variacao_energia=0.03,
            duracao_segundos=30.0,
        )

        assert service._adjust_risk("baixo", features, "violencia") == "baixo"
        assert service._adjust_risk("medio", features, "saude_mental") == "medio"
