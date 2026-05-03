"""
Testes de edge cases para rotas de áudio.

Este módulo cobre os cenários de erro específicos do endpoint de áudio:
T009: Erro de transcrição (Azure Speech)
T010: Erro de análise prosódica (librosa)
T011: Erro de Content Safety
T012: Erro de detecção de risco
"""
import io
import struct
import wave
from unittest.mock import MagicMock, patch

from fastapi import status

from src.core.exceptions import (
    AzureServiceError,
)


class TestAudioEdgeCases:
    """Testes de edge cases para endpoints de áudio."""

    def _create_test_wav(self) -> io.BytesIO:
        """Cria um arquivo WAV em memória para testes."""
        buffer = io.BytesIO()
        with wave.open(buffer, 'w') as wav_file:
            wav_file.setnchannels(1)
            wav_file.setsampwidth(2)
            wav_file.setframerate(16000)
            # 1 segundo de silêncio
            samples = [0] * 16000
            wav_file.writeframes(struct.pack('<' + 'h' * len(samples), *samples))
        buffer.seek(0)
        buffer.name = "test_audio.wav"
        return buffer

    def test_audio_transcription_error(self, client):
        """Testa erro quando transcrição falha (AzureServiceError).

        T009: Simula falha no serviço Azure Speech durante transcrição.
        Esperado: HTTP 503 Service Unavailable
        """
        # Cria arquivo WAV de teste
        audio_file = self._create_test_wav()

        # Mock do serviço de análise para lançar erro de transcrição
        with patch('src.api.routes.audio.AudioAnalysisService') as mock_service:
            mock_instance = MagicMock()
            mock_instance.analyze.side_effect = AzureServiceError(
                message="Falha na transcrição do áudio",
                service="Azure Speech"
            )
            mock_service.return_value = mock_instance

            response = client.post(
                "/analyze/audio",
                headers={"X-API-Key": "test-api-key"},
                files={"audio": ("test.wav", audio_file, "audio/wav")},
                data={"patient_id": "TEST-001"}
            )

        assert response.status_code == status.HTTP_503_SERVICE_UNAVAILABLE
        data = response.json()
        assert "transcrição" in data["detail"].lower() or "serviço" in data["detail"].lower()

    def test_audio_prosody_error(self, client):
        """Testa erro quando análise prosódica falha.

        T010: Simula falha na extração de features prosódicas via librosa.
        Esperado: HTTP 500 Internal Server Error
        """
        # Cria arquivo WAV de teste
        audio_file = self._create_test_wav()

        # Mock do serviço para lançar erro na análise prosódica
        with patch('src.api.routes.audio.AudioAnalysisService') as mock_service:
            mock_instance = MagicMock()
            mock_instance.analyze.side_effect = Exception(
                "Erro ao extrair features prosódicas: librosa load failed"
            )
            mock_service.return_value = mock_instance

            response = client.post(
                "/analyze/audio",
                headers={"X-API-Key": "test-api-key"},
                files={"audio": ("test.wav", audio_file, "audio/wav")},
                data={"patient_id": "TEST-001"}
            )

        assert response.status_code == status.HTTP_500_INTERNAL_SERVER_ERROR
        data = response.json()
        assert "erro" in data["detail"].lower() or "prosódica" in data["detail"].lower() or "interno" in data["detail"].lower()

    def test_audio_content_safety_error(self, client):
        """Testa erro quando Content Safety falha.

        T011: Simula falha no Azure Content Safety durante análise de risco.
        Esperado: HTTP 503 Service Unavailable
        """
        # Cria arquivo WAV de teste
        audio_file = self._create_test_wav()

        # Mock do serviço para lançar erro de Content Safety
        with patch('src.api.routes.audio.AudioAnalysisService') as mock_service:
            mock_instance = MagicMock()
            mock_instance.analyze.side_effect = AzureServiceError(
                message="Content Safety indisponível",
                service="Azure Content Safety",
                status_code=503
            )
            mock_service.return_value = mock_instance

            response = client.post(
                "/analyze/audio",
                headers={"X-API-Key": "test-api-key"},
                files={"audio": ("test.wav", audio_file, "audio/wav")},
                data={"patient_id": "TEST-001"}
            )

        assert response.status_code == status.HTTP_503_SERVICE_UNAVAILABLE
        data = response.json()
        assert "indisponível" in data["detail"].lower() or "serviço" in data["detail"].lower()

    def test_audio_risk_detection_error(self, client):
        """Testa erro quando detecção de risco falha.

        T012: Simula falha no cálculo de risco (risk_detector).
        Esperado: HTTP 500 Internal Server Error
        """
        # Cria arquivo WAV de teste
        audio_file = self._create_test_wav()

        # Mock do serviço para lançar erro na detecção de risco
        with patch('src.api.routes.audio.AudioAnalysisService') as mock_service:
            mock_instance = MagicMock()
            mock_instance.analyze.side_effect = Exception(
                "Erro ao calcular risk scores: division by zero"
            )
            mock_service.return_value = mock_instance

            response = client.post(
                "/analyze/audio",
                headers={"X-API-Key": "test-api-key"},
                files={"audio": ("test.wav", audio_file, "audio/wav")},
                data={"patient_id": "TEST-001"}
            )

        assert response.status_code == status.HTTP_500_INTERNAL_SERVER_ERROR
        data = response.json()
        assert "erro" in data["detail"].lower() or "interno" in data["detail"].lower()
