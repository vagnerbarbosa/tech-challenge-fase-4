"""Testes para file_validation.

Validação de arquivos com magic numbers.
"""

from pathlib import Path
from unittest.mock import Mock, patch

import pytest
from fastapi import HTTPException

from src.utils.file_validation import (
    ALLOWED_EXTENSIONS,
    MAX_FILE_SIZE,
    check_file_size,
    validate_audio_file,
)


class TestValidateAudioFile:
    """Test suite para validate_audio_file."""

    @pytest.fixture
    def mock_upload(self):
        """Fixture para UploadFile mockado."""
        upload = Mock()
        upload.filename = "test.wav"
        upload.read = Mock()
        upload.seek = Mock()
        return upload

    @pytest.mark.asyncio
    async def test_valid_wav_file(self, mock_upload):
        """Testa arquivo WAV válido."""
        # Arrange - WAV header magic bytes
        mock_upload.read.return_value = b"RIFF\x00\x00\x00\x00WAVEfmt"
        mock_upload.filename = "test.wav"

        with patch("src.utils.file_validation.magic.from_buffer", return_value="audio/wav"):
            # Act & Assert (não deve lançar exceção)
            await validate_audio_file(mock_upload)

    @pytest.mark.asyncio
    async def test_invalid_extension_rejected(self, mock_upload):
        """Testa extensão inválida rejeitada."""
        # Arrange
        mock_upload.filename = "test.flac"
        mock_upload.read.return_value = b"fLaC"

        # Act & Assert
        with pytest.raises(HTTPException) as exc_info:
            await validate_audio_file(mock_upload)

        assert exc_info.value.status_code == 400
        assert "Extensão não permitida" in exc_info.value.detail

    @pytest.mark.asyncio
    async def test_invalid_mime_type_rejected(self, mock_upload):
        """Testa MIME type inválido rejeitado."""
        # Arrange
        mock_upload.filename = "test.wav"
        mock_upload.read.return_value = b"fake content"

        with patch(
            "src.utils.file_validation.magic.from_buffer", return_value="text/plain"
        ):
            # Act & Assert
            with pytest.raises(HTTPException) as exc_info:
                await validate_audio_file(mock_upload)

            assert exc_info.value.status_code == 400
            assert "Tipo de arquivo não suportado" in exc_info.value.detail

    @pytest.mark.asyncio
    async def test_seek_reset_after_validation(self, mock_upload):
        """Testa se seek(0) é chamado após leitura."""
        # Arrange
        mock_upload.filename = "test.mp3"
        mock_upload.read.return_value = b"\xff\xfb\x00\x00"  # MP3 magic

        with patch(
            "src.utils.file_validation.magic.from_buffer", return_value="audio/mpeg"
        ):
            # Act
            await validate_audio_file(mock_upload)

            # Assert
            mock_upload.seek.assert_called_once_with(0)


class TestCheckFileSize:
    """Test suite para check_file_size."""

    def test_file_within_limit_ok(self, tmp_path):
        """Testa arquivo dentro do limite."""
        # Arrange
        test_file = tmp_path / "small.wav"
        test_file.write_text("small content")

        # Act & Assert (não deve lançar exceção)
        check_file_size(test_file)

    def test_file_over_limit_rejected(self, tmp_path):
        """Testa arquivo acima do limite rejeitado."""
        # Arrange - criar arquivo > 50MB
        test_file = tmp_path / "large.wav"
        test_file.write_bytes(b"0" * (MAX_FILE_SIZE + 1))

        # Act & Assert
        with pytest.raises(HTTPException) as exc_info:
            check_file_size(test_file)

        assert exc_info.value.status_code == 400
        assert "Arquivo muito grande" in exc_info.value.detail


class TestConstants:
    """Testes para constantes."""

    def test_allowed_extensions(self):
        """Testa extensões permitidas."""
        assert ALLOWED_EXTENSIONS == {".wav", ".mp3", ".ogg"}

    def test_max_file_size(self):
        """Testa tamanho máximo (50MB)."""
        assert MAX_FILE_SIZE == 50 * 1024 * 1024
