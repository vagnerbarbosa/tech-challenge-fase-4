"""LGPD-specific tests for audit log export.

Tests compliance with Brazilian LGPD (Lei Geral de Proteção de Dados)
requirements for audit log export and retention.
"""

from __future__ import annotations

import json
import tempfile
from datetime import datetime, timedelta
from typing import Any

import pytest

from src.models.audit_log import AuditEventType, AuditLogEntry
from src.utils.audit_logger import AuditLogger, get_audit_logger


class TestLGPDCompliance:
    """Tests for LGPD compliance requirements."""

    @pytest.fixture
    def temp_audit_logger(self) -> AuditLogger:
        """Create a temporary audit logger for testing."""
        with tempfile.TemporaryDirectory() as tmpdir:
            # Reset singleton
            AuditLogger._instance = None

            logger = AuditLogger(
                log_dir=str(tmpdir),
                max_size_bytes=1024 * 1024,
                max_age_days=365,
            )

            yield logger

            # Cleanup
            AuditLogger._instance = None

    def test_anpd_format_compliance(self, temp_audit_logger: AuditLogger) -> None:
        """Test that export follows ANPD format requirements.

        LGPD Art. 46 requires that processing operations on personal data
        be recorded with specific information. This test verifies the
        ANPD-compliant export format.
        """
        # Create a sample entry
        entry = temp_audit_logger.log(
            event_type=AuditEventType.DATA_ACCESS,
            correlation_id="anpd-compliance-test",
            action="GET /patient/data",
            resource="/patient/123",
            result="success",
            patient_id="patient-123",
            user_id="doctor-456",
            ip_address="192.168.1.1",
            consent_reference="consent-uuid-789",
        )

        # Export in ANPD format
        export_data = entry.to_anpd_format()

        # Verify required ANPD fields
        required_fields = [
            "idEvento",          # Event ID
            "dataHora",          # Timestamp
            "tipoEvento",        # Event type
            "usuario",           # User (hashed)
            "titularDados",      # Data subject (hashed patient_id)
            "idCorrelacao",      # Correlation ID
            "acao",              # Action
            "recurso",           # Resource
            "resultado",         # Result
            "enderecoIp",        # IP address (hashed)
            "referenciaConsentimento",  # Consent reference
        ]

        for field in required_fields:
            assert field in export_data, f"Missing required ANPD field: {field}"

    def test_sensitive_data_hashing(self, temp_audit_logger: AuditLogger) -> None:
        """Test that sensitive data is properly hashed.

        LGPD requires pseudonymization of personal data in logs.
        """
        raw_patient_id = "patient-raw-id-12345"
        raw_user_id = "user-raw-id-67890"
        raw_ip = "192.168.1.100"

        entry = temp_audit_logger.log(
            event_type=AuditEventType.DATA_ACCESS,
            correlation_id="hash-test",
            action="GET /data",
            resource="/patient/data",
            result="success",
            patient_id=raw_patient_id,
            user_id=raw_user_id,
            ip_address=raw_ip,
        )

        # Verify fields are hashed (not raw values)
        assert entry.patient_id is not None
        assert entry.patient_id != raw_patient_id
        assert entry.patient_id.startswith("sha256:")

        assert entry.user_id is not None
        assert entry.user_id != raw_user_id
        assert entry.user_id.startswith("sha256:")

        assert entry.ip_address is not None
        assert entry.ip_address != raw_ip
        assert entry.ip_address.startswith("sha256:")

    def test_retention_period(self, temp_audit_logger: AuditLogger) -> None:
        """Test that retention period is set correctly.

        LGPD requires data retention limits. This test verifies that
        logs are configured with appropriate retention periods.
        """
        entry = temp_audit_logger.log(
            event_type=AuditEventType.ANALYSIS_CREATED,
            correlation_id="retention-test",
            action="POST /analyze",
            resource="/analyze/text",
            result="success",
        )

        # Verify retention date is set (1 year from timestamp)
        assert entry.data_retention_until is not None
        expected_retention = entry.timestamp + timedelta(days=365)
        # Allow for small time differences during test execution
        diff = abs((entry.data_retention_until - expected_retention).total_seconds())
        assert diff < 60, "Retention period should be approximately 1 year"

    def test_consent_tracking(self, temp_audit_logger: AuditLogger) -> None:
        """Test that consent references are tracked.

        LGPD Art. 7 requires that processing be based on legal basis,
        including consent. This test verifies consent tracking.
        """
        consent_id = "consent-uuid-12345"

        entry = temp_audit_logger.log(
            event_type=AuditEventType.DATA_ACCESS,
            correlation_id="consent-test",
            action="GET /patient/data",
            resource="/patient/data",
            result="success",
            patient_id="patient-123",
            consent_reference=consent_id,
        )

        # Verify consent reference is preserved
        assert entry.consent_reference == consent_id

        # Verify in ANPD export
        anpd_data = entry.to_anpd_format()
        assert anpd_data["referenciaConsentimento"] == consent_id

    def test_purpose_limitation(self, temp_audit_logger: AuditLogger) -> None:
        """Test that audit logs support purpose specification.

        LGPD Art. 7, I requires specification of processing purpose.
        """
        entry = temp_audit_logger.log(
            event_type=AuditEventType.ANALYSIS_CREATED,
            correlation_id="purpose-test",
            action="POST /analyze/text",
            resource="/analyze/text",
            result="success",
            patient_id="patient-123",
            details={
                "purpose": "health_assessment",
                "modalities": ["text"],
                "legal_basis": "legitimate_interest",
            },
        )

        # Verify purpose is recorded in details
        assert entry.details.get("purpose") == "health_assessment"

    def test_data_minimization_in_logs(self, temp_audit_logger: AuditLogger) -> None:
        """Test that logs don't contain unnecessary personal data.

        LGPD Art. 6, IV requires data minimization.
        """
        entry = temp_audit_logger.log(
            event_type=AuditEventType.DATA_ACCESS,
            correlation_id="minimization-test",
            action="GET /data",
            resource="/patient/data",
            result="success",
            patient_id="patient-123",
            details={
                "record_count": 5,
                # Should NOT include actual patient data
            },
        )

        # Verify details don't contain raw personal data
        assert "patient_name" not in entry.details
        assert "patient_email" not in entry.details
        assert "ssn" not in entry.details
        assert "cpf" not in entry.details

    def test_audit_trail_completeness(self, temp_audit_logger: AuditLogger) -> None:
        """Test that audit trail is complete and immutable.

        LGPD Art. 46 requires complete records of processing operations.
        """
        # Log various operations
        operations = [
            (AuditEventType.DATA_ACCESS, "GET", "/patient/1"),
            (AuditEventType.ANALYSIS_CREATED, "POST", "/analyze/text"),
            (AuditEventType.CONSENT_GIVEN, "POST", "/consent"),
            (AuditEventType.DATA_DELETION, "DELETE", "/patient/1"),
        ]

        for i, (event_type, action, resource) in enumerate(operations):
            temp_audit_logger.log(
                event_type=event_type,
                correlation_id=f"completeness-test-{i}",
                action=f"{action} {resource}",
                resource=resource,
                result="success",
                patient_id="patient-123",
            )

        # Retrieve all entries
        entries = temp_audit_logger.get_entries(limit=100)

        # Verify all operations are logged
        correlation_ids = [e.correlation_id for e in entries]
        for i in range(len(operations)):
            assert f"completeness-test-{i}" in correlation_ids

    def test_export_for_regulatory_request(self, temp_audit_logger: AuditLogger) -> None:
        """Test export capability for regulatory requests.

        LGPD Art. 42 requires controller to demonstrate compliance.
        """
        # Create entries across different dates
        for i in range(5):
            temp_audit_logger.log(
                event_type=AuditEventType.DATA_ACCESS,
                correlation_id=f"regulatory-test-{i}",
                action="GET /patient/data",
                resource="/patient/data",
                result="success",
                patient_id=f"patient-{i}",
            )

        # Export all entries
        export = temp_audit_logger.export_for_anpd(format="json")

        # Verify export is usable for regulatory purposes
        assert isinstance(export, list)
        assert len(export) >= 5

        # Verify each entry has required fields
        for entry in export:
            assert entry["idEvento"] is not None
            assert entry["dataHora"] is not None
            assert entry["tipoEvento"] is not None
            assert entry["resultado"] is not None

    def test_patient_data_access_logging(self, temp_audit_logger: AuditLogger) -> None:
        """Test logging of patient data access operations.

        Required for LGPD Art. 46 compliance.
        """
        patient_id = "patient-lgpd-123"

        # Simulate data access
        entry = temp_audit_logger.log_data_access(
            resource="patient_records",
            action="read",
            correlation_id="access-log-test",
            patient_id=patient_id,
            user_id="doctor-456",
            details={
                "records_accessed": 5,
                "access_type": "clinical_review",
            },
        )

        # Verify entry
        assert entry.event_type == AuditEventType.DATA_ACCESS
        assert entry.action == "read_patient_records"
        assert entry.resource == "patient_records"

        # Verify patient_id is hashed
        assert entry.patient_id is not None
        assert entry.patient_id.startswith("sha256:")

    def test_timestamp_accuracy(self, temp_audit_logger: AuditLogger) -> None:
        """Test that timestamps are accurate and in UTC.

        Required for accurate audit trails.
        """
        before_log = datetime.utcnow()

        entry = temp_audit_logger.log(
            event_type=AuditEventType.ANALYSIS_CREATED,
            correlation_id="timestamp-test",
            action="POST /test",
            resource="/test",
            result="success",
        )

        after_log = datetime.utcnow()

        # Verify timestamp is between before and after
        assert before_log <= entry.timestamp <= after_log

        # Verify timestamp has no timezone (naive UTC)
        assert entry.timestamp.tzinfo is None

    def test_ndjson_export_format(self, temp_audit_logger: AuditLogger) -> None:
        """Test NDJSON export format for bulk data transfer.

        Common format for regulatory data exports.
        """
        # Create multiple entries
        for i in range(3):
            temp_audit_logger.log(
                event_type=AuditEventType.DATA_ACCESS,
                correlation_id=f"ndjson-test-{i}",
                action="GET /data",
                resource="/data",
                result="success",
            )

        # Export as NDJSON
        ndjson = temp_audit_logger.export_for_anpd(format="ndjson")

        # Verify NDJSON format (one JSON object per line)
        lines = ndjson.strip().split("\n")
        assert len(lines) >= 3

        for line in lines:
            # Each line should be valid JSON
            obj = json.loads(line)
            assert "idEvento" in obj

    def test_audit_log_integrity(self, temp_audit_logger: AuditLogger) -> None:
        """Test that audit logs have integrity checksums.

        Prevents tampering with audit records.
        """
        entry = temp_audit_logger.log(
            event_type=AuditEventType.ANALYSIS_CREATED,
            correlation_id="integrity-test",
            action="POST /test",
            resource="/test",
            result="success",
        )

        # Verify entry is immutable
        with pytest.raises(Exception):
            entry.action = "modified"

        # Verify checksum is written to log file
        log_files = list(temp_audit_logger.log_dir.glob("audit-*.log"))
        assert len(log_files) > 0

        with open(log_files[0], "r") as f:
            line = f.readline()
            data = json.loads(line)
            assert "_checksum" in data
            assert len(data["_checksum"]) == 64  # SHA-256

    def test_entry_uniqueness(self, temp_audit_logger: AuditLogger) -> None:
        """Test that each audit entry has a unique ID.

        Required for proper audit trail tracking.
        """
        entries = []
        for i in range(5):
            entry = temp_audit_logger.log(
                event_type=AuditEventType.ANALYSIS_CREATED,
                correlation_id=f"uniqueness-test-{i}",
                action="POST /test",
                resource="/test",
                result="success",
            )
            entries.append(entry)

        # Verify all event_ids are unique
        event_ids = [str(e.event_id) for e in entries]
        assert len(event_ids) == len(set(event_ids))


class TestLGPDExportScenarios:
    """Tests for specific LGPD export scenarios."""

    @pytest.fixture
    def populated_logger(self) -> AuditLogger:
        """Create a logger with various types of entries."""
        with tempfile.TemporaryDirectory() as tmpdir:
            AuditLogger._instance = None
            logger = AuditLogger(
                log_dir=str(tmpdir),
                max_size_bytes=1024 * 1024,
                max_age_days=365,
            )

            # Create various LGPD-relevant entries
            logger.log(
                event_type=AuditEventType.CONSENT_GIVEN,
                correlation_id="consent-given-1",
                action="POST /consent",
                resource="/consent",
                result="success",
                patient_id="patient-001",
                consent_reference="consent-ref-001",
                details={"consent_type": "data_processing", "expiry": "2027-01-01"},
            )

            logger.log(
                event_type=AuditEventType.CONSENT_REVOKED,
                correlation_id="consent-revoked-1",
                action="DELETE /consent",
                resource="/consent",
                result="success",
                patient_id="patient-001",
                consent_reference="consent-ref-001",
                details={"revocation_date": "2026-06-01"},
            )

            logger.log(
                event_type=AuditEventType.DATA_DELETION,
                correlation_id="deletion-1",
                action="DELETE /patient/001",
                resource="/patient/001",
                result="success",
                patient_id="patient-001",
                details={"deletion_reason": "patient_request", "records_deleted": 10},
            )

            logger.log(
                event_type=AuditEventType.DATA_EXPORT,
                correlation_id="export-1",
                action="GET /export",
                resource="/patient/002/data",
                result="success",
                patient_id="patient-002",
                details={"export_format": "json", "records_exported": 25},
            )

            yield logger
            AuditLogger._instance = None

    def test_export_includes_consent_events(self, populated_logger: AuditLogger) -> None:
        """Test that export includes consent-related events."""
        entries = populated_logger.get_entries(
            event_type=AuditEventType.CONSENT_GIVEN,
            limit=100,
        )

        assert len(entries) >= 1
        assert any(e.correlation_id == "consent-given-1" for e in entries)

    def test_export_includes_deletion_events(self, populated_logger: AuditLogger) -> None:
        """Test that export includes data deletion events."""
        entries = populated_logger.get_entries(
            event_type=AuditEventType.DATA_DELETION,
            limit=100,
        )

        assert len(entries) >= 1
        assert any(e.correlation_id == "deletion-1" for e in entries)

    def test_export_includes_export_events(self, populated_logger: AuditLogger) -> None:
        """Test that export includes data export events (meta)."""
        entries = populated_logger.get_entries(
            event_type=AuditEventType.DATA_EXPORT,
            limit=100,
        )

        assert len(entries) >= 1
        assert any(e.correlation_id == "export-1" for e in entries)

    def test_full_export_for_anpd_submission(self, populated_logger: AuditLogger) -> None:
        """Test generating a complete export suitable for ANPD submission."""
        export = populated_logger.export_for_anpd(format="json")

        # Verify export structure
        assert isinstance(export, list)
        assert len(export) >= 4  # All entries we created

        # Verify all required ANPD fields are present
        for entry in export:
            assert entry.get("idEvento")
            assert entry.get("dataHora")
            assert entry.get("tipoEvento")
            assert entry.get("acao")
            assert entry.get("resultado")

    def test_filter_by_patient(self, populated_logger: AuditLogger) -> None:
        """Test filtering audit log by patient ID."""
        entries = populated_logger.get_entries(
            patient_id="patient-001",
            limit=100,
        )

        # Should return entries for patient-001 (consent given, revoked, deletion)
        assert len(entries) >= 3

        for entry in entries:
            # Patient ID should be hashed
            assert entry.patient_id is not None


class TestLGPDDataRetention:
    """Tests for LGPD data retention requirements."""

    def test_retention_date_calculated_correctly(self) -> None:
        """Test that retention date is 1 year from entry timestamp."""
        with tempfile.TemporaryDirectory() as tmpdir:
            AuditLogger._instance = None
            logger = AuditLogger(log_dir=str(tmpdir))

            entry = logger.log(
                event_type=AuditEventType.ANALYSIS_CREATED,
                correlation_id="retention-test",
                action="POST /test",
                resource="/test",
                result="success",
            )

            expected_retention = entry.timestamp + timedelta(days=365)
            # Allow 1 second tolerance
            diff = abs((entry.data_retention_until - expected_retention).total_seconds())
            assert diff < 1

            AuditLogger._instance = None

    def test_anpd_format_includes_retention(self) -> None:
        """Test that ANPD format includes retention date."""
        with tempfile.TemporaryDirectory() as tmpdir:
            AuditLogger._instance = None
            logger = AuditLogger(log_dir=str(tmpdir))

            entry = logger.log(
                event_type=AuditEventType.ANALYSIS_CREATED,
                correlation_id="retention-format-test",
                action="POST /test",
                resource="/test",
                result="success",
            )

            anpd_data = entry.to_anpd_format()
            assert "retencaoAte" in anpd_data
            assert anpd_data["retencaoAte"] is not None

            AuditLogger._instance = None
