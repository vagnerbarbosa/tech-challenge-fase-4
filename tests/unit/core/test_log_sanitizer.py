"""Unit tests for LogSanitizer (T029).

Tests secret masking, patient ID hashing, and log sanitization
to ensure LGPD compliance.
"""

import pytest

from src.core.security.log_sanitizer import (
    LogSanitizer,
    PatientIdHasher,
    SecretMasker,
    hash_patient_id,
    sanitize_log_data,
)


class TestSecretMasker:
    """Tests for SecretMasker class."""

    def test_mask_azure_key(self):
        """Azure keys should be masked with special pattern."""
        text = "My Azure key is 1234567890abcdef1234567890abcdef"
        result = SecretMasker.mask(text)
        assert SecretMasker.MASK_AZURE_KEY in result
        assert "1234567890abcdef" not in result

    def test_mask_api_key(self):
        """API keys should be masked."""
        text = "api_key=supersecrettoken123"
        result = SecretMasker.mask(text)
        assert SecretMasker.MASK_VALUE in result
        assert "supersecrettoken123" not in result

    def test_mask_bearer_token(self):
        """Bearer tokens should be masked."""
        text = "Authorization: Bearer eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9"
        result = SecretMasker.mask(text)
        assert SecretMasker.MASK_VALUE in result
        assert "eyJhbGci" not in result

    def test_mask_connection_string_password(self):
        """Passwords in connection strings should be masked."""
        text = "Server=myserver;Password=mypassword123;"
        result = SecretMasker.mask(text)
        assert SecretMasker.MASK_VALUE in result
        assert "mypassword123" not in result

    def test_mask_none(self):
        """None input should return empty string."""
        result = SecretMasker.mask(None)
        assert result == ""

    def test_mask_dict_with_sensitive_keys(self):
        """Dictionary with sensitive keys should be masked."""
        data = {
            "api_key": "secret123",
            "password": "mypass",
            "normal_field": "normal_value",
        }
        result = SecretMasker.mask_dict(data)
        assert result["api_key"] == SecretMasker.MASK_VALUE
        assert result["password"] == SecretMasker.MASK_VALUE
        assert result["normal_field"] == "normal_value"

    def test_mask_dict_nested(self):
        """Nested dictionaries should be recursively masked."""
        data = {
            "level1": {
                "api_key": "nested_secret",
                "level2": {
                    "password": "deep_secret",
                },
            },
        }
        result = SecretMasker.mask_dict(data)
        assert result["level1"]["api_key"] == SecretMasker.MASK_VALUE
        assert result["level1"]["level2"]["password"] == SecretMasker.MASK_VALUE

    def test_mask_list(self):
        """Lists should be recursively masked."""
        data = ["api_key=secret", {"password": "test"}, "normal"]
        result = SecretMasker.mask_list(data)
        assert SecretMasker.MASK_VALUE in result[0]
        assert result[1]["password"] == SecretMasker.MASK_VALUE
        assert result[2] == "normal"

    def test_mask_exception_message(self):
        """Exception messages should be masked."""
        message = "Error connecting with key: supersecret"
        result = SecretMasker.mask_exception_message(message)
        assert "supersecret" not in result


class TestPatientIdHasher:
    """Tests for PatientIdHasher class."""

    def test_hash_patient_id(self):
        """Patient ID should be hashed consistently."""
        patient_id = "patient-123-abc"
        result = PatientIdHasher.hash(patient_id)
        assert result is not None
        assert len(result) == 16
        # Should be consistent
        result2 = PatientIdHasher.hash(patient_id)
        assert result == result2

    def test_hash_none(self):
        """None input should return None."""
        result = PatientIdHasher.hash(None)
        assert result is None

    def test_hash_different_ids(self):
        """Different IDs should produce different hashes."""
        id1 = "patient-001"
        id2 = "patient-002"
        hash1 = PatientIdHasher.hash(id1)
        hash2 = PatientIdHasher.hash(id2)
        assert hash1 != hash2

    def test_hash_patient_id_field(self):
        """Patient ID field in dict should be hashed."""
        data = {
            "patient_id": "patient-123",
            "other_field": "value",
        }
        result = PatientIdHasher.hash_patient_id_field(data)
        assert result["patient_id"] != "patient-123"
        assert len(result["patient_id"]) == 16
        assert result["other_field"] == "value"

    def test_hash_patient_id_field_nested(self):
        """Nested patient_id fields should be hashed."""
        data = {
            "nested": {
                "patient_id": "patient-456",
            },
        }
        result = PatientIdHasher.hash_patient_id_field(data)
        assert result["nested"]["patient_id"] != "patient-456"

    def test_get_hash_prefix(self):
        """Should return first 8 chars of hash."""
        patient_id = "patient-123"
        full_hash = PatientIdHasher.hash(patient_id)
        prefix = PatientIdHasher.get_hash_prefix(patient_id)
        assert prefix == full_hash[:8]


class TestLogSanitizer:
    """Tests for LogSanitizer class."""

    def test_sanitize_string(self):
        """Strings should be masked."""
        text = "Error with api_key=secret123"
        result = LogSanitizer.sanitize(text)
        assert "secret123" not in result
        assert SecretMasker.MASK_VALUE in result

    def test_sanitize_dict(self):
        """Dicts should have patient_id hashed and secrets masked."""
        data = {
            "patient_id": "patient-123",
            "api_key": "secret",
            "message": "Test message",
        }
        result = LogSanitizer.sanitize(data)
        assert result["patient_id"] != "patient-123"
        assert result["api_key"] == SecretMasker.MASK_VALUE
        assert result["message"] == "Test message"

    def test_sanitize_list(self):
        """Lists should be sanitized."""
        data = [
            {"patient_id": "patient-123", "api_key": "secret"},
            "normal string",
        ]
        result = LogSanitizer.sanitize(data)
        assert result[0]["patient_id"] != "patient-123"
        assert result[0]["api_key"] == SecretMasker.MASK_VALUE

    def test_sanitize_for_audit(self):
        """Audit sanitization should be more aggressive."""
        data = {
            "patient_id": "patient-123",
            "transcricao": "sensitive patient data here",
            "api_key": "secret",
            "normal_field": "value",
        }
        result = LogSanitizer.sanitize_for_audit(data)
        assert result["patient_id"] != "patient-123"
        assert result["transcricao"] == "[REDACTED_MEDIA_CONTENT]"
        assert result["api_key"] == SecretMasker.MASK_VALUE
        assert result["normal_field"] == "value"

    def test_sanitize_for_audit_nested(self):
        """Audit sanitization should handle nested structures."""
        data = {
            "nested": {
                "transcricao": "sensitive data",
                "text": "more sensitive",
            },
        }
        result = LogSanitizer.sanitize_for_audit(data)
        assert result["nested"]["transcricao"] == "[REDACTED_MEDIA_CONTENT]"


class TestConvenienceFunctions:
    """Tests for module-level convenience functions."""

    def test_sanitize_log_data(self):
        """sanitize_log_data should work as LogSanitizer.sanitize."""
        data = {"api_key": "secret"}
        result = sanitize_log_data(data)
        assert result["api_key"] == SecretMasker.MASK_VALUE

    def test_hash_patient_id_convenience(self):
        """hash_patient_id should work as PatientIdHasher.hash."""
        patient_id = "patient-123"
        result = hash_patient_id(patient_id)
        expected = PatientIdHasher.hash(patient_id)
        assert result == expected


class TestAzureKeyMasking:
    """Specific tests for Azure key masking (FR-009)."""

    def test_mask_azure_text_key(self):
        """Azure text keys should be masked."""
        key = "a" * 32  # 32 hex chars
        text = f"azure_text_key={key}"
        result = SecretMasker.mask(text)
        assert key not in result

    def test_mask_azure_speech_key(self):
        """Azure speech keys should be masked."""
        key = "b" * 32
        text = f"azure_speech_key={key}"
        result = SecretMasker.mask(text)
        assert key not in result

    def test_mask_azure_vision_key(self):
        """Azure vision keys should be masked."""
        key = "c" * 32
        text = f"azure_vision_key={key}"
        result = SecretMasker.mask(text)
        assert key not in result

    def test_mask_connection_string(self):
        """Azure connection strings should be masked."""
        text = "DefaultEndpointsProtocol=https;AccountName=myaccount;AccountKey=mykey;"
        result = SecretMasker.mask(text)
        assert "mykey" not in result


class TestPatientIdHashingCompliance:
    """Tests for LGPD patient ID hashing compliance (FR-010)."""

    def test_patient_id_not_in_plaintext(self):
        """Original patient ID should never appear in logs."""
        patient_id = "123.456.789-00"  # CPF-like
        data = {"patient_id": patient_id}
        result = LogSanitizer.sanitize(data)
        assert patient_id not in str(result)

    def test_patient_id_correlation(self):
        """Same patient ID should produce same hash for correlation."""
        patient_id = "patient-abc-123"
        hash1 = PatientIdHasher.hash(patient_id)
        hash2 = PatientIdHasher.hash(patient_id)
        assert hash1 == hash2
        # Different ID should produce different hash
        hash3 = PatientIdHasher.hash("different-id")
        assert hash3 != hash1

    def test_hash_length(self):
        """Hash should be 16 characters for readability."""
        patient_id = "any-patient-id"
        result = PatientIdHasher.hash(patient_id)
        assert len(result) == 16
