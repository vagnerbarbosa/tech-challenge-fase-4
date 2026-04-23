"""Security tests for secrets in logs (T030).

Tests that verify secrets are never logged in plaintext.
This test uses grep-like verification to ensure no sensitive data leaks.

Reference: spec.md FR-009 - mascarar secrets em logs
"""

import json

from src.core.security.log_sanitizer import (
    LogSanitizer,
    PatientIdHasher,
    SecretMasker,
)


class TestSecretsNotInLogs:
    """Tests to verify secrets are never logged in plaintext."""

    SECRETS_TO_TEST = [
        "supersecrettoken123",
        "my-api-key-456",
        "password123!",
        "sk-1234567890abcdef",
        "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.test",
    ]

    def test_api_keys_masked_in_strings(self):
        """API keys should be masked in log strings."""
        for secret in self.SECRETS_TO_TEST:
            log_message = f"Processing with api_key={secret}"
            masked = SecretMasker.mask(log_message)
            assert secret not in masked, f"Secret was not masked: {secret[:10]}..."

    def test_connection_strings_masked(self):
        """Connection string passwords should be masked."""
        secret_password = "MySecretP@ssw0rd"
        connection_string = (
            f"Server=myserver;Database=mydb;Password={secret_password};"
        )
        masked = SecretMasker.mask(connection_string)
        assert secret_password not in masked

    def test_azure_keys_masked(self):
        """Azure keys should be masked."""
        azure_key = "1234567890abcdef1234567890abcdef"
        log_message = f"Azure request with key: {azure_key}"
        masked = SecretMasker.mask(log_message)
        assert azure_key not in masked

    def test_bearer_tokens_masked(self):
        """Bearer tokens should be masked."""
        token = "Bearer eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJzdWIiOiIxMjM0NTY3ODkwIn0"
        log_message = f"Authorization: {token}"
        masked = SecretMasker.mask(log_message)
        assert "eyJhbGci" not in masked

    def test_private_keys_masked(self):
        """Private keys should be masked."""
        private_key = """-----BEGIN RSA PRIVATE KEY-----
MIIEpAIBAAKCAQEA...
-----END RSA PRIVATE KEY-----"""
        log_message = f"Loaded key: {private_key}"
        masked = SecretMasker.mask(log_message)
        assert "BEGIN RSA PRIVATE KEY" not in masked


class TestPatientIdNotInPlaintext:
    """Tests to verify patient IDs are never logged in plaintext (FR-010)."""

    PATIENT_IDS = [
        "patient-123-456",
        "123.456.789-00",  # CPF-like
        "MRN123456",
        "PACIENTE_001",
    ]

    def test_patient_id_hashed_in_logs(self):
        """Patient IDs should be hashed, not logged in plaintext."""
        for patient_id in self.PATIENT_IDS:
            log_data = {"patient_id": patient_id, "action": "analysis"}
            sanitized = LogSanitizer.sanitize(log_data)
            assert patient_id not in str(sanitized)
            # Should have a hash instead
            assert sanitized["patient_id"] is not None
            assert len(sanitized["patient_id"]) == 16

    def test_patient_id_consistency(self):
        """Same patient ID should produce same hash for correlation."""
        patient_id = "patient-abc-123"
        hash1 = PatientIdHasher.hash(patient_id)
        hash2 = PatientIdHasher.hash(patient_id)
        assert hash1 == hash2, "Patient ID hashing should be consistent"

    def test_different_patients_different_hashes(self):
        """Different patient IDs should produce different hashes."""
        id1 = "patient-001"
        id2 = "patient-002"
        hash1 = PatientIdHasher.hash(id1)
        hash2 = PatientIdHasher.hash(id2)
        assert hash1 != hash2, "Different patients should have different hashes"


class TestAuditLogSanitization:
    """Tests for audit log sanitization (T037)."""

    def test_media_content_redacted(self):
        """Media content should be completely redacted from audit logs."""
        data = {
            "patient_id": "patient-123",
            "transcricao": "sensitive medical transcript",
            "texto": "patient symptoms description",
        }
        sanitized = LogSanitizer.sanitize_for_audit(data)
        assert sanitized["transcricao"] == "[REDACTED_MEDIA_CONTENT]"
        assert sanitized["texto"] == "[REDACTED_MEDIA_CONTENT]"

    def test_patient_id_hashed_in_audit(self):
        """Patient ID should be hashed in audit logs."""
        patient_id = "patient-456"
        data = {"patient_id": patient_id}
        sanitized = LogSanitizer.sanitize_for_audit(data)
        assert patient_id not in sanitized["patient_id"]
        assert len(sanitized["patient_id"]) == 16


class TestGrepLikeVerification:
    """Grep-like tests to simulate log scanning for secrets."""

    def test_grep_no_api_keys_in_masked_logs(self):
        """Simulate grep for API keys - should find nothing."""
        log_entries = [
            "api_key=secret123",
            "API_KEY: another_secret",
            "X-API-Key: third_secret",
        ]
        for entry in log_entries:
            masked = SecretMasker.mask(entry)
            # Simulate grep for common secret patterns
            assert "secret" not in masked.lower()

    def test_grep_no_passwords_in_masked_logs(self):
        """Simulate grep for passwords - should find nothing."""
        log_entries = [
            "password=my_password",
            "pwd=secretpwd",
            "Password: SuperSecret123!",
        ]
        for entry in log_entries:
            masked = SecretMasker.mask(entry)
            assert "my_password" not in masked
            assert "secretpwd" not in masked
            assert "SuperSecret123" not in masked

    def test_grep_no_patient_ids_in_hashed_logs(self):
        """Simulate grep for patient IDs - should find only hashes."""
        patient_id = "PATIENT_12345"
        log_data = {
            "event": "analysis_complete",
            "patient_id": patient_id,
            "result": "success",
        }
        sanitized = LogSanitizer.sanitize(log_data)
        log_string = json.dumps(sanitized)
        # Original patient ID should not be found
        assert patient_id not in log_string
        # But there should be a hash
        assert sanitized["patient_id"] is not None


class TestErrorMessagesSanitized:
    """Tests for sanitized error messages (FR-034)."""

    def test_error_messages_dont_contain_secrets(self):
        """Error messages should not contain secrets."""
        error_message = "Connection failed with key: secret_api_key_123"
        sanitized = SecretMasker.mask_exception_message(error_message)
        assert "secret_api_key_123" not in sanitized
        assert SecretMasker.MASK_VALUE in sanitized

    def test_azure_errors_masked(self):
        """Azure connection errors should not expose keys."""
        error_message = (
            "Azure error: Authentication failed for key "
            "1234567890abcdef1234567890abcdef"
        )
        sanitized = SecretMasker.mask_exception_message(error_message)
        assert "1234567890abcdef" not in sanitized


class TestSensitiveKeysDetection:
    """Tests for detection of sensitive keys in dictionaries."""

    SENSITIVE_KEYS = [
        "api_key",
        "apikey",
        "key",
        "secret",
        "password",
        "token",
        "credential",
        "authorization",
        "azure_text_key",
        "azure_speech_key",
        "azure_vision_key",
        "connection_string",
        "private_key",
        "access_key",
        "secret_key",
        "client_secret",
    ]

    def test_all_sensitive_keys_masked(self):
        """All sensitive key variants should be masked."""
        for key in self.SENSITIVE_KEYS:
            data = {key: "sensitive_value_123"}
            masked = SecretMasker.mask_dict(data)
            assert masked[key] == SecretMasker.MASK_VALUE, f"Key '{key}' was not masked"

    def test_case_insensitive_key_matching(self):
        """Sensitive key detection should be case-insensitive."""
        data = {
            "API_KEY": "value1",
            "Password": "value2",
            "Secret": "value3",
        }
        masked = SecretMasker.mask_dict(data)
        assert masked["API_KEY"] == SecretMasker.MASK_VALUE
        assert masked["Password"] == SecretMasker.MASK_VALUE
        assert masked["Secret"] == SecretMasker.MASK_VALUE
