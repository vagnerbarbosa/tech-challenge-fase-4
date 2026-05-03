"""Testes para verificação de integridade."""

from __future__ import annotations

import gzip
import json
import tempfile
from datetime import datetime
from pathlib import Path
from unittest.mock import patch

import pytest

from src.models.audit_log import AuditEventType
from src.utils.audit_logger import AuditLogger


class TestAuditIntegrity:
    """Testes para verificação de integridade de logs de auditoria."""

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

    def test_verify_all_entries(self, temp_logger):
        """T027: Testar verificação de integridade de todas entradas."""
        logger = temp_logger

        # Create multiple log entries
        for i in range(5):
            logger.log(
                event_type=AuditEventType.ANALYSIS_CREATED,
                correlation_id=f"verify-test-{i}",
                action="POST /analyze",
                resource="/analyze/text",
                result="success",
                details={"index": i},
            )

        # Retrieve entries with integrity verification enabled
        entries = logger.get_entries(verify_integrity=True, limit=10)

        # All entries should be retrieved successfully
        assert len(entries) == 5, "All 5 entries should be retrieved"

        # Verify each entry has valid data
        for i, entry in enumerate(entries):
            assert entry.correlation_id == f"verify-test-{i}"
            assert entry.event_type == AuditEventType.ANALYSIS_CREATED
            assert entry.details.get("index") == i

    def test_detect_corrupted_entry(self, temp_logger):
        """T028: Testar detecção de entrada corrompida."""
        logger = temp_logger

        # Create a valid entry first
        logger.log(
            event_type=AuditEventType.DATA_ACCESS,
            correlation_id="valid-entry",
            action="GET /data",
            resource="/data/patients",
            result="success",
            details={"status": "ok"},
        )

        # Manually create a corrupted entry in the log file
        corrupted_entry = {
            "event_type": "security_alert",
            "timestamp": datetime.utcnow().isoformat(),
            "correlation_id": "corrupted-entry",
            "action": "POST /alert",
            "resource": "/security",
            "result": "error",
            "details": {"alert": "test"},
            "_checksum": "invalid_checksum_12345",  # Invalid checksum
        }

        # Append corrupted entry to log file
        with open(logger.current_log_file, "a") as f:
            f.write(json.dumps(corrupted_entry) + "\n")

        # Retrieve entries with integrity verification
        with patch("src.utils.audit_logger.logger") as mock_logger:
            entries = logger.get_entries(verify_integrity=True, limit=10)

            # Valid entry should still be retrieved
            assert len(entries) == 1, "Only valid entry should be retrieved"
            assert entries[0].correlation_id == "valid-entry"

            # Warning should be logged for corrupted entry
            warning_calls = [call for call in mock_logger.warning.call_args_list
                           if "Integrity check failed" in str(call)]
            assert len(warning_calls) > 0, "Warning should be logged for corrupted entry"

    def test_verify_integrity_disabled(self, temp_logger):
        """Test that corrupted entries are included when verification is disabled."""
        logger = temp_logger

        # Create a valid entry
        logger.log(
            event_type=AuditEventType.DATA_ACCESS,
            correlation_id="valid-entry",
            action="GET /data",
            resource="/data/patients",
            result="success",
            details={"status": "ok"},
        )

        # Create a corrupted entry
        corrupted_entry = {
            "event_type": "security_alert",
            "timestamp": datetime.utcnow().isoformat(),
            "correlation_id": "corrupted-entry",
            "action": "POST /alert",
            "resource": "/security",
            "result": "error",
            "details": {"alert": "test"},
            "_checksum": "invalid_checksum_12345",
        }

        with open(logger.current_log_file, "a") as f:
            f.write(json.dumps(corrupted_entry) + "\n")

        # Retrieve entries without integrity verification
        entries = logger.get_entries(verify_integrity=False, limit=10)

        # Both entries should be retrieved
        assert len(entries) == 2, "Both entries should be retrieved when verification is disabled"

        correlation_ids = [e.correlation_id for e in entries]
        assert "valid-entry" in correlation_ids
        assert "corrupted-entry" in correlation_ids

    def test_verify_archived_log_integrity(self, temp_logger):
        """Test integrity verification for archived (compressed) logs."""
        logger = temp_logger

        # Create an archived log file with valid and corrupted entries
        timestamp = datetime.utcnow().strftime("%Y%m%d_%H%M%S")
        archived_file = logger.log_dir / f"audit-{timestamp}.log.gz"

        valid_entry = {
            "event_type": "analysis_created",
            "timestamp": datetime.utcnow().isoformat(),
            "correlation_id": "archived-entry",
            "action": "POST /analyze",
            "resource": "/analyze/text",
            "result": "success",
            "details": {"in_archive": True},
        }
        # Calculate correct checksum for valid entry
        entry_copy = valid_entry.copy()
        json_str = json.dumps(entry_copy, sort_keys=True, ensure_ascii=False)
        valid_entry["_checksum"] = __import__("hashlib").sha256(json_str.encode("utf-8")).hexdigest()

        corrupted_archived = {
            "event_type": "authentication",
            "timestamp": datetime.utcnow().isoformat(),
            "correlation_id": "archived-bad",
            "action": "POST /auth",
            "resource": "/auth",
            "result": "failure",
            "details": {},
            "_checksum": "bad_checksum_11111",
        }

        with gzip.open(archived_file, "wt", encoding="utf-8") as f:
            f.write(json.dumps(valid_entry) + "\n")
            f.write(json.dumps(corrupted_archived) + "\n")

        # Retrieve entries with integrity verification
        with patch("src.utils.audit_logger.logger") as mock_logger:
            entries = logger.get_entries(verify_integrity=True, limit=10)

            # Should get 1 valid entry from archive (the corrupted one is skipped)
            valid_correlation_ids = [e.correlation_id for e in entries]
            assert "archived-entry" in valid_correlation_ids
            assert "archived-bad" not in valid_correlation_ids

            # Warning should be logged for corrupted archived entry
            warning_calls = [call for call in mock_logger.warning.call_args_list
                           if "Integrity check failed" in str(call)]
            assert len(warning_calls) > 0, "Warning should be logged for corrupted archived entry"

    def test_read_log_file_handles_os_error(self, temp_logger):
        """Test handling of OS errors when reading log files."""
        logger = temp_logger

        with patch("src.utils.audit_logger.logger") as mock_logger:
            with patch("builtins.open", side_effect=OSError("Permission denied")):
                entries = logger._read_log_file(
                    Path("/nonexistent/file.log"),
                    None, None, None, None, False
                )
                assert entries == []

                # Error should be logged
                mock_logger.error.assert_called_once()

    def test_read_archived_log_handles_corruption(self, temp_logger):
        """Test handling of corrupted archived log files."""
        logger = temp_logger

        # Create a corrupted gzip file
        timestamp = datetime.utcnow().strftime("%Y%m%d_%H%M%S")
        corrupted_archive = logger.log_dir / f"audit-{timestamp}.log.gz"
        corrupted_archive.write_bytes(b"this is not valid gzip data")

        # Try to read corrupted archive
        entries = logger._read_archived_log_file(
            corrupted_archive,
            None, None, None, None, False
        )

        # Should return empty list without crashing
        assert entries == []

    def test_verify_entry_with_malformed_json(self, temp_logger):
        """Test verification handles malformed JSON gracefully."""
        logger = temp_logger

        # Test various malformed inputs
        malformed_lines = [
            "not json at all",
            "{invalid json",
        ]

        for line in malformed_lines:
            result = logger._verify_entry_integrity(line)
            assert result is False, f"Should return False for malformed line: {line}"
