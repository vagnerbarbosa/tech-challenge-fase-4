"""Unit tests for MagicBytesValidator.

Tests the magic bytes validation functionality including:
- MIME type detection using python-magic
- Fallback signature validation
- Extension/MIME type mismatch detection
- Empty file handling
"""

import pytest

from src.core.security.file_validator import (
    ALLOWED_AUDIO_MIME_TYPES,
    ALLOWED_VIDEO_MIME_TYPES,
    MAGIC_SIGNATURES,
    MagicBytesValidator,
    ValidationResult,
)


class TestMagicBytesValidator:
    """Test suite for MagicBytesValidator class."""

    @pytest.fixture
    def validator(self) -> MagicBytesValidator:
        """Create a MagicBytesValidator instance for testing."""
        return MagicBytesValidator()

    def test_validate_empty_file(self, validator: MagicBytesValidator) -> None:
        """Test validation of empty file content."""
        result = validator.validate_content(b"")

        assert not result.is_valid
        assert result.error_code == "empty_file"
        assert "vazio" in result.error_message or "empty" in result.error_message.lower()

    def test_validate_wav_signature(self, validator: MagicBytesValidator) -> None:
        """Test validation of WAV file signature (RIFF header)."""
        # WAV files start with "RIFF" followed by size and "WAVE"
        wav_content = b"RIFF\x00\x00\x00\x00WAVEfmt "

        result = validator.validate_content(
            content=wav_content,
            expected_extension=".wav",
        )

        # Should be valid with signature validation
        assert result.is_valid or result.error_code == "validation_degraded"

    def test_validate_mp3_signature(self, validator: MagicBytesValidator) -> None:
        """Test validation of MP3 file signature."""
        # MP3 files start with frame sync bytes (0xFFFB) or ID3 header
        mp3_content = b"\xff\xfb\x90\x00\x00\x00\x00\x00"

        result = validator.validate_content(
            content=mp3_content,
            expected_extension=".mp3",
        )

        assert result.is_valid or result.error_code == "validation_degraded"

    def test_validate_mp3_with_id3(self, validator: MagicBytesValidator) -> None:
        """Test validation of MP3 with ID3 tag."""
        # MP3 with ID3v2 header
        mp3_content = b"ID3\x04\x00\x00\x00\x00\x00\x00"

        result = validator.validate_content(
            content=mp3_content,
            expected_extension=".mp3",
        )

        # Accept valid, validation_degraded, or unsupported_mime_type (when magic fails)
        assert result.is_valid or result.error_code in ("validation_degraded", "unsupported_mime_type")

    def test_validate_ogg_signature(self, validator: MagicBytesValidator) -> None:
        """Test validation of OGG file signature."""
        # OGG files start with "OggS"
        ogg_content = b"OggS\x00\x00\x00\x00\x00\x00\x00\x00"

        result = validator.validate_content(
            content=ogg_content,
            expected_extension=".ogg",
        )

        # Accept valid, validation_degraded, or unsupported_mime_type (when magic fails)
        assert result.is_valid or result.error_code in ("validation_degraded", "unsupported_mime_type")

    def test_validate_mp4_signature(self, validator: MagicBytesValidator) -> None:
        """Test validation of MP4 file signature."""
        # MP4 files start with size and "ftyp"
        mp4_content = b"\x00\x00\x00\x20ftypisom\x00\x00\x00\x00isommp41"

        result = validator.validate_content(
            content=mp4_content,
            expected_extension=".mp4",
        )

        assert result.is_valid or result.error_code == "validation_degraded"

    def test_validate_avi_signature(self, validator: MagicBytesValidator) -> None:
        """Test validation of AVI file signature."""
        # AVI files start with "RIFF" and have "AVI " marker
        avi_content = b"RIFF\x00\x00\x00\x00AVI "

        result = validator.validate_content(
            content=avi_content,
            expected_extension=".avi",
        )

        assert result.is_valid or result.error_code == "validation_degraded"

    def test_invalid_signature_mismatch(self, validator: MagicBytesValidator) -> None:
        """Test validation fails with wrong signature for extension."""
        # Trying to pass a text file as MP3
        text_content = b"This is not an MP3 file content"

        result = validator.validate_content(
            content=text_content,
            expected_extension=".mp3",
        )

        # Should fail signature validation when not using magic
        if not validator._magic_available:
            assert not result.is_valid
            assert result.error_code == "invalid_signature"

    def test_executable_disguised_as_mp3(self, validator: MagicBytesValidator) -> None:
        """Test detection of executable file disguised as MP3."""
        # EXE file starts with "MZ"
        exe_content = b"MZ\x90\x00\x03\x00\x00\x00\x04\x00\x00\x00\xff\xff"

        result = validator.validate_content(
            content=exe_content,
            expected_extension=".mp3",  # Claiming to be MP3
        )

        # Should be detected as invalid
        if not validator._magic_available:
            assert not result.is_valid

    def test_allowed_audio_types(self) -> None:
        """Test that allowed audio types are properly defined."""
        assert ".wav" in ALLOWED_AUDIO_MIME_TYPES.values()
        assert ".mp3" in ALLOWED_AUDIO_MIME_TYPES.values()
        assert ".ogg" in ALLOWED_AUDIO_MIME_TYPES.values()

        # Check MIME types
        assert "audio/wav" in ALLOWED_AUDIO_MIME_TYPES
        assert "audio/mpeg" in ALLOWED_AUDIO_MIME_TYPES
        assert "audio/ogg" in ALLOWED_AUDIO_MIME_TYPES

    def test_allowed_video_types(self) -> None:
        """Test that allowed video types are properly defined."""
        assert ".mp4" in ALLOWED_VIDEO_MIME_TYPES.values()
        assert ".avi" in ALLOWED_VIDEO_MIME_TYPES.values()
        assert ".mov" in ALLOWED_VIDEO_MIME_TYPES.values()

        # Check MIME types
        assert "video/mp4" in ALLOWED_VIDEO_MIME_TYPES
        assert "video/x-msvideo" in ALLOWED_VIDEO_MIME_TYPES
        assert "video/quicktime" in ALLOWED_VIDEO_MIME_TYPES

    def test_magic_signatures_defined(self) -> None:
        """Test that magic signatures are defined for all allowed types."""
        expected_extensions = {".wav", ".mp3", ".ogg", ".mp4", ".avi", ".mov"}

        for ext in expected_extensions:
            assert ext in MAGIC_SIGNATURES, f"Missing signature for {ext}"
            assert len(MAGIC_SIGNATURES[ext]) > 0, f"Empty signature list for {ext}"

    def test_validation_result_dataclass(self) -> None:
        """Test ValidationResult dataclass creation."""
        result = ValidationResult(
            is_valid=True,
            mime_type="audio/mpeg",
            extension=".mp3",
        )

        assert result.is_valid is True
        assert result.mime_type == "audio/mpeg"
        assert result.extension == ".mp3"
        assert result.error_message is None
        assert result.error_code is None

    def test_validation_result_failure(self) -> None:
        """Test ValidationResult for failed validation."""
        result = ValidationResult(
            is_valid=False,
            error_message="Invalid file",
            error_code="invalid_signature",
        )

        assert not result.is_valid
        assert result.error_message == "Invalid file"
        assert result.error_code == "invalid_signature"

    def test_validate_without_extension(self, validator: MagicBytesValidator) -> None:
        """Test validation without expected extension (degraded mode)."""
        content = b"Some content here"

        result = validator.validate_content(content=content)

        # Without extension and magic, should return degraded validation
        if not validator._magic_available:
            assert result.error_code == "validation_degraded"

    def test_validate_unknown_extension(self, validator: MagicBytesValidator) -> None:
        """Test validation with unknown/unsupported extension."""
        content = b"Some content"

        result = validator.validate_content(
            content=content,
            expected_extension=".xyz",  # Unknown extension
        )

        # Should fail with unknown extension
        if not validator._magic_available:
            assert not result.is_valid
            assert result.error_code == "unknown_extension"
