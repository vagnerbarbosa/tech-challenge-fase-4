"""Testes para file_validation.

Validação de arquivos com magic numbers.
"""

from unittest.mock import AsyncMock, Mock, patch

import pytest
from fastapi import HTTPException

from src.utils.file_validation import (
    ALLOWED_EXTENSIONS,
    MAGIC_AVAILABLE,
    MAX_FILE_SIZE,
    check_file_size,
    validate_audio_file,
)

# Skip tests that require python-magic if not available
requires_magic = pytest.mark.skipif(
    not MAGIC_AVAILABLE,
    reason="python-magic não está disponível no ambiente"
)


class TestValidateAudioFile:
    """Test suite para validate_audio_file."""

    @pytest.fixture
    def mock_upload(self):
        """Fixture para UploadFile mockado."""
        upload = Mock()
        upload.filename = "test.wav"
        upload.read = AsyncMock()
        upload.seek = AsyncMock()
        return upload

    @requires_magic
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

    @requires_magic
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

    @requires_magic
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


class TestValidateVideoFile:
    """Test suite para validate_video_file."""

    @pytest.fixture
    def mock_video_upload(self):
        """Fixture para UploadFile de vídeo mockado."""
        upload = Mock()
        upload.filename = "test.mp4"
        upload.read = AsyncMock()
        upload.seek = AsyncMock()
        return upload

    @pytest.mark.asyncio
    async def test_invalid_video_extension_rejected(self, mock_video_upload):
        """Testa extensão de vídeo inválida rejeitada."""
        mock_video_upload.filename = "test.avi"
        mock_video_upload.read.return_value = b"fake content"

        from src.utils.file_validation import validate_video_file

        with pytest.raises(HTTPException) as exc_info:
            await validate_video_file(mock_video_upload)

        assert exc_info.value.status_code == 400

    @pytest.mark.asyncio
    async def test_valid_mp4_extension(self, mock_video_upload):
        """Testa extensão MP4 válida."""
        mock_video_upload.filename = "test.mp4"
        mock_video_upload.read.return_value = b"\x00\x00\x00\x18ftypmp4"

        from src.utils.file_validation import validate_video_file

        # Deve passar sem exceção
        await validate_video_file(mock_video_upload)


class TestCheckUploadSize:
    """Test suite para check_upload_size."""

    @pytest.mark.asyncio
    async def test_file_with_size_attribute(self):
        """Testa arquivo com atributo size disponível."""
        upload = Mock()
        upload.size = 1024  # 1KB
        upload.read = AsyncMock()
        upload.seek = AsyncMock()

        from src.utils.file_validation import check_upload_size

        # Não deve lançar exceção
        await check_upload_size(upload)

    @pytest.mark.asyncio
    async def test_file_size_none_uses_streaming(self):
        """Testa quando size é None, usa streaming."""
        upload = Mock()
        upload.size = None
        upload.read = AsyncMock(return_value=b"")  # Empty file
        upload.seek = AsyncMock()

        from src.utils.file_validation import check_upload_size

        with pytest.raises(HTTPException) as exc_info:
            await check_upload_size(upload)

        assert exc_info.value.status_code == 400


class TestCheckUploadSizeStreaming:
    """Test suite para check_upload_size_streaming."""

    @pytest.mark.asyncio
    async def test_empty_file_rejected(self):
        """Testa arquivo vazio rejeitado."""
        upload = Mock()
        upload.size = None
        upload.read = AsyncMock(return_value=b"")
        upload.seek = AsyncMock()

        from src.utils.file_validation import check_upload_size_streaming

        with pytest.raises(HTTPException) as exc_info:
            await check_upload_size_streaming(upload)

        assert exc_info.value.status_code == 400
        assert "vazio" in exc_info.value.detail.lower()

    @pytest.mark.asyncio
    async def test_large_file_rejected(self):
        """Testa arquivo muito grande rejeitado."""
        upload = Mock()
        upload.size = None
        # Simula arquivo grande
        chunks = [b"x" * 8192] * 7000  # ~57MB
        upload.read = AsyncMock(side_effect=chunks + [b""])
        upload.seek = AsyncMock()

        from src.utils.file_validation import check_upload_size_streaming

        with pytest.raises(HTTPException) as exc_info:
            await check_upload_size_streaming(upload)

        assert exc_info.value.status_code == 413
        assert "excede" in exc_info.value.detail.lower()


class TestValidateAudioFileFallback:
    """Testes para validate_audio_file sem python-magic."""

    @pytest.mark.asyncio
    async def test_wav_fallback_validation(self):
        """Testa validação WAV sem magic."""
        upload = Mock()
        upload.filename = "test.wav"
        upload.read = AsyncMock(return_value=b"RIFF\x00\x00\x00\x00WAVE")
        upload.seek = AsyncMock()

        # Deve passar sem magic
        await validate_audio_file(upload)
        upload.seek.assert_called_once_with(0)

    @pytest.mark.asyncio
    async def test_mp3_fallback_validation(self):
        """Testa validação MP3 sem magic."""
        upload = Mock()
        upload.filename = "test.mp3"
        upload.read = AsyncMock(return_value=b"\xff\xfb\x00\x00")
        upload.seek = AsyncMock()

        # Deve passar sem magic
        await validate_audio_file(upload)
        upload.seek.assert_called_once_with(0)

    @pytest.mark.asyncio
    async def test_ogg_fallback_validation(self):
        """Testa validação OGG sem magic."""
        upload = Mock()
        upload.filename = "test.ogg"
        upload.read = AsyncMock(return_value=b"OggS\x00\x00")
        upload.seek = AsyncMock()

        # Deve passar sem magic
        await validate_audio_file(upload)
        upload.seek.assert_called_once_with(0)

    @pytest.mark.asyncio
    async def test_invalid_signature_rejected(self):
        """Testa assinatura inválida rejeitada no fallback."""
        upload = Mock()
        upload.filename = "test.wav"
        upload.read = AsyncMock(return_value=b"INVALID")
        upload.seek = AsyncMock()

        with pytest.raises(HTTPException) as exc_info:
            await validate_audio_file(upload)

        assert exc_info.value.status_code == 400
        assert "assinatura" in exc_info.value.detail.lower()


class TestConstants:
    """Testes para constantes."""

    def test_allowed_extensions(self):
        """Testa extensões permitidas."""
        assert {".wav", ".mp3", ".ogg"} == ALLOWED_EXTENSIONS

    def test_max_file_size(self):
        """Testa tamanho máximo (50MB)."""
        assert MAX_FILE_SIZE == 50 * 1024 * 1024
