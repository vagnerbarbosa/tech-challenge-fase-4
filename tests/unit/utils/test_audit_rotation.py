"""Testes para rotação de logs de auditoria."""

from __future__ import annotations

import gzip
import json
import tempfile
from datetime import datetime, timedelta
from pathlib import Path
from unittest.mock import patch

import pytest

from src.models.audit_log import AuditEventType
from src.utils.audit_logger import AuditLogger


class TestAuditRotation:
    """Testes para rotação de logs de auditoria."""

    @pytest.fixture
    def temp_logger_small_size(self):
        """Create a temporary audit logger with small max size for testing."""
        with tempfile.TemporaryDirectory() as tmpdir:
            AuditLogger._instance = None
            logger = AuditLogger(
                log_dir=str(tmpdir),
                max_size_bytes=500,  # Very small to trigger rotation quickly
                max_age_days=365,
            )
            yield logger
            AuditLogger._instance = None

    def test_rotate_on_file_size(self, temp_logger_small_size):
        """T023: Testar rotação de logs quando arquivo excede tamanho."""
        logger = temp_logger_small_size

        # Create a large entry that will exceed the max size
        large_details = {"data": "x" * 600}  # More than 500 bytes

        # Log an entry that should trigger rotation due to size
        logger.log(
            event_type=AuditEventType.ANALYSIS_CREATED,
            correlation_id="test-rotation-size",
            action="POST /test",
            resource="/test",
            result="success",
            details=large_details,
        )

        # Manually trigger rotation by writing another large entry
        logger._current_size = 600  # Simulate current size being large

        logger.log(
            event_type=AuditEventType.ANALYSIS_CREATED,
            correlation_id="test-rotation-size-2",
            action="POST /test",
            resource="/test",
            result="success",
            details={"small": "data"},
        )

        # Check that archived log file exists
        archived_files = list(logger.log_dir.glob("audit-*.log.gz"))
        assert len(archived_files) > 0, "Should have at least one archived log file"

    def test_rotate_on_file_count(self, temp_logger_small_size):
        """T024: Testar rotação de logs quando número de arquivos excede limite."""
        logger = temp_logger_small_size

        # Create multiple archived log files
        for i in range(5):
            timestamp = (datetime.utcnow() - timedelta(hours=i)).strftime("%Y%m%d_%H%M%S")
            archived_file = logger.log_dir / f"audit-{timestamp}.log.gz"

            # Create a compressed log file with valid content
            test_entry = {
                "event_type": "ANALYSIS_CREATED",
                "timestamp": datetime.utcnow().isoformat(),
                "correlation_id": f"test-{i}",
                "action": "POST /test",
                "resource": "/test",
                "result": "success",
                "details": {},
            }

            with gzip.open(archived_file, "wt", encoding="utf-8") as f:
                f.write(json.dumps(test_entry) + "\n")

        # Verify archived files exist
        archived_files = list(logger.log_dir.glob("audit-*.log.gz"))
        assert len(archived_files) >= 5, "Should have multiple archived files"

        # Clean up old logs should be triggered during rotation
        with patch.object(logger, "_cleanup_old_logs") as mock_cleanup:
            # Create a test file to rotate
            test_log = logger.log_dir / "audit-test.log"
            test_log.write_text(json.dumps({"test": "data"}) + "\n")

            # Trigger rotation
            logger._rotate_log(test_log)

            # Verify cleanup was called
            mock_cleanup.assert_called_once()

    def test_rotate_creates_compressed_archive(self):
        """Test that rotation creates compressed archive."""
        with tempfile.TemporaryDirectory() as tmpdir:
            AuditLogger._instance = None
            logger = AuditLogger(
                log_dir=str(tmpdir),
                max_size_bytes=1024,
            )

            # Create a log file with content
            log_file = Path(tmpdir) / "audit-2024-01-01.log"
            test_content = json.dumps({
                "event_type": "ANALYSIS_CREATED",
                "timestamp": "2024-01-01T00:00:00",
                "correlation_id": "test-compress",
                "action": "POST /test",
                "resource": "/test",
                "result": "success",
            }) + "\n"
            log_file.write_text(test_content)

            # Rotate the log
            logger._rotate_log(log_file)

            # Check that original file is removed
            assert not log_file.exists(), "Original log file should be removed"

            # Check that compressed file exists
            compressed_files = list(Path(tmpdir).glob("audit-*.log.gz"))
            assert len(compressed_files) > 0, "Compressed file should exist"

            # Verify compressed content can be read
            with gzip.open(compressed_files[0], "rt", encoding="utf-8") as f:
                content = f.read()
                assert "test-compress" in content

            AuditLogger._instance = None

    def test_rotate_handles_missing_file(self):
        """Test that rotation handles missing file gracefully."""
        with tempfile.TemporaryDirectory() as tmpdir:
            AuditLogger._instance = None
            logger = AuditLogger(log_dir=str(tmpdir))

            # Try to rotate non-existent file
            non_existent = Path(tmpdir) / "non-existent.log"

            # Should not raise an exception
            logger._rotate_log(non_existent)

            AuditLogger._instance = None

    def test_cleanup_old_logs_removes_expired(self):
        """Test that cleanup removes old archived logs."""
        with tempfile.TemporaryDirectory() as tmpdir:
            AuditLogger._instance = None
            logger = AuditLogger(
                log_dir=str(tmpdir),
                max_age_days=30,  # 30 days retention
            )

            # Create an old archived file (older than max_age_days)
            old_file = Path(tmpdir) / "audit-20240101_000000.log.gz"
            with gzip.open(old_file, "wt") as f:
                f.write("{}")

            # Set modification time to 60 days ago
            old_time = (datetime.now() - timedelta(days=60)).timestamp()
            import os
            os.utime(old_file, (old_time, old_time))

            # Create a recent archived file
            recent_file = Path(tmpdir) / "audit-20241201_000000.log.gz"
            with gzip.open(recent_file, "wt") as f:
                f.write("{}")

            # Run cleanup
            logger._cleanup_old_logs()

            # Old file should be removed
            assert not old_file.exists(), "Old file should be removed"

            # Recent file should remain
            assert recent_file.exists(), "Recent file should remain"

            AuditLogger._instance = None
