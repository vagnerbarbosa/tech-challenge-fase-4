"""Testes para validacao de magic bytes em arquivos.

Validacao de magic numbers (assinaturas de arquivo) para
prevencao de spoofing de tipo de arquivo.
"""

from unittest.mock import AsyncMock, Mock, patch

import pytest
from fastapi import HTTPException, UploadFile

from src.utils.file_validation import (
    validate_audio_file,
    validate_video_file,
)


class TestFileValidationMagic:
    """Testes de validacao de magic bytes."""

    def _create_mock_upload(self, filename: str, content: bytes) -> Mock:
        """Cria um UploadFile mockado com conteudo especifico."""
        upload = Mock(spec=UploadFile)
        upload.filename = filename
        upload.read = AsyncMock(return_value=content)
        upload.seek = AsyncMock()
        return upload

    def _mock_magic_module(self, mime_type: str) -> Mock:
        """Cria mock do modulo magic retornando um MIME type especifico."""
        mock_magic = Mock()
        mock_magic.from_buffer = Mock(return_value=mime_type)
        return mock_magic

    # ============= T017: WAV Validation =============
    @pytest.mark.asyncio
    async def test_validate_magic_bytes_wav(self):
        """T017: Testar validacao de magic bytes para WAV.

        Verifica que arquivo WAV com header RIFF/WAVE eh aceito.
        """
        # WAV header: RIFF....WAVEfmt - usando bytes.fromhex para evitar nulls no source
        wav_header = b"RIFF" + bytes(4) + b"WAVEfmt" + bytes(4)
        upload = self._create_mock_upload("test.wav", wav_header)

        with patch("src.utils.file_validation.magic", self._mock_magic_module("audio/wav")):
            # Nao deve lancar excecao
            await validate_audio_file(upload)

        upload.seek.assert_called_with(0)

    @pytest.mark.asyncio
    async def test_validate_magic_bytes_wav_with_fallback(self):
        """T017: Testar validacao WAV sem python-magic (fallback)."""
        # WAV header: RIFF....WAVE
        wav_header = b"RIFF" + bytes(4) + b"WAVE"
        upload = self._create_mock_upload("test.wav", wav_header)

        # Simula python-magic nao disponivel (MAGIC_AVAILABLE=False)
        with (
            patch("src.utils.file_validation.MAGIC_AVAILABLE", False),
            patch("src.utils.file_validation.magic", None),
        ):
            # Nao deve lancar excecao - usa validacao por assinatura
            await validate_audio_file(upload)

        upload.seek.assert_called_with(0)

    # ============= T018: MP3 Validation =============
    @pytest.mark.asyncio
    async def test_validate_magic_bytes_mp3(self):
        """T018: Testar validacao de magic bytes para MP3.

        Verifica que arquivo MP3 com header MPEG (0xFFE) ou ID3 eh aceito.
        """
        # MP3 header: MPEG sync (0xFF 0xFB)
        mp3_content = bytes([0xFF, 0xFB, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00])
        upload = self._create_mock_upload("test.mp3", mp3_content)

        with patch(
            "src.utils.file_validation.magic", self._mock_magic_module("audio/mpeg")
        ):
            # Nao deve lancar excecao
            await validate_audio_file(upload)

        upload.seek.assert_called_with(0)

    @pytest.mark.asyncio
    async def test_validate_magic_bytes_mp3_id3(self):
        """T018: Testar validacao MP3 com header ID3."""
        # MP3 header: ID3v2
        mp3_content = b"ID3" + bytes([0x04, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00])
        upload = self._create_mock_upload("test.mp3", mp3_content)

        with patch(
            "src.utils.file_validation.magic", self._mock_magic_module("audio/mpeg")
        ):
            await validate_audio_file(upload)

        upload.seek.assert_called_with(0)

    @pytest.mark.asyncio
    async def test_validate_magic_bytes_mp3_with_fallback(self):
        """T018: Testar validacao MP3 sem python-magic (fallback)."""
        mp3_content = bytes([0xFF, 0xFB, 0x00, 0x00])  # MPEG sync
        upload = self._create_mock_upload("test.mp3", mp3_content)

        with (
            patch("src.utils.file_validation.MAGIC_AVAILABLE", False),
            patch("src.utils.file_validation.magic", None),
        ):
            await validate_audio_file(upload)

        upload.seek.assert_called_with(0)

    # ============= T019: MP4 Validation =============
    @pytest.mark.asyncio
    async def test_validate_magic_bytes_mp4(self):
        """T019: Testar validacao de magic bytes para MP4.

        Verifica que arquivo MP4 com ftyp box eh aceito.
        """
        # MP4 header: size(4 bytes) + "ftyp" + brand - usando bytes() para nulls
        mp4_header = bytes([0x00, 0x00, 0x00, 0x18]) + b"ftypmp41" + bytes(4)
        upload = self._create_mock_upload("test.mp4", mp4_header)

        with patch(
            "src.utils.file_validation.magic", self._mock_magic_module("video/mp4")
        ):
            # Nao deve lancar excecao
            await validate_video_file(upload)

        upload.seek.assert_called_with(0)

    @pytest.mark.asyncio
    async def test_validate_magic_bytes_mp4_with_fallback(self):
        """T019: Testar validacao MP4 sem python-magic (fallback)."""
        # MP4 ftyp signature nos bytes 4-7
        mp4_header = bytes([0x00, 0x00, 0x00, 0x18]) + b"ftypmp41"
        upload = self._create_mock_upload("test.mp4", mp4_header)

        with (
            patch("src.utils.file_validation.MAGIC_AVAILABLE", False),
            patch("src.utils.file_validation.magic", None),
        ):
            await validate_video_file(upload)

        upload.seek.assert_called_with(0)

    # ============= T020: Invalid Magic Bytes =============
    @pytest.mark.asyncio
    async def test_validate_magic_bytes_invalid(self):
        """T020: Testar rejeicao de arquivo com magic bytes invalidos.

        Verifica que arquivo com assinatura incorreta eh rejeitado.
        """
        # Conteudo invalido (nao eh WAV/MP3/OGG)
        invalid_content = b"FAKEFILECONTENT12345"
        upload = self._create_mock_upload("test.wav", invalid_content)

        with patch(
            "src.utils.file_validation.magic",
            self._mock_magic_module("application/octet-stream"),
        ), pytest.raises(HTTPException) as exc_info:
            await validate_audio_file(upload)

        assert exc_info.value.status_code == 400
        assert "suportado" in exc_info.value.detail.lower()

    @pytest.mark.asyncio
    async def test_validate_magic_bytes_invalid_with_fallback(self):
        """T020: Testar rejeicao no fallback (assinatura invalida)."""
        # Conteudo que nao corresponde a assinatura esperada
        invalid_content = b"FAKEWAVC"
        upload = self._create_mock_upload("test.wav", invalid_content)

        with (
            patch("src.utils.file_validation.MAGIC_AVAILABLE", False),
            patch("src.utils.file_validation.magic", None),
            pytest.raises(HTTPException) as exc_info,
        ):
            await validate_audio_file(upload)

        assert exc_info.value.status_code == 400
        assert "assinatura" in exc_info.value.detail.lower()

    @pytest.mark.asyncio
    async def test_validate_magic_bytes_video_invalid(self):
        """T020: Testar rejeicao de video com magic bytes invalidos."""
        invalid_content = b"FAKEVIDEOCONTENT1234"
        upload = self._create_mock_upload("test.mp4", invalid_content)

        with patch(
            "src.utils.file_validation.magic", self._mock_magic_module("text/plain")
        ), pytest.raises(HTTPException) as exc_info:
            await validate_video_file(upload)

        assert exc_info.value.status_code == 400

    @pytest.mark.asyncio
    async def test_validate_magic_bytes_mismatch_extension(self):
        """T020: Testar mismatch entre extensao e conteudo (WAV com conteudo MP3).

        Quando MIME eh valido mas extensao nao corresponde, apenas loga warning.
        """
        # Arquivo .wav com conteudo MP3 (MIME audio/mpeg, extensao .wav)
        mp3_content = bytes([0xFF, 0xFB, 0x00, 0x00])
        upload = self._create_mock_upload("test.wav", mp3_content)

        with patch(
            "src.utils.file_validation.magic", self._mock_magic_module("audio/mpeg")
        ):
            # Nao lanca excecao, apenas loga warning
            await validate_audio_file(upload)

        # Verifica que seek foi chamado (validacao passou)
        upload.seek.assert_called_with(0)

    # ============= T021: Error Reading Magic Bytes =============
    @pytest.mark.asyncio
    async def test_validate_magic_bytes_error(self):
        """T021: Testar erro ao ler magic bytes.

        Verifica comportamento quando a leitura do arquivo falha.
        """
        upload = Mock(spec=UploadFile)
        upload.filename = "test.wav"
        upload.read = AsyncMock(side_effect=OSError("Erro de leitura"))
        upload.seek = AsyncMock()

        with (
            patch("src.utils.file_validation.magic", self._mock_magic_module("audio/wav")),
            pytest.raises(IOError) as exc_info,
        ):
            await validate_audio_file(upload)

        assert "leitura" in str(exc_info.value).lower() or "Erro" in str(exc_info.value)

    @pytest.mark.asyncio
    async def test_validate_magic_bytes_error_on_seek(self):
        """T021: Testar erro ao fazer seek apos leitura."""
        wav_header = b"RIFF" + bytes(4) + b"WAVE"
        upload = Mock(spec=UploadFile)
        upload.filename = "test.wav"
        upload.read = AsyncMock(return_value=wav_header)
        upload.seek = AsyncMock(side_effect=OSError("Erro de seek"))

        with (
            patch("src.utils.file_validation.magic", self._mock_magic_module("audio/wav")),
            pytest.raises(IOError) as exc_info,
        ):
            await validate_audio_file(upload)

        assert "seek" in str(exc_info.value).lower() or "Erro" in str(exc_info.value)

    @pytest.mark.asyncio
    async def test_validate_magic_bytes_empty_content(self):
        """T021: Testar comportamento com conteudo vazio (edge case).

        Com conteudo vazio, a validacao de assinatura nao rejeita (len=0),
        permitindo que passe no fallback.
        """
        upload = self._create_mock_upload("test.wav", b"")

        with (
            patch("src.utils.file_validation.MAGIC_AVAILABLE", False),
            patch("src.utils.file_validation.magic", None),
        ):
            # Com conteudo vazio, nao levanta excecao (is_valid=False mas len=0)
            await validate_audio_file(upload)

        # Verifica que seek foi chamado
        upload.seek.assert_called_with(0)

    @pytest.mark.asyncio
    async def test_validate_magic_bytes_video_error(self):
        """T021: Testar erro ao ler magic bytes em video."""
        upload = Mock(spec=UploadFile)
        upload.filename = "test.mp4"
        upload.read = AsyncMock(side_effect=OSError("Erro de leitura de video"))
        upload.seek = AsyncMock()

        with pytest.raises(IOError):
            await validate_video_file(upload)


class TestFileValidationMagicExtended:
    """Testes adicionais para cobertura de casos edge."""

    @pytest.mark.asyncio
    async def test_ogg_validation_magic(self):
        """Testar validacao OGG com magic bytes."""
        ogg_content = b"OggS" + bytes(8)
        upload = Mock(spec=UploadFile)
        upload.filename = "test.ogg"
        upload.read = AsyncMock(return_value=ogg_content)
        upload.seek = AsyncMock()

        mock_magic = Mock()
        mock_magic.from_buffer = Mock(return_value="audio/ogg")

        with patch("src.utils.file_validation.magic", mock_magic):
            await validate_audio_file(upload)

        upload.seek.assert_called_with(0)

    @pytest.mark.asyncio
    async def test_avi_validation_fallback(self):
        """Testar validacao AVI via fallback (RIFF header)."""
        # AVI eh RIFF....AVI
        avi_header = b"RIFF" + bytes(4) + b"AVI "
        upload = Mock(spec=UploadFile)
        upload.filename = "test.avi"
        upload.read = AsyncMock(return_value=avi_header)
        upload.seek = AsyncMock()

        with (
            patch("src.utils.file_validation.MAGIC_AVAILABLE", False),
            patch("src.utils.file_validation.magic", None),
        ):
            await validate_video_file(upload)

    @pytest.mark.asyncio
    async def test_mov_validation_fallback(self):
        """Testar validacao MOV via fallback (ftyp)."""
        # MOV usa ftyp nos bytes 4-7
        mov_header = bytes([0x00, 0x00, 0x00, 0x14]) + b"ftypqt  "
        upload = Mock(spec=UploadFile)
        upload.filename = "test.mov"
        upload.read = AsyncMock(return_value=mov_header)
        upload.seek = AsyncMock()

        with (
            patch("src.utils.file_validation.MAGIC_AVAILABLE", False),
            patch("src.utils.file_validation.magic", None),
        ):
            await validate_video_file(upload)

    @pytest.mark.asyncio
    async def test_extension_mime_mismatch_logged(self):
        """Testar que mismatch entre extensao e MIME gera log."""
        # Arquivo .wav com conteudo/texto
        fake_content = b"text content"
        upload = Mock(spec=UploadFile)
        upload.filename = "test.wav"
        upload.read = AsyncMock(return_value=fake_content)
        upload.seek = AsyncMock()

        mock_magic = Mock()
        mock_magic.from_buffer = Mock(return_value="text/plain")

        with (
            patch("src.utils.file_validation.magic", mock_magic),
            pytest.raises(HTTPException) as exc_info,
        ):
            await validate_audio_file(upload)

        assert exc_info.value.status_code == 400
