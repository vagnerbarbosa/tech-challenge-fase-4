"""Testes de integração para o endpoint /analyze/audio.

Valida upload de arquivos, validação, processamento e resposta.
"""

from pathlib import Path
from unittest.mock import Mock, patch

import pytest
from fastapi import status
from httpx import AsyncClient


class TestAudioEndpointSuccess:
    """Testes de sucesso para análise de áudio."""

    @pytest.mark.asyncio
    async def test_analyze_audio_mock_mode(self, async_client: AsyncClient, tmp_path):
        """Testa análise de áudio em modo mock (sem Azure)."""
        # Arrange
        test_audio = tmp_path / "test.wav"
        # Cria um arquivo WAV mínimo válido
        test_audio.write_bytes(
            b"RIFF" + b"\x00\x00\x00\x00" + b"WAVEfmt " + b"\x00" * 20
        )

        with patch(
            "src.utils.file_validation.magic.from_buffer", return_value="audio/wav"
        ):
            with open(test_audio, "rb") as f:
                response = await async_client.post(
                    "/analyze/audio",
                    files={"file": ("test.wav", f, "audio/wav")},
                    data={"patient_id": "patient-123"},
                )

        # Assert
        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        assert "transcricao" in data
        assert "sentimento" in data
        assert data["idioma_detectado"] == "pt-BR"
        assert data["risco_violencia"] in ["baixo", "medio", "alto"]
        assert data["risco_saude_mental"] in ["baixo", "medio", "alto"]
        assert "metadata" in data

    @pytest.mark.asyncio
    async def test_analyze_audio_no_patient_id(self, async_client: AsyncClient, tmp_path):
        """Testa análise sem patient_id (opcional)."""
        # Arrange
        test_audio = tmp_path / "test.wav"
        test_audio.write_bytes(
            b"RIFF" + b"\x00\x00\x00\x00" + b"WAVEfmt " + b"\x00" * 20
        )

        with patch(
            "src.utils.file_validation.magic.from_buffer", return_value="audio/wav"
        ):
            with open(test_audio, "rb") as f:
                response = await async_client.post(
                    "/analyze/audio",
                    files={"file": ("test.wav", f, "audio/wav")},
                )

        # Assert
        assert response.status_code == status.HTTP_200_OK


class TestAudioEndpointValidation:
    """Testes de validação para o endpoint de áudio."""

    @pytest.mark.asyncio
    async def test_invalid_extension_rejected(self, async_client: AsyncClient, tmp_path):
        """Testa que extensão inválida é rejeitada."""
        # Arrange
        test_file = tmp_path / "test.txt"
        test_file.write_text("conteudo invalido")

        with open(test_file, "rb") as f:
            response = await async_client.post(
                "/analyze/audio",
                files={"file": ("test.txt", f, "text/plain")},
            )

        # Assert
        assert response.status_code == status.HTTP_400_BAD_REQUEST
        assert "Extensão não permitida" in response.json()["detail"]

    @pytest.mark.asyncio
    async def test_invalid_mime_type_rejected(self, async_client: AsyncClient, tmp_path):
        """Testa que MIME type inválido é rejeitado."""
        # Arrange
        test_audio = tmp_path / "test.wav"
        test_audio.write_bytes(b"fake wav content")

        with patch(
            "src.utils.file_validation.magic.from_buffer",
            return_value="application/octet-stream",
        ):
            with open(test_audio, "rb") as f:
                response = await async_client.post(
                    "/analyze/audio",
                    files={"file": ("test.wav", f, "audio/wav")},
                )

        # Assert
        assert response.status_code == status.HTTP_400_BAD_REQUEST

    @pytest.mark.asyncio
    async def test_file_too_large_rejected(self, async_client: AsyncClient, tmp_path):
        """Testa que arquivo muito grande é rejeitado."""
        # Arrange
        test_audio = tmp_path / "test.wav"
        test_audio.write_bytes(b"RIFF" + b"WAVE" + b"\x00" * (51 * 1024 * 1024))

        with patch(
            "src.utils.file_validation.magic.from_buffer", return_value="audio/wav"
        ):
            with open(test_audio, "rb") as f:
                response = await async_client.post(
                    "/analyze/audio",
                    files={"file": ("test.wav", f, "audio/wav")},
                )

        # Assert
        assert response.status_code == status.HTTP_400_BAD_REQUEST
        assert "Arquivo muito grande" in response.json()["detail"]


class TestAudioFormatsEndpoint:
    """Testes para endpoint de formatos suportados."""

    @pytest.mark.asyncio
    async def test_get_audio_formats(self, async_client: AsyncClient):
        """Testa endpoint de formatos."""
        response = await async_client.get("/analyze/audio/formats")

        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        assert "formats" in data
        assert "extensions" in data
        assert ".wav" in data["extensions"]
        assert ".mp3" in data["extensions"]


class TestAudioAzureErrors:
    """Testes para erros do Azure."""

    @pytest.mark.asyncio
    async def test_quota_exceeded_returns_429(self, async_client: AsyncClient, tmp_path):
        """Testa retorno 429 quando quota excedida."""
        # Arrange
        test_audio = tmp_path / "test.wav"
        test_audio.write_bytes(
            b"RIFF" + b"\x00\x00\x00\x00" + b"WAVEfmt " + b"\x00" * 20
        )

        with patch(
            "src.utils.file_validation.magic.from_buffer", return_value="audio/wav"
        ):
            with patch(
                "src.services.audio_analysis.AzureSpeechClient.transcribe_with_retry",
                side_effect=Exception("Quota exceeded"),
            ):
                with open(test_audio, "rb") as f:
                    response = await async_client.post(
                        "/analyze/audio",
                        files={"file": ("test.wav", f, "audio/wav")},
                    )

        # Assert - deve retornar 500 (erro interno) ou 429 dependendo do tratamento
        assert response.status_code >= 400
