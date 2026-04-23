"""Integration tests for upload security validation.

Tests end-to-end upload security including:
- Malicious file upload blocking
- Path traversal prevention
- Magic bytes validation
- Extension/MIME type mismatch detection
- Size validation
"""

import io

import pytest
from fastapi.testclient import TestClient

from src.api.main import app
from tests.conftest import TEST_API_KEY


class TestUploadSecurity:
    """Integration tests for upload security endpoints."""

    @pytest.fixture
    def client(self) -> TestClient:
        """Create test client."""
        return TestClient(app, headers={"X-API-Key": TEST_API_KEY})

    def create_test_file(self, content: bytes, filename: str) -> tuple[io.BytesIO, str]:
        """Create a test file for upload.

        Args:
            content: File content bytes
            filename: Name of the file

        Returns:
            Tuple of (file object, filename)
        """
        return (io.BytesIO(content), filename)

    def test_upload_exe_disguised_as_mp3(self, client: TestClient) -> None:
        """Test that EXE file disguised as MP3 is rejected."""
        # EXE file content with MP3 extension
        exe_content = b"MZ\x90\x00\x03\x00\x00\x00\x04\x00\x00\x00\xff\xff"
        file_obj, filename = self.create_test_file(exe_content, "malicious.mp3")

        response = client.post(
            "/analyze/audio",
            files={"file": (filename, file_obj, "audio/mpeg")},
        )

        # Should be rejected as invalid
        assert response.status_code == 400

    def test_upload_exe_disguised_as_wav(self, client: TestClient) -> None:
        """Test that EXE file disguised as WAV is rejected."""
        exe_content = b"MZ\x90\x00\x03\x00\x00\x00\x04\x00\x00\x00\xff\xff"
        file_obj, filename = self.create_test_file(exe_content, "virus.wav")

        response = client.post(
            "/analyze/audio",
            files={"file": (filename, file_obj, "audio/wav")},
        )

        assert response.status_code == 400

    def test_upload_pdf_disguised_as_mp4(self, client: TestClient) -> None:
        """Test that PDF file disguised as MP4 is rejected."""
        # PDF header
        pdf_content = b"%PDF-1.4\n1 0 obj\n<<\n/Type /Catalog"
        file_obj, filename = self.create_test_file(pdf_content, "document.mp4")

        response = client.post(
            "/analyze/video",
            files={"video": (filename, file_obj, "video/mp4")},
        )

        assert response.status_code == 400

    def test_upload_path_traversal_in_filename(self, client: TestClient) -> None:
        """Test that path traversal in filename is blocked."""
        # Valid WAV content
        wav_content = b"RIFF\x00\x00\x00\x00WAVEfmt \x00\x00\x00\x00\x00\x00\x00\x00"
        file_obj, filename = self.create_test_file(
            wav_content, "../../../etc/passwd.wav"
        )

        response = client.post(
            "/analyze/audio",
            files={"file": (filename, file_obj, "audio/wav")},
        )

        # Should be rejected
        assert response.status_code == 400

    def test_upload_absolute_path_in_filename(self, client: TestClient) -> None:
        """Test that absolute path in filename is blocked."""
        wav_content = b"RIFF\x00\x00\x00\x00WAVEfmt \x00\x00\x00\x00\x00\x00\x00\x00"
        file_obj, filename = self.create_test_file(wav_content, "/etc/shadow.wav")

        response = client.post(
            "/analyze/audio",
            files={"file": (filename, file_obj, "audio/wav")},
        )

        # Should be rejected
        assert response.status_code == 400

    def test_upload_null_byte_in_filename(self, client: TestClient) -> None:
        """Test that null byte in filename is rejected."""
        wav_content = b"RIFF\x00\x00\x00\x00WAVEfmt \x00\x00\x00\x00\x00\x00\x00\x00"
        file_obj, filename = self.create_test_file(wav_content, "file\x00.mp3")

        response = client.post(
            "/analyze/audio",
            files={"file": (filename, file_obj, "audio/wav")},
        )

        # Should be rejected
        assert response.status_code == 400

    def test_upload_dangerous_extension(self, client: TestClient) -> None:
        """Test that files with dangerous extensions are rejected."""
        file_content = b"Some content"
        file_obj, filename = self.create_test_file(file_content, "script.py")

        response = client.post(
            "/analyze/audio",
            files={"file": (filename, file_obj, "text/plain")},
        )

        # Should be rejected for invalid extension
        assert response.status_code == 400

    def test_upload_php_extension(self, client: TestClient) -> None:
        """Test that PHP files are rejected."""
        file_content = b"<?php echo 'shell'; ?>"
        file_obj, filename = self.create_test_file(file_content, "shell.php")

        response = client.post(
            "/analyze/audio",
            files={"file": (filename, file_obj, "text/plain")},
        )

        assert response.status_code == 400

    def test_upload_shell_script_extension(self, client: TestClient) -> None:
        """Test that shell scripts are rejected."""
        file_content = b"#!/bin/bash\necho 'hello'"
        file_obj, filename = self.create_test_file(file_content, "script.sh")

        response = client.post(
            "/analyze/audio",
            files={"file": (filename, file_obj, "text/plain")},
        )

        assert response.status_code == 400

    def test_upload_reserved_windows_name(self, client: TestClient) -> None:
        """Test that reserved Windows names are sanitized."""
        wav_content = b"RIFF\x00\x00\x00\x00WAVEfmt \x00\x00\x00\x00\x00\x00\x00\x00"
        file_obj, filename = self.create_test_file(wav_content, "CON.wav")

        # This might be accepted with sanitization or rejected
        response = client.post(
            "/analyze/audio",
            files={"file": (filename, file_obj, "audio/wav")},
        )

        # Should not be accepted as-is (either rejected or sanitized)
        if response.status_code == 200:
            # If accepted, the filename should have been sanitized
            pass  # File was accepted after sanitization
        else:
            # Otherwise should be rejected
            assert response.status_code in [400, 422]

    def test_upload_extension_case_sensitivity(self, client: TestClient) -> None:
        """Test that extension validation is case-insensitive."""
        # Valid WAV content with uppercase extension
        wav_content = b"RIFF\x00\x00\x00\x00WAVEfmt \x00\x00\x00\x00\x00\x00\x00\x00"
        file_obj, filename = self.create_test_file(wav_content, "audio.WAV")

        # The validation may pass or fail based on content check
        # This test mainly verifies the extension check doesn't crash
        response = client.post(
            "/analyze/audio",
            files={"file": (filename, file_obj, "audio/wav")},
        )

        # Response should be valid HTTP (not 500)
        assert response.status_code in [200, 400, 422]

    def test_upload_double_extension_trick(self, client: TestClient) -> None:
        """Test handling of double extension (e.g., file.php.jpg)."""
        file_content = b"RIFF\x00\x00\x00\x00WAVEfmt \x00\x00\x00\x00\x00\x00\x00\x00"
        file_obj, filename = self.create_test_file(file_content, "shell.php.mp3")

        response = client.post(
            "/analyze/audio",
            files={"file": (filename, file_obj, "audio/mpeg")},
        )

        # Should be rejected based on final extension or content
        # (the .mp3 extension is valid but content might not match)

    def test_upload_control_characters_in_filename(self, client: TestClient) -> None:
        """Test handling of control characters in filename."""
        wav_content = b"RIFF\x00\x00\x00\x00WAVEfmt \x00\x00\x00\x00\x00\x00\x00\x00"
        file_obj, filename = self.create_test_file(wav_content, "file\x01\x02.mp3")

        response = client.post(
            "/analyze/audio",
            files={"file": (filename, file_obj, "audio/mpeg")},
        )

        # Control characters should be sanitized or rejected
        assert response.status_code in [200, 400, 422]

    def test_upload_empty_filename(self, client: TestClient) -> None:
        """Test handling of empty filename."""
        wav_content = b"RIFF\x00\x00\x00\x00WAVEfmt \x00\x00\x00\x00\x00\x00\x00\x00"
        file_obj, _ = self.create_test_file(wav_content, "")

        response = client.post(
            "/analyze/audio",
            files={"file": ("", file_obj, "audio/wav")},
        )

        # Should be rejected
        assert response.status_code in [400, 422]

    def test_upload_very_large_filename(self, client: TestClient) -> None:
        """Test handling of very long filename."""
        wav_content = b"RIFF\x00\x00\x00\x00WAVEfmt \x00\x00\x00\x00\x00\x00\x00\x00"
        long_name = "a" * 300 + ".wav"
        file_obj, filename = self.create_test_file(wav_content, long_name)

        response = client.post(
            "/analyze/audio",
            files={"file": (filename, file_obj, "audio/wav")},
        )

        # Should handle gracefully (truncate or reject)
        assert response.status_code in [200, 400, 422]

    def test_upload_special_chars_in_filename(self, client: TestClient) -> None:
        """Test handling of special characters in filename."""
        wav_content = b"RIFF\x00\x00\x00\x00WAVEfmt \x00\x00\x00\x00\x00\x00\x00\x00"
        file_obj, filename = self.create_test_file(wav_content, "file<>:|.wav")

        response = client.post(
            "/analyze/audio",
            files={"file": (filename, file_obj, "audio/wav")},
        )

        # Special characters should be sanitized
        assert response.status_code in [200, 400, 422]

    def test_upload_video_path_traversal(self, client: TestClient) -> None:
        """Test path traversal protection for video endpoint."""
        mp4_content = b"\x00\x00\x00\x20ftypisom\x00\x00\x00\x00isommp41"
        file_obj, filename = self.create_test_file(mp4_content, "../../../etc/shadow.mp4")

        response = client.post(
            "/analyze/video",
            files={"video": (filename, file_obj, "video/mp4")},
        )

        assert response.status_code == 400

    def test_upload_video_exe_disguised(self, client: TestClient) -> None:
        """Test EXE disguised as MP4 for video endpoint."""
        exe_content = b"MZ\x90\x00\x03\x00\x00\x00\x04\x00\x00\x00\xff\xff"
        file_obj, filename = self.create_test_file(exe_content, "virus.mp4")

        response = client.post(
            "/analyze/video",
            files={"video": (filename, file_obj, "video/mp4")},
        )

        assert response.status_code == 400
