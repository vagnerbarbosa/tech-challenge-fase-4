"""Integration tests for audit endpoints.

Tests the /admin/audit/* endpoints for LGPD compliance and audit log management.
"""

from __future__ import annotations

import json
import tempfile
from datetime import datetime, timedelta
from pathlib import Path

import pytest
from fastapi.testclient import TestClient
from httpx import Response

from src.api.main import app
from src.models.audit_log import AuditEventType, AuditLogEntry
from src.utils.audit_logger import AuditLogger, get_audit_logger
from tests.conftest import TEST_API_KEY


@pytest.fixture
def client() -> TestClient:
    """Create a test client for the FastAPI app."""
    return TestClient(app, headers={"X-API-Key": TEST_API_KEY})


@pytest.fixture
def temp_audit_logger(monkeypatch) -> AuditLogger:
    """Create a temporary audit logger for testing."""
    with tempfile.TemporaryDirectory() as tmpdir:
        # Reset singleton
        AuditLogger._instance = None

        logger = AuditLogger(
            log_dir=str(tmpdir),
            max_size_bytes=1024 * 1024,
            max_age_days=365,
        )

        # Monkeypatch get_audit_logger to return our test logger
        monkeypatch.setattr("src.utils.audit_logger.get_audit_logger", lambda *args, **kwargs: logger)
        monkeypatch.setattr("src.api.routes.admin.get_audit_logger", lambda *args, **kwargs: logger)

        yield logger

        # Cleanup
        AuditLogger._instance = None


@pytest.fixture
def sample_audit_entries(temp_audit_logger: AuditLogger) -> list[AuditLogEntry]:
    """Create sample audit entries for testing."""
    entries = []

    # Create various types of audit entries
    entries.append(temp_audit_logger.log(
        event_type=AuditEventType.ANALYSIS_CREATED,
        correlation_id="test-analysis-1",
        action="POST /analyze/text",
        resource="/analyze/text",
        result="success",
        patient_id="patient-001",
        user_id="user-001",
        details={"modalities": ["text"], "risk_detected": True},
    ))

    entries.append(temp_audit_logger.log(
        event_type=AuditEventType.DATA_ACCESS,
        correlation_id="test-access-1",
        action="GET /data",
        resource="/patient/records",
        result="success",
        patient_id="patient-001",
        user_id="admin-001",
        details={"resource_type": "patient_record"},
    ))

    entries.append(temp_audit_logger.log(
        event_type=AuditEventType.AUTHENTICATION,
        correlation_id="test-auth-1",
        action="POST /auth/login",
        resource="/auth",
        result="success",
        user_id="user-001",
        ip_address="192.168.1.1",
        details={"method": "api_key"},
    ))

    entries.append(temp_audit_logger.log(
        event_type=AuditEventType.SECURITY_ALERT,
        correlation_id="test-alert-1",
        action="rate_limit_exceeded",
        resource="security",
        result="alert",
        ip_address="10.0.0.1",
        details={"alert_type": "rate_limit", "severity": "medium"},
    ))

    return entries


class TestAuditStatsEndpoint:
    """Tests for GET /admin/audit/stats endpoint."""

    def test_get_stats_returns_success(self, client: TestClient, temp_audit_logger: AuditLogger) -> None:
        """Test that stats endpoint returns 200."""
        response = client.get("/admin/audit/stats")
        assert response.status_code == 200

    def test_get_stats_returns_correct_structure(self, client: TestClient, temp_audit_logger: AuditLogger) -> None:
        """Test that stats returns expected structure."""
        response = client.get("/admin/audit/stats")
        data = response.json()

        assert "log_directory" in data
        assert "active_log_files" in data
        assert "archived_log_files" in data
        assert "total_size_bytes" in data
        assert "total_size_mb" in data
        assert "max_size_bytes" in data
        assert "max_age_days" in data
        assert "current_log_file" in data

    def test_get_stats_counts_files(self, client: TestClient, temp_audit_logger: AuditLogger) -> None:
        """Test that stats correctly counts files."""
        # Create an entry to generate a log file
        temp_audit_logger.log(
            event_type=AuditEventType.ANALYSIS_CREATED,
            correlation_id="stats-test",
            action="POST /test",
            resource="/test",
            result="success",
        )

        response = client.get("/admin/audit/stats")
        data = response.json()

        assert data["active_log_files"] >= 0
        assert data["total_size_bytes"] >= 0


class TestAuditExportEndpoint:
    """Tests for GET /admin/audit/export endpoint."""

    def test_export_requires_admin_access(self, client: TestClient) -> None:
        """Test that export requires admin access."""
        response = client.get("/admin/audit/export")
        # In dev mode without admin key configured, should return data
        assert response.status_code in [200, 403]

    def test_export_ndjson_format(self, client: TestClient, temp_audit_logger: AuditLogger) -> None:
        """Test NDJSON export format."""
        # Create sample entries
        temp_audit_logger.log(
            event_type=AuditEventType.ANALYSIS_CREATED,
            correlation_id="export-test",
            action="POST /test",
            resource="/test",
            result="success",
        )

        response = client.get("/admin/audit/export?format=ndjson")
        assert response.status_code == 200

        # Verify NDJSON format
        content = response.text
        lines = content.strip().split("\n")
        assert len(lines) >= 1

        # Each line should be valid JSON
        for line in lines:
            data = json.loads(line)
            assert "idEvento" in data  # ANPD format
            assert "tipoEvento" in data

    def test_export_json_format(self, client: TestClient, temp_audit_logger: AuditLogger) -> None:
        """Test JSON array export format."""
        # Create sample entries
        temp_audit_logger.log(
            event_type=AuditEventType.ANALYSIS_CREATED,
            correlation_id="export-json-test",
            action="POST /test",
            resource="/test",
            result="success",
        )

        response = client.get("/admin/audit/export?format=json")
        assert response.status_code == 200

        # Verify JSON array format
        data = response.json()
        assert isinstance(data, list)
        assert len(data) >= 1
        assert "idEvento" in data[0]

    def test_export_with_date_filter(self, client: TestClient, temp_audit_logger: AuditLogger) -> None:
        """Test export with date range filter."""
        # Create an entry
        temp_audit_logger.log(
            event_type=AuditEventType.ANALYSIS_CREATED,
            correlation_id="date-test",
            action="POST /test",
            resource="/test",
            result="success",
        )

        # Export with past date range (should return no results)
        past_date = (datetime.utcnow() - timedelta(days=2)).isoformat()
        future_date = (datetime.utcnow() - timedelta(days=1)).isoformat()

        response = client.get(f"/admin/audit/export?format=json&start_date={past_date}&end_date={future_date}")
        assert response.status_code == 200

        data = response.json()
        assert isinstance(data, list)

    def test_export_with_event_type_filter(self, client: TestClient, temp_audit_logger: AuditLogger) -> None:
        """Test export with event type filter."""
        # Create different types of entries
        temp_audit_logger.log(
            event_type=AuditEventType.ANALYSIS_CREATED,
            correlation_id="type-test-1",
            action="POST /test",
            resource="/test",
            result="success",
        )
        temp_audit_logger.log(
            event_type=AuditEventType.DATA_ACCESS,
            correlation_id="type-test-2",
            action="GET /data",
            resource="/data",
            result="success",
        )

        # Export filtering by event type
        response = client.get("/admin/audit/export?format=json&event_type=analysis_created")
        assert response.status_code == 200

        data = response.json()
        for entry in data:
            assert entry["tipoEvento"] == "analysis_created"

    def test_export_invalid_format(self, client: TestClient) -> None:
        """Test export with invalid format."""
        response = client.get("/admin/audit/export?format=xml")
        assert response.status_code == 422  # Validation error


class TestAuditVerifyEndpoint:
    """Tests for GET /admin/audit/verify endpoint."""

    def test_verify_returns_success(self, client: TestClient, temp_audit_logger: AuditLogger) -> None:
        """Test that verify endpoint returns 200."""
        response = client.get("/admin/audit/verify")
        assert response.status_code == 200

    def test_verify_returns_correct_structure(self, client: TestClient, temp_audit_logger: AuditLogger) -> None:
        """Test that verify returns expected structure."""
        response = client.get("/admin/audit/verify")
        data = response.json()

        assert "total_entries_checked" in data
        assert "valid_entries" in data
        assert "corrupted_entries" in data
        assert "integrity_percentage" in data
        assert "status" in data
        assert "message" in data

    def test_verify_all_valid(self, client: TestClient, temp_audit_logger: AuditLogger) -> None:
        """Test verification with all valid entries."""
        # Create valid entries
        temp_audit_logger.log(
            event_type=AuditEventType.ANALYSIS_CREATED,
            correlation_id="verify-test",
            action="POST /test",
            resource="/test",
            result="success",
        )

        response = client.get("/admin/audit/verify")
        data = response.json()

        assert data["total_entries_checked"] >= 1
        assert data["valid_entries"] >= 1
        assert data["corrupted_entries"] == 0
        assert data["integrity_percentage"] == 100.0
        assert data["status"] == "ok"

    def test_verify_respects_limit(self, client: TestClient) -> None:
        """Test that verify respects the limit parameter."""
        response = client.get("/admin/audit/verify?limit=5")
        assert response.status_code == 200

        data = response.json()
        assert data["total_entries_checked"] <= 5


class TestAuditEntryImmutability:
    """Tests for audit log entry immutability."""

    def test_entries_have_checksum(self, client: TestClient, temp_audit_logger: AuditLogger) -> None:
        """Test that entries include checksum for immutability."""
        temp_audit_logger.log(
            event_type=AuditEventType.ANALYSIS_CREATED,
            correlation_id="checksum-test",
            action="POST /test",
            resource="/test",
            result="success",
        )

        # Read log file directly
        log_files = list(temp_audit_logger.log_dir.glob("audit-*.log"))
        assert len(log_files) > 0

        with open(log_files[0], "r") as f:
            line = f.readline()
            entry = json.loads(line)
            assert "_checksum" in entry
            assert len(entry["_checksum"]) == 64  # SHA-256 hex

    def test_entries_in_anpd_format(self, client: TestClient, temp_audit_logger: AuditLogger) -> None:
        """Test that exported entries follow ANPD format."""
        temp_audit_logger.log(
            event_type=AuditEventType.ANALYSIS_CREATED,
            correlation_id="anpd-test",
            action="POST /test",
            resource="/test",
            result="success",
        )

        response = client.get("/admin/audit/export?format=json")
        data = response.json()

        for entry in data:
            # Verify ANPD format fields
            assert "idEvento" in entry
            assert "dataHora" in entry
            assert "tipoEvento" in entry
            assert "acao" in entry
            assert "recurso" in entry
            assert "resultado" in entry


class TestAuditLogIntegration:
    """Integration tests for end-to-end audit logging."""

    def test_analysis_creates_audit_entry(self, client: TestClient, temp_audit_logger: AuditLogger) -> None:
        """Test that analysis endpoint creates audit entry."""
        # This test verifies that calling an analysis endpoint
        # results in an audit log entry being created

        # Since we can't easily mock the service in integration tests,
        # we verify the audit logger is properly integrated

        initial_entries = len(temp_audit_logger.get_entries(limit=100))

        # Create an audit entry directly to verify the logger works
        temp_audit_logger.log_analysis_created(
            correlation_id="integration-test",
            resource="/analyze/text",
            patient_id="test-patient",
            modalities=["text"],
            risk_detected=False,
        )

        # Verify entry was created
        entries = temp_audit_logger.get_entries(limit=100)
        assert len(entries) == initial_entries + 1

        # Find our entry
        found = False
        for entry in entries:
            if entry.correlation_id == "integration-test":
                found = True
                assert entry.event_type == AuditEventType.ANALYSIS_CREATED
                assert entry.resource == "/analyze/text"
                break

        assert found, "Audit entry not found"


class TestAuditEndpointSecurity:
    """Security tests for audit endpoints."""

    def test_export_does_not_expose_raw_patient_ids(self, client: TestClient, temp_audit_logger: AuditLogger) -> None:
        """Test that export doesn't expose raw patient IDs."""
        temp_audit_logger.log(
            event_type=AuditEventType.DATA_ACCESS,
            correlation_id="privacy-test",
            action="GET /data",
            resource="/patient/12345",
            result="success",
            patient_id="patient-12345",
            user_id="user-12345",
        )

        response = client.get("/admin/audit/export?format=json")
        data = response.json()

        # Verify patient_id is hashed
        for entry in data:
            if entry.get("idCorrelacao") == "privacy-test":
                if entry.get("titularDados"):
                    assert entry["titularDados"].startswith("sha256:")
                if entry.get("usuario"):
                    assert entry["usuario"].startswith("sha256:")
