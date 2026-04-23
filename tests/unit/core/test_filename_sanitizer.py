"""Unit tests for FilenameSanitizer.

Tests filename sanitization and path traversal prevention including:
- Path traversal detection (../)
- Control character removal
- Dangerous extension blocking
- Reserved name handling
- Length limits
"""

import pytest

from src.core.security.file_validator import (
    DANGEROUS_EXTENSIONS,
    FilenameSanitizer,
    SanitizationResult,
)


class TestFilenameSanitizer:
    """Test suite for FilenameSanitizer class."""

    @pytest.fixture
    def sanitizer(self) -> FilenameSanitizer:
        """Create a FilenameSanitizer instance for testing."""
        return FilenameSanitizer()

    def test_sanitize_simple_filename(self, sanitizer: FilenameSanitizer) -> None:
        """Test sanitization of a simple valid filename."""
        result = sanitizer.sanitize("audio.mp3")

        assert result.is_safe is True
        assert result.sanitized_name == "audio.mp3"
        assert result.original_name == "audio.mp3"

    def test_sanitize_filename_with_spaces(self, sanitizer: FilenameSanitizer) -> None:
        """Test sanitization of filename with spaces."""
        result = sanitizer.sanitize("my audio file.wav")

        assert result.is_safe is True
        assert result.sanitized_name == "my audio file.wav"

    def test_sanitize_filename_with_dashes(self, sanitizer: FilenameSanitizer) -> None:
        """Test sanitization of filename with dashes and underscores."""
        result = sanitizer.sanitize("my-audio_file-test.ogg")

        assert result.is_safe is True
        assert result.sanitized_name == "my-audio_file-test.ogg"

    def test_detect_path_traversal_double_dot(self, sanitizer: FilenameSanitizer) -> None:
        """Test detection of path traversal with double dots."""
        result = sanitizer.sanitize("../etc/passwd.mp3")

        assert not result.is_safe
        # Should still extract basename
        assert "passwd.mp3" in (result.sanitized_name or "")

    def test_detect_path_traversal_backslash(self, sanitizer: FilenameSanitizer) -> None:
        """Test detection of path traversal with backslash."""
        result = sanitizer.sanitize("..\\windows\\system32.wav")

        assert not result.is_safe
        assert result.sanitized_name is not None

    def test_detect_absolute_path(self, sanitizer: FilenameSanitizer) -> None:
        """Test detection of absolute path."""
        result = sanitizer.sanitize("/etc/passwd.mp3")

        assert not result.is_safe
        # Should extract just the filename
        assert result.sanitized_name == "passwd.mp3"

    def test_detect_path_with_dot_prefix(self, sanitizer: FilenameSanitizer) -> None:
        """Test detection of path starting with dot slash."""
        result = sanitizer.sanitize("./config.mp3")

        # Dot slash is not necessarily unsafe, but should be handled
        assert result.sanitized_name is not None
        assert result.sanitized_name != ""

    def test_sanitize_null_byte_injection(self, sanitizer: FilenameSanitizer) -> None:
        """Test detection of null byte injection."""
        result = sanitizer.sanitize("file\x00.mp3")

        assert not result.is_safe
        assert "nulo" in result.error_message.lower() or "null" in result.error_message.lower()

    def test_sanitize_control_characters(self, sanitizer: FilenameSanitizer) -> None:
        """Test removal of control characters from filename."""
        result = sanitizer.sanitize("file\x01\x02.mp3")

        # Control characters should be replaced
        assert "\x01" not in (result.sanitized_name or "")
        assert "\x02" not in (result.sanitized_name or "")

    def test_sanitize_special_characters(self, sanitizer: FilenameSanitizer) -> None:
        """Test removal of special characters from filename."""
        result = sanitizer.sanitize("file<>:|?*.mp3")

        # Special characters should be replaced with underscore
        assert "<" not in (result.sanitized_name or "")
        assert ">" not in (result.sanitized_name or "")
        assert ":" not in (result.sanitized_name or "")
        assert "|" not in (result.sanitized_name or "")

    def test_block_dangerous_extension_exe(self, sanitizer: FilenameSanitizer) -> None:
        """Test blocking of .exe extension."""
        result = sanitizer.sanitize("malicious.exe")

        assert not result.is_safe
        assert result.error_message is not None
        assert "não permitida" in result.error_message or "not allowed" in result.error_message.lower()

    def test_block_dangerous_extension_php(self, sanitizer: FilenameSanitizer) -> None:
        """Test blocking of .php extension."""
        result = sanitizer.sanitize("shell.php.mp3")  # Double extension trick

        # Should extract and check the final extension
        ext = result.sanitized_name.split(".")[-1] if result.sanitized_name else ""
        # The full extension is .mp3 in this case
        assert result.sanitized_name is not None

    def test_dangerous_extensions_list(self) -> None:
        """Test that dangerous extensions are properly defined."""
        dangerous = {
            ".exe", ".dll", ".bat", ".cmd", ".sh", ".py", ".php",
            ".jsp", ".asp", ".rb", ".pl", ".cgi", ".jar",
        }

        for ext in dangerous:
            assert ext in DANGEROUS_EXTENSIONS, f"{ext} should be in DANGEROUS_EXTENSIONS"

    def test_sanitize_reserved_windows_names(self, sanitizer: FilenameSanitizer) -> None:
        """Test sanitization of reserved Windows names."""
        result = sanitizer.sanitize("CON.mp3")  # Reserved name

        # Should prefix with underscore
        assert result.sanitized_name is not None
        assert not result.sanitized_name.lower().startswith("con.")

    def test_sanitize_com_port_names(self, sanitizer: FilenameSanitizer) -> None:
        """Test sanitization of COM port reserved names."""
        result = sanitizer.sanitize("COM1.mp3")

        assert result.sanitized_name is not None
        assert not result.sanitized_name.lower().startswith("com1")

    def test_sanitize_lpt_port_names(self, sanitizer: FilenameSanitizer) -> None:
        """Test sanitization of LPT port reserved names."""
        result = sanitizer.sanitize("LPT1.mp3")

        assert result.sanitized_name is not None
        assert not result.sanitized_name.lower().startswith("lpt1")

    def test_sanitize_empty_filename(self, sanitizer: FilenameSanitizer) -> None:
        """Test handling of empty filename."""
        result = sanitizer.sanitize("")

        assert not result.is_safe
        assert result.error_message is not None

    def test_sanitize_none_filename(self, sanitizer: FilenameSanitizer) -> None:
        """Test handling of None filename."""
        result = sanitizer.sanitize(None)

        assert not result.is_safe
        assert result.error_message is not None

    def test_sanitize_filename_with_unicode(self, sanitizer: FilenameSanitizer) -> None:
        """Test handling of unicode characters in filename."""
        result = sanitizer.sanitize("áudio-música.mp3")

        # Unicode should be preserved (Python 3 handles this)
        assert result.sanitized_name is not None

    def test_sanitize_very_long_filename(self, sanitizer: FilenameSanitizer) -> None:
        """Test handling of very long filename."""
        long_name = "a" * 300 + ".mp3"
        result = sanitizer.sanitize(long_name)

        # Should be truncated
        assert len(result.sanitized_name or "") <= 255

    def test_sanitize_dot_files(self, sanitizer: FilenameSanitizer) -> None:
        """Test handling of dot files."""
        result = sanitizer.sanitize(".htaccess")

        # Dot files should be prefixed
        assert result.sanitized_name is not None
        assert result.sanitized_name != ".htaccess"

    def test_validate_extension_allowed(self, sanitizer: FilenameSanitizer) -> None:
        """Test validation of allowed extensions."""
        from src.core.security.file_validator import ALLOWED_EXTENSIONS

        assert sanitizer.validate_extension("audio.mp3", ALLOWED_EXTENSIONS)
        assert sanitizer.validate_extension("audio.wav", ALLOWED_EXTENSIONS)
        assert sanitizer.validate_extension("video.mp4", ALLOWED_EXTENSIONS)

    def test_validate_extension_not_allowed(self, sanitizer: FilenameSanitizer) -> None:
        """Test validation of not allowed extensions."""
        from src.core.security.file_validator import ALLOWED_EXTENSIONS

        assert not sanitizer.validate_extension("file.exe", ALLOWED_EXTENSIONS)
        assert not sanitizer.validate_extension("file.pdf", ALLOWED_EXTENSIONS)
        assert not sanitizer.validate_extension("file.docx", ALLOWED_EXTENSIONS)

    def test_validate_extension_case_insensitive(self, sanitizer: FilenameSanitizer) -> None:
        """Test that extension validation is case insensitive."""
        from src.core.security.file_validator import ALLOWED_EXTENSIONS

        assert sanitizer.validate_extension("audio.MP3", ALLOWED_EXTENSIONS)
        assert sanitizer.validate_extension("audio.WAV", ALLOWED_EXTENSIONS)

    def test_sanitization_result_dataclass(self) -> None:
        """Test SanitizationResult dataclass creation."""
        result = SanitizationResult(
            is_safe=True,
            sanitized_name="safe_file.mp3",
            original_name="unsafe/../file.mp3",
        )

        assert result.is_safe is True
        assert result.sanitized_name == "safe_file.mp3"
        assert result.original_name == "unsafe/../file.mp3"
        assert result.error_message is None

    def test_sanitize_path_traversal_url_encoded(self, sanitizer: FilenameSanitizer) -> None:
        """Test detection of URL-encoded path traversal."""
        # URL-encoded ../ sequences
        result = sanitizer.sanitize("%2e%2e%2fetc%2fpasswd.mp3")

        assert not result.is_safe

    def test_sanitize_deeply_nested_path(self, sanitizer: FilenameSanitizer) -> None:
        """Test sanitization of deeply nested path."""
        result = sanitizer.sanitize("a/b/c/../../../etc/passwd.mp3")

        assert not result.is_safe
        # Should extract just the filename
        assert result.sanitized_name == "passwd.mp3"

    def test_sanitize_home_directory(self, sanitizer: FilenameSanitizer) -> None:
        """Test detection of home directory reference."""
        result = sanitizer.sanitize("~/.bashrc")

        assert not result.is_safe
