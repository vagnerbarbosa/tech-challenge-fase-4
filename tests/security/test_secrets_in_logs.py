"""Testes de segurança para secrets em logs (T030).

Testes que verificam que secrets nunca são logados em plaintext.
Este teste usa verificação tipo grep para garantir que não há vazamento de dados sensíveis.

Referência: spec.md FR-009 - mascarar secrets em logs
"""

import json

from src.core.security.log_sanitizer import (
    LogSanitizer,
    PatientIdHasher,
    SecretMasker,
)


class TestSecretsNotInLogs:
    """Testes para verificar que secrets nunca são logados em plaintext."""

    SECRETS_TO_TEST = [
        "supersecrettoken123",
        "my-api-key-456",
        "password123!",
        "sk-1234567890abcdef",
        "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.test",
    ]

    def test_api_keys_masked_in_strings(self):
        """API keys devem ser mascarados em strings de log."""
        for secret in self.SECRETS_TO_TEST:
            log_message = f"Processing with api_key={secret}"
            masked = SecretMasker.mask(log_message)
            assert secret not in masked, f"Secret não foi mascarado: {secret[:10]}..."

    def test_connection_strings_masked(self):
        """Senhas de connection string devem ser mascaradas."""
        secret_password = "MySecretP@ssw0rd"
        connection_string = (
            f"Server=myserver;Database=mydb;Password={secret_password};"
        )
        masked = SecretMasker.mask(connection_string)
        assert secret_password not in masked

    def test_azure_keys_masked(self):
        """Azure keys devem ser mascaradas."""
        azure_key = "1234567890abcdef1234567890abcdef"
        log_message = f"Azure request with key: {azure_key}"
        masked = SecretMasker.mask(log_message)
        assert azure_key not in masked

    def test_bearer_tokens_masked(self):
        """Bearer tokens devem ser mascarados."""
        token = "Bearer eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJzdWIiOiIxMjM0NTY3ODkwIn0"
        log_message = f"Authorization: {token}"
        masked = SecretMasker.mask(log_message)
        assert "eyJhbGci" not in masked

    def test_private_keys_masked(self):
        """Private keys devem ser mascaradas."""
        private_key = """-----BEGIN RSA PRIVATE KEY-----
MIIEpAIBAAKCAQEA...
-----END RSA PRIVATE KEY-----"""
        log_message = f"Loaded key: {private_key}"
        masked = SecretMasker.mask(log_message)
        assert "BEGIN RSA PRIVATE KEY" not in masked


class TestPatientIdNotInPlaintext:
    """Testes para verificar que patient IDs nunca são logados em plaintext (FR-010)."""

    PATIENT_IDS = [
        "patient-123-456",
        "123.456.789-00",  # CPF-like
        "MRN123456",
        "PACIENTE_001",
    ]

    def test_patient_id_hashed_in_logs(self):
        """Patient IDs devem ser hasheados, não logados em plaintext."""
        for patient_id in self.PATIENT_IDS:
            log_data = {"patient_id": patient_id, "action": "analysis"}
            sanitized = LogSanitizer.sanitize(log_data)
            assert patient_id not in str(sanitized)
            # Deve ter um hash no lugar
            assert sanitized["patient_id"] is not None
            assert len(sanitized["patient_id"]) == 16

    def test_patient_id_consistency(self):
        """Mesmo patient ID deve produzir mesmo hash para correlação."""
        patient_id = "patient-abc-123"
        hash1 = PatientIdHasher.hash(patient_id)
        hash2 = PatientIdHasher.hash(patient_id)
        assert hash1 == hash2, "Hashing de patient ID deve ser consistente"

    def test_different_patients_different_hashes(self):
        """Different patient IDs devem produzir hashes diferentes."""
        id1 = "patient-001"
        id2 = "patient-002"
        hash1 = PatientIdHasher.hash(id1)
        hash2 = PatientIdHasher.hash(id2)
        assert hash1 != hash2, "Pacientes diferentes devem ter hashes diferentes"


class TestAuditLogSanitization:
    """Testes para sanitização de logs de auditoria (T037)."""

    def test_media_content_redacted(self):
        """Conteúdo de mídia deve ser completamente removido dos logs de auditoria."""
        data = {
            "patient_id": "patient-123",
            "transcricao": "sensitive medical transcript",
            "texto": "patient symptoms description",
        }
        sanitized = LogSanitizer.sanitize_for_audit(data)
        assert sanitized["transcricao"] == "[REDACTED_MEDIA_CONTENT]"
        assert sanitized["texto"] == "[REDACTED_MEDIA_CONTENT]"

    def test_patient_id_hashed_in_audit(self):
        """Patient ID deve ser hasheado em logs de auditoria."""
        patient_id = "patient-456"
        data = {"patient_id": patient_id}
        sanitized = LogSanitizer.sanitize_for_audit(data)
        assert patient_id not in sanitized["patient_id"]
        assert len(sanitized["patient_id"]) == 16


class TestGrepLikeVerification:
    """Testes tipo grep para simular scan de logs por secrets."""

    def test_grep_no_api_keys_in_masked_logs(self):
        """Simula grep por API keys - não deve encontrar nada."""
        log_entries = [
            "api_key=secret123",
            "API_KEY: another_secret",
            "X-API-Key: third_secret",
        ]
        for entry in log_entries:
            masked = SecretMasker.mask(entry)
            # Simula grep por padrões comuns de secrets
            assert "secret" not in masked.lower()

    def test_grep_no_passwords_in_masked_logs(self):
        """Simula grep por senhas - não deve encontrar nada."""
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
        """Simula grep por patient IDs - deve encontrar apenas hashes."""
        patient_id = "PATIENT_12345"
        log_data = {
            "event": "analysis_complete",
            "patient_id": patient_id,
            "result": "success",
        }
        sanitized = LogSanitizer.sanitize(log_data)
        log_string = json.dumps(sanitized)
        # Patient ID original não deve ser encontrado
        assert patient_id not in log_string
        # Mas deve haver um hash
        assert sanitized["patient_id"] is not None


class TestErrorMessagesSanitized:
    """Testes para mensagens de erro sanitizadas (FR-034)."""

    def test_error_messages_dont_contain_secrets(self):
        """Mensagens de erro não devem conter secrets."""
        error_message = "Connection failed with key: secret_api_key_123"
        sanitized = SecretMasker.mask_exception_message(error_message)
        assert "secret_api_key_123" not in sanitized
        assert SecretMasker.MASK_VALUE in sanitized

    def test_azure_errors_masked(self):
        """Erros de conexão Azure não devem expor keys."""
        error_message = (
            "Azure error: Authentication failed for key "
            "1234567890abcdef1234567890abcdef"
        )
        sanitized = SecretMasker.mask_exception_message(error_message)
        assert "1234567890abcdef" not in sanitized


class TestSensitiveKeysDetection:
    """Testes para detecção de chaves sensíveis em dicionários."""

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
        """Todas as variantes de chaves sensíveis devem ser mascaradas."""
        for key in self.SENSITIVE_KEYS:
            data = {key: "sensitive_value_123"}
            masked = SecretMasker.mask_dict(data)
            assert masked[key] == SecretMasker.MASK_VALUE, f"Chave '{key}' não foi mascarada"

    def test_case_insensitive_key_matching(self):
        """Detecção de chaves sensíveis deve ser case-insensitive."""
        data = {
            "API_KEY": "value1",
            "Password": "value2",
            "Secret": "value3",
        }
        masked = SecretMasker.mask_dict(data)
        assert masked["API_KEY"] == SecretMasker.MASK_VALUE
        assert masked["Password"] == SecretMasker.MASK_VALUE
        assert masked["Secret"] == SecretMasker.MASK_VALUE
