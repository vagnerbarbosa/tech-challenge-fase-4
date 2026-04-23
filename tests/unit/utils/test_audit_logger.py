"""Unit tests for audit_logger module.

Tests the AuditLogger class and related functions for LGPD compliance.
"""

from __future__ import annotations

import json
import tempfile
from datetime import datetime, timedelta
from pathlib import Path

import pytest

from src.models.audit_log import AuditEventType, AuditLogEntry
from src.utils.audit_logger import (
    AuditLogger,
    _hash_sensitive_data,
    get_audit_logger,
)


class TestHashSensitiveData:
    """Tests for _hash_sensitive_data function."""

    def test_hashes_string_correctly(self) -> None:
        """Test that sensitive data is hashed with SHA-256 prefix."""
        result = _hash_sensitive_data("sensitive_data")
        assert result.startswith("sha256:")
        assert len(result) == 39  # "sha256:" + 32 hex chars

    def test_empty_string_returns_empty(self) -> None:
        """Test that empty string returns empty."""
        result = _hash_sensitive_data("")
        assert result == ""

    def test_same_input_produces_same_hash(self) -> None:
        """Test that hashing is deterministic."""
        result1 = _hash_sensitive_data("test_data")
        result2 = _hash_sensitive_data("test_data")
        assert result1 == result2

    def test_different_inputs_produce_different_hashes(self) -> None:
        """Test that different inputs produce different hashes."""
        result1 = _hash_sensitive_data("data1")
        result2 = _hash_sensitive_data("data2")
        assert result1 != result2


class TestAuditLoggerSingleton:
    """Tests for AuditLogger singleton pattern."""

    def test_returns_same_instance(self) -> None:
        """Test that get_audit_logger returns singleton."""
        logger1 = get_audit_logger()
        logger2 = get_audit_logger()
        assert logger1 is logger2

    def test_instance_is_audit_logger(self) -> None:
        """Test that instance is AuditLogger type."""
        logger = get_audit_logger()
        assert isinstance(logger, AuditLogger)


class TestAuditLoggerInitialization:
    """Tests for AuditLogger initialization."""

    def test_creates_log_directory(self) -> None:
        """Test that logger creates log directory."""
        with tempfile.TemporaryDirectory() as tmpdir:
            log_dir = Path(tmpdir) / "audit_logs"
            _ = AuditLogger(log_dir=str(log_dir))
            assert log_dir.exists()

    def test_uses_provided_settings(self) -> None:
        """Test that logger uses provided settings."""
        with tempfile.TemporaryDirectory() as tmpdir:
            logger = AuditLogger(
                log_dir=str(tmpdir),
                max_size_bytes=1024,
                max_age_days=30,
            )
            assert logger.max_size_bytes == 1024
            assert logger.max_age_days == 30


class TestAuditLoggerLogEntry:
    """Tests for logging audit entries."""

    @pytest.fixture
    def temp_logger(self) -> AuditLogger:
        """Create a temporary audit logger for testing."""
        with tempfile.TemporaryDirectory() as tmpdir:
            # Reset singleton for test
            AuditLogger._instance = None
            logger = AuditLogger(
                log_dir=str(tmpdir),
                max_size_bytes=1024 * 1024,  # 1MB
                max_age_days=365,
            )
            yield logger
            # Cleanup
            AuditLogger._instance = None

    def test_log_creates_entry(self, temp_logger: AuditLogger) -> None:
        """Test that log creates an audit entry."""
        entry = temp_logger.log(
            event_type=AuditEventType.ANALYSIS_CREATED,
            correlation_id="test-123",
            action="POST /test",
            resource="/test",
            result="success",
            patient_id="patient-123",
        )

        assert isinstance(entry, AuditLogEntry)
        assert entry.event_type == AuditEventType.ANALYSIS_CREATED
        assert entry.correlation_id == "test-123"
        assert entry.result == "success"

    def test_log_hashes_patient_id(self, temp_logger: AuditLogger) -> None:
        """Test that patient_id is hashed."""
        entry = temp_logger.log(
            event_type=AuditEventType.DATA_ACCESS,
            correlation_id="test-123",
            action="GET /data",
            resource="/data",
            result="success",
            patient_id="patient-123",
        )

        assert entry.patient_id is not None
        assert entry.patient_id.startswith("sha256:")
        assert entry.patient_id != "patient-123"

    def test_log_hashes_user_id(self, temp_logger: AuditLogger) -> None:
        """Test that user_id is hashed."""
        entry = temp_logger.log(
            event_type=AuditEventType.DATA_ACCESS,
            correlation_id="test-123",
            action="GET /data",
            resource="/data",
            result="success",
            user_id="user-123",
        )

        assert entry.user_id is not None
        assert entry.user_id.startswith("sha256:")
        assert entry.user_id != "user-123"

    def test_log_hashes_ip_address(self, temp_logger: AuditLogger) -> None:
        """Test that ip_address is hashed."""
        entry = temp_logger.log(
            event_type=AuditEventType.DATA_ACCESS,
            correlation_id="test-123",
            action="GET /data",
            resource="/data",
            result="success",
            ip_address="192.168.1.1",
        )

        assert entry.ip_address is not None
        assert entry.ip_address.startswith("sha256:")
        assert entry.ip_address != "192.168.1.1"

    def test_log_writes_to_file(self, temp_logger: AuditLogger) -> None:
        """Test that log entry is written to file."""
        temp_logger.log(
            event_type=AuditEventType.ANALYSIS_CREATED,
            correlation_id="test-123",
            action="POST /test",
            resource="/test",
            result="success",
        )

        # Read the log file
        log_files = list(temp_logger.log_dir.glob("audit-*.log"))
        assert len(log_files) > 0

        with open(log_files[0]) as f:
            content = f.read()
            assert "test-123" in content

    def test_log_includes_checksum(self, temp_logger: AuditLogger) -> None:
        """Test that log entry includes integrity checksum."""
        temp_logger.log(
            event_type=AuditEventType.ANALYSIS_CREATED,
            correlation_id="test-123",
            action="POST /test",
            resource="/test",
            result="success",
        )

        # Read the log file
        log_files = list(temp_logger.log_dir.glob("audit-*.log"))
        with open(log_files[0]) as f:
            line = f.readline()
            entry = json.loads(line)
            assert "_checksum" in entry
            assert len(entry["_checksum"]) == 64  # SHA-256 hex length


class TestAuditLoggerLogHelperMethods:
    """Tests for helper logging methods."""

    @pytest.fixture
    def temp_logger(self) -> AuditLogger:
        """Create a temporary audit logger for testing."""
        with tempfile.TemporaryDirectory() as tmpdir:
            AuditLogger._instance = None
            logger = AuditLogger(log_dir=str(tmpdir))
            yield logger
            AuditLogger._instance = None

    def test_log_auth_success(self, temp_logger: AuditLogger) -> None:
        """Test log_auth for successful authentication."""
        entry = temp_logger.log_auth(
            success=True,
            correlation_id="auth-123",
            user_id="user-123",
            ip_address="192.168.1.1",
        )

        assert entry.event_type == AuditEventType.AUTHENTICATION
        assert entry.result == "success"
        assert entry.action == "authentication"

    def test_log_auth_failure(self, temp_logger: AuditLogger) -> None:
        """Test log_auth for failed authentication."""
        entry = temp_logger.log_auth(
            success=False,
            correlation_id="auth-123",
            user_id="user-123",
            ip_address="192.168.1.1",
            reason="invalid_credentials",
        )

        assert entry.event_type == AuditEventType.AUTHORIZATION_FAILURE
        assert entry.result == "denied"
        assert entry.details.get("reason") == "invalid_credentials"

    def test_log_data_access(self, temp_logger: AuditLogger) -> None:
        """Test log_data_access method."""
        entry = temp_logger.log_data_access(
            resource="patient_records",
            action="read",
            correlation_id="access-123",
            patient_id="patient-123",
            user_id="user-123",
        )

        assert entry.event_type == AuditEventType.DATA_ACCESS
        assert entry.action == "read_patient_records"
        assert entry.resource == "patient_records"

    def test_log_analysis_created(self, temp_logger: AuditLogger) -> None:
        """Test log_analysis_created method."""
        entry = temp_logger.log_analysis_created(
            correlation_id="analysis-123",
            resource="/analyze/text",
            patient_id="patient-123",
            modalities=["text"],
            risk_detected=True,
        )

        assert entry.event_type == AuditEventType.ANALYSIS_CREATED
        assert entry.details.get("modalities") == ["text"]
        assert entry.details.get("risk_detected") is True

    def test_log_security_alert(self, temp_logger: AuditLogger) -> None:
        """Test log_security_alert method."""
        entry = temp_logger.log_security_alert(
            alert_type="rate_limit_exceeded",
            severity="high",
            correlation_id="alert-123",
            details={"limit": 60, "current": 61},
        )

        assert entry.event_type == AuditEventType.SECURITY_ALERT
        assert entry.details.get("alert_type") == "rate_limit_exceeded"
        assert entry.details.get("severity") == "high"


class TestAuditLogIntegrity:
    """Tests for log integrity verification."""

    @pytest.fixture
    def temp_logger(self) -> AuditLogger:
        """Create a temporary audit logger for testing."""
        with tempfile.TemporaryDirectory() as tmpdir:
            AuditLogger._instance = None
            logger = AuditLogger(log_dir=str(tmpdir))
            yield logger
            AuditLogger._instance = None

    def test_verify_valid_entry(self, temp_logger: AuditLogger) -> None:
        """Test verification of valid entry."""
        # Write an entry
        temp_logger.log(
            event_type=AuditEventType.ANALYSIS_CREATED,
            correlation_id="test-123",
            action="POST /test",
            resource="/test",
            result="success",
        )

        # Read and verify
        log_files = list(temp_logger.log_dir.glob("audit-*.log"))
        with open(log_files[0]) as f:
            line = f.readline()
            is_valid = temp_logger._verify_entry_integrity(line)
            assert is_valid is True

    def test_verify_tampered_entry(self, temp_logger: AuditLogger) -> None:
        """Test detection of tampered entry."""
        # Create a tampered entry line
        tampered_entry = json.dumps({
            "event_id": "test-123",
            "timestamp": datetime.utcnow().isoformat(),
            "event_type": "analysis_created",
            "correlation_id": "test-123",
            "action": "POST /test",
            "resource": "/test",
            "result": "success",
            "_checksum": "invalid_checksum_12345678901234567890123456789012",
        })

        is_valid = temp_logger._verify_entry_integrity(tampered_entry)
        assert is_valid is False

    def test_verify_missing_checksum(self, temp_logger: AuditLogger) -> None:
        """Test detection of entry without checksum."""
        entry_without_checksum = json.dumps({
            "event_id": "test-123",
            "timestamp": datetime.utcnow().isoformat(),
            "event_type": "analysis_created",
            "correlation_id": "test-123",
            "action": "POST /test",
            "resource": "/test",
            "result": "success",
        })

        is_valid = temp_logger._verify_entry_integrity(entry_without_checksum)
        assert is_valid is False


class TestAuditLogRetrieval:
    """Tests for retrieving audit log entries."""

    @pytest.fixture
    def temp_logger(self) -> AuditLogger:
        """Create a temporary audit logger for testing."""
        with tempfile.TemporaryDirectory() as tmpdir:
            AuditLogger._instance = None
            logger = AuditLogger(log_dir=str(tmpdir))
            yield logger
            AuditLogger._instance = None

    def test_get_entries_returns_logged_entries(self, temp_logger: AuditLogger) -> None:
        """Test retrieving logged entries."""
        # Create entries
        temp_logger.log(
            event_type=AuditEventType.ANALYSIS_CREATED,
            correlation_id="entry-1",
            action="POST /test",
            resource="/test",
            result="success",
        )
        temp_logger.log(
            event_type=AuditEventType.DATA_ACCESS,
            correlation_id="entry-2",
            action="GET /data",
            resource="/data",
            result="success",
        )

        # Retrieve entries
        entries = temp_logger.get_entries(limit=10)
        assert len(entries) == 2

    def test_get_entries_filters_by_event_type(self, temp_logger: AuditLogger) -> None:
        """Test filtering by event type."""
        temp_logger.log(
            event_type=AuditEventType.ANALYSIS_CREATED,
            correlation_id="entry-1",
            action="POST /test",
            resource="/test",
            result="success",
        )
        temp_logger.log(
            event_type=AuditEventType.DATA_ACCESS,
            correlation_id="entry-2",
            action="GET /data",
            resource="/data",
            result="success",
        )

        entries = temp_logger.get_entries(
            event_type=AuditEventType.ANALYSIS_CREATED,
            limit=10,
        )
        assert len(entries) == 1
        assert entries[0].event_type == AuditEventType.ANALYSIS_CREATED

    def test_get_entries_respects_limit(self, temp_logger: AuditLogger) -> None:
        """Test that limit is respected."""
        for i in range(5):
            temp_logger.log(
                event_type=AuditEventType.ANALYSIS_CREATED,
                correlation_id=f"entry-{i}",
                action="POST /test",
                resource="/test",
                result="success",
            )

        entries = temp_logger.get_entries(limit=3)
        assert len(entries) == 3


class TestAuditLogExport:
    """Tests for audit log export functionality."""

    @pytest.fixture
    def temp_logger(self) -> AuditLogger:
        """Create a temporary audit logger for testing."""
        with tempfile.TemporaryDirectory() as tmpdir:
            AuditLogger._instance = None
            logger = AuditLogger(log_dir=str(tmpdir))
            yield logger
            AuditLogger._instance = None

    def test_export_ndjson_format(self, temp_logger: AuditLogger) -> None:
        """Test NDJSON export format."""
        temp_logger.log(
            event_type=AuditEventType.ANALYSIS_CREATED,
            correlation_id="export-test",
            action="POST /test",
            resource="/test",
            result="success",
        )

        result = temp_logger.export_for_anpd(format="ndjson")
        assert isinstance(result, str)
        lines = result.strip().split("\n")
        assert len(lines) >= 1

        # Verify each line is valid JSON
        for line in lines:
            data = json.loads(line)
            assert "idEvento" in data  # ANPD format

    def test_export_json_format(self, temp_logger: AuditLogger) -> None:
        """Test JSON array export format."""
        temp_logger.log(
            event_type=AuditEventType.ANALYSIS_CREATED,
            correlation_id="export-test",
            action="POST /test",
            resource="/test",
            result="success",
        )

        result = temp_logger.export_for_anpd(format="json")
        assert isinstance(result, list)
        assert len(result) >= 1
        assert "idEvento" in result[0]

    def test_export_invalid_format_raises(self, temp_logger: AuditLogger) -> None:
        """Test that invalid format raises error."""
        with pytest.raises(ValueError, match="Unsupported export format"):
            temp_logger.export_for_anpd(format="xml")

    def test_export_filters_by_date(self, temp_logger: AuditLogger) -> None:
        """Test date range filtering in export."""
        # Create entry
        temp_logger.log(
            event_type=AuditEventType.ANALYSIS_CREATED,
            correlation_id="export-test",
            action="POST /test",
            resource="/test",
            result="success",
        )

        # Export with future date range (should return empty)
        future_start = datetime.utcnow() + timedelta(days=1)
        future_end = datetime.utcnow() + timedelta(days=2)
        result = temp_logger.export_for_anpd(
            start_date=future_start,
            end_date=future_end,
            format="json",
        )
        assert len(result) == 0


class TestAuditLoggerStats:
    """Tests for audit logger statistics."""

    @pytest.fixture
    def temp_logger(self) -> AuditLogger:
        """Create a temporary audit logger for testing."""
        with tempfile.TemporaryDirectory() as tmpdir:
            AuditLogger._instance = None
            logger = AuditLogger(log_dir=str(tmpdir))
            yield logger
            AuditLogger._instance = None

    def test_get_stats_returns_dict(self, temp_logger: AuditLogger) -> None:
        """Test that get_stats returns dictionary."""
        stats = temp_logger.get_stats()
        assert isinstance(stats, dict)
        assert "log_directory" in stats
        assert "active_log_files" in stats
        assert "archived_log_files" in stats

    def test_stats_counts_files(self, temp_logger: AuditLogger) -> None:
        """Test that stats counts files correctly."""
        # Create a log entry to generate a file
        temp_logger.log(
            event_type=AuditEventType.ANALYSIS_CREATED,
            correlation_id="stats-test",
            action="POST /test",
            resource="/test",
            result="success",
        )

        stats = temp_logger.get_stats()
        assert stats["active_log_files"] >= 0
        assert stats["total_size_bytes"] >= 0


class TestAuditLogImmutability:
    """Tests for log entry immutability."""

    def test_audit_log_entry_is_frozen(self) -> None:
        """Test that AuditLogEntry is immutable."""
        entry = AuditLogEntry(
            event_type=AuditEventType.ANALYSIS_CREATED,
            correlation_id="test-123",
            action="POST /test",
            resource="/test",
            result="success",
        )

        # Attempting to modify should raise error
        with pytest.raises(Exception):  # pydantic ValidationError or similar
            entry.action = "modified"

    def test_model_config_frozen(self) -> None:
        """Test that model config sets frozen=True."""
        from src.models.audit_log import AuditLogEntry

        assert AuditLogEntry.model_config.get("frozen") is True
