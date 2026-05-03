"""Testes para checksum de auditoria."""

from __future__ import annotations

import hashlib
import json
import tempfile
from datetime import datetime

import pytest

from src.models.audit_log import AuditEventType, AuditLogEntry
from src.utils.audit_logger import AuditLogger


class TestAuditChecksum:
    """Testes para funcionalidade de checksum de auditoria."""

    @pytest.fixture
    def temp_logger(self):
        """Create a temporary audit logger for testing."""
        with tempfile.TemporaryDirectory() as tmpdir:
            AuditLogger._instance = None
            logger = AuditLogger(
                log_dir=str(tmpdir),
                max_size_bytes=1024 * 1024,
                max_age_days=365,
            )
            yield logger
            AuditLogger._instance = None

    def test_calculate_checksum(self, temp_logger):
        """T025: Testar cálculo de checksum de entrada."""
        logger = temp_logger

        # Create a test entry
        entry = AuditLogEntry(
            event_type=AuditEventType.ANALYSIS_CREATED,
            timestamp=datetime.utcnow(),
            correlation_id="test-checksum-123",
            action="POST /analyze",
            resource="/analyze/text",
            result="success",
            details={"modalities": ["text"]},
        )

        # Calculate checksum using the internal method
        entry_bytes = logger._write_entry_with_integrity(entry)
        entry_dict = json.loads(entry_bytes.decode("utf-8"))

        # Verify checksum exists and is valid SHA-256
        assert "_checksum" in entry_dict, "Entry should have _checksum field"
        assert len(entry_dict["_checksum"]) == 64, "Checksum should be 64 hex chars (SHA-256)"

        # Calculate expected checksum
        entry_dict_copy = entry_dict.copy()
        entry_dict_copy.pop("_checksum", None)
        json_str = json.dumps(entry_dict_copy, sort_keys=True, ensure_ascii=False)
        expected_checksum = hashlib.sha256(json_str.encode("utf-8")).hexdigest()

        assert entry_dict["_checksum"] == expected_checksum, "Checksum should match expected value"

    def test_validate_checksum(self, temp_logger):
        """T026: Testar validação de checksum."""
        logger = temp_logger

        # Create a valid entry with checksum
        entry = AuditLogEntry(
            event_type=AuditEventType.DATA_ACCESS,
            timestamp=datetime.utcnow(),
            correlation_id="test-validate-123",
            action="GET /data",
            resource="/data/patients",
            result="success",
            user_id="sha256:abc123",
            details={"action": "read"},
        )

        # Write entry with integrity
        entry_bytes = logger._write_entry_with_integrity(entry)
        entry_line = entry_bytes.decode("utf-8").strip()

        # Verify valid checksum
        is_valid = logger._verify_entry_integrity(entry_line)
        assert is_valid is True, "Valid entry should pass integrity check"

    def test_validate_checksum_invalid(self, temp_logger):
        """Test validation fails with tampered data."""
        logger = temp_logger

        # Create an entry and tamper with it
        entry = AuditLogEntry(
            event_type=AuditEventType.SECURITY_ALERT,
            timestamp=datetime.utcnow(),
            correlation_id="test-tamper-123",
            action="POST /alert",
            resource="/security",
            result="error",
            details={"severity": "high"},
        )

        # Write entry with integrity
        entry_bytes = logger._write_entry_with_integrity(entry)
        entry_dict = json.loads(entry_bytes.decode("utf-8"))

        # Tamper with the data
        entry_dict["result"] = "success"  # Change the result
        tampered_line = json.dumps(entry_dict)

        # Verify tampered entry fails integrity check
        is_valid = logger._verify_entry_integrity(tampered_line)
        assert is_valid is False, "Tampered entry should fail integrity check"

    def test_validate_checksum_missing_checksum(self, temp_logger):
        """Test validation fails when checksum is missing."""
        logger = temp_logger

        # Create entry without checksum
        entry_dict = {
            "event_type": "ANALYSIS_CREATED",
            "timestamp": datetime.utcnow().isoformat(),
            "correlation_id": "test-no-checksum",
            "action": "POST /test",
            "resource": "/test",
            "result": "success",
            "details": {},
        }
        entry_line = json.dumps(entry_dict)

        # Verify missing checksum fails
        is_valid = logger._verify_entry_integrity(entry_line)
        assert is_valid is False, "Entry without checksum should fail validation"

    def test_validate_checksum_invalid_json(self, temp_logger):
        """Test validation fails with invalid JSON."""
        logger = temp_logger

        # Invalid JSON line
        invalid_line = "this is not valid json"

        # Verify invalid JSON fails
        is_valid = logger._verify_entry_integrity(invalid_line)
        assert is_valid is False, "Invalid JSON should fail validation"

    def test_checksum_consistency(self, temp_logger):
        """Test that same entry data produces consistent checksum."""
        logger = temp_logger

        from uuid import UUID
        fixed_timestamp = datetime(2024, 1, 1, 12, 0, 0)
        fixed_event_id = UUID("12345678-1234-5678-1234-567812345678")

        # Create an entry with fixed values
        entry = AuditLogEntry(
            event_id=fixed_event_id,
            event_type=AuditEventType.ANALYSIS_CREATED,
            timestamp=fixed_timestamp,
            correlation_id="consistent-123",
            action="POST /analyze",
            resource="/analyze/text",
            result="success",
            details={"test": "data"},
        )

        # Write entry twice
        bytes1 = logger._write_entry_with_integrity(entry)
        bytes2 = logger._write_entry_with_integrity(entry)

        dict1 = json.loads(bytes1.decode("utf-8"))
        dict2 = json.loads(bytes2.decode("utf-8"))

        # Checksums should be identical since same entry data is used
        assert dict1["_checksum"] == dict2["_checksum"], "Same entry should produce identical checksums"

    def test_checksum_different_data(self, temp_logger):
        """Test that different data produces different checksums."""
        logger = temp_logger

        # Create different entries
        entry1 = AuditLogEntry(
            event_type=AuditEventType.ANALYSIS_CREATED,
            timestamp=datetime.utcnow(),
            correlation_id="diff-123",
            action="POST /analyze",
            resource="/analyze/text",
            result="success",
            details={"data": "value1"},
        )
        entry2 = AuditLogEntry(
            event_type=AuditEventType.ANALYSIS_CREATED,
            timestamp=datetime.utcnow(),
            correlation_id="diff-123",
            action="POST /analyze",
            resource="/analyze/text",
            result="success",
            details={"data": "value2"},  # Different value
        )

        # Write both entries
        bytes1 = logger._write_entry_with_integrity(entry1)
        bytes2 = logger._write_entry_with_integrity(entry2)

        dict1 = json.loads(bytes1.decode("utf-8"))
        dict2 = json.loads(bytes2.decode("utf-8"))

        # Checksums should be different
        assert dict1["_checksum"] != dict2["_checksum"], "Different entries should have different checksums"
