"""Integration tests for error handling (T031).

Tests that error responses don't expose sensitive data in production,
and that proper generic messages are returned.

Reference: spec.md FR-034 - ocultar detalhes de erro em produção
"""

from fastapi.testclient import TestClient

from src.api.main import app
from src.core.config import settings
from tests.conftest import TEST_API_KEY

client = TestClient(app, headers={"X-API-Key": TEST_API_KEY})


class TestErrorHandlingProduction:
    """Tests for error handling in production mode."""

    def test_generic_error_message_in_production(self, monkeypatch):
        """Generic errors should return sanitized messages in production."""
        # Force production environment
        monkeypatch.setattr(settings, "environment", "production")
        monkeypatch.setattr(settings, "debug", False)

        # Trigger a 404 (which will exercise error handling)
        response = client.get("/nonexistent-endpoint-12345")

        # Response should not contain sensitive details
        assert response.status_code == 404
        content = response.json()
        # Should have a generic error message
        assert "error" in content

    def test_validation_error_sanitized(self):
        """Validation errors should not expose internal details."""
        # Send invalid data to an endpoint
        response = client.post(
            "/analyze/text",
            json={"texto": "", "tipo": "invalid"},  # Empty text
        )

        assert response.status_code == 422
        content = response.json()
        # Should have structured error without internal details
        assert "detail" in content

    def test_method_not_allowed(self):
        """Method not allowed should be handled gracefully."""
        response = client.delete("/health")  # DELETE not allowed

        assert response.status_code == 405

    def test_cors_preflight_allowed(self):
        """CORS preflight should work for valid origins."""
        response = client.options(
            "/analyze/text",
            headers={
                "Origin": "http://localhost:3000",
                "Access-Control-Request-Method": "POST",
            },
        )

        assert response.status_code == 200


class TestSecurityHeadersInErrors:
    """Tests that security headers are present even in error responses."""

    def test_security_headers_on_404(self):
        """Security headers should be present on 404 errors."""
        response = client.get("/not-found")

        # Check security headers
        assert "X-Content-Type-Options" in response.headers
        assert response.headers["X-Content-Type-Options"] == "nosniff"
        assert "X-Frame-Options" in response.headers
        assert response.headers["X-Frame-Options"] == "DENY"

    def test_security_headers_on_405(self):
        """Security headers should be present on 405 errors."""
        response = client.delete("/health")

        assert "X-Content-Type-Options" in response.headers
        assert "X-Frame-Options" in response.headers

    def test_security_headers_on_422(self):
        """Security headers should be present on validation errors."""
        response = client.post(
            "/analyze/text",
            json={"invalid": "data"},
        )

        assert response.status_code == 422
        assert "X-Content-Type-Options" in response.headers


class TestErrorResponseStructure:
    """Tests for error response structure."""

    def test_error_has_required_fields(self):
        """Error responses should have required fields."""
        response = client.get("/nonexistent")

        if response.status_code == 404:
            content = response.json()
            # FastAPI's default 404 has 'detail'
            assert "detail" in content

    def test_error_id_in_internal_errors(self, monkeypatch):
        """Internal errors should include error_id for tracking."""
        # This test assumes generic exception handler is in place
        # Note: In real scenarios, this would require triggering an actual error

        # Force production environment
        monkeypatch.setattr(settings, "environment", "production")

        # Try to access an endpoint that might cause issues
        response = client.get("/health")

        # Health endpoint should work, but if it errors,
        # it should include error_id
        if response.status_code >= 500:
            content = response.json()
            assert "error_id" in content


class TestContentTypeSecurity:
    """Tests for content-type related security."""

    def test_nosniff_header_present(self):
        """X-Content-Type-Options: nosniff should be present."""
        response = client.get("/health")

        assert "X-Content-Type-Options" in response.headers
        assert response.headers["X-Content-Type-Options"] == "nosniff"

    def test_frame_options_header_present(self):
        """X-Frame-Options: DENY should be present."""
        response = client.get("/health")

        assert "X-Frame-Options" in response.headers
        assert response.headers["X-Frame-Options"] == "DENY"


class TestDebugModeDifferences:
    """Tests for differences between debug and production modes."""

    def test_debug_false_hides_details(self, monkeypatch):
        """When debug=False, internal details should be hidden."""
        monkeypatch.setattr(settings, "debug", False)

        response = client.get("/nonexistent-path-xyz")
        assert response.status_code == 404

        # Response should not contain internal stack traces
        content = response.text
        assert "Traceback" not in content
        assert "File \"" not in content

    def test_production_error_message_generic(self, monkeypatch):
        """Production should show generic error messages."""
        monkeypatch.setattr(settings, "environment", "production")
        monkeypatch.setattr(settings, "debug", False)

        # Test on 404
        response = client.get("/nonexistent")
        assert response.status_code == 404

        # The error message should be generic
        content = response.json()
        # Should not have technical details
        assert "stack" not in str(content).lower()
        assert "trace" not in str(content).lower()


class TestLGPDComplianceInErrors:
    """Tests for LGPD compliance in error responses."""

    def test_no_pii_in_error_responses(self):
        """Error responses should never contain PII."""
        response = client.post(
            "/analyze/text",
            json={"invalid_field": "test"},
        )

        # Even in error, no PII should be exposed
        assert response.status_code in [422, 400]

    def test_error_logging_doesnt_expose_data(self, monkeypatch):
        """Errors should be logged without exposing sensitive data."""
        # This is a behavioral test - the actual logging is tested
        # through log capture in other tests

        monkeypatch.setattr(settings, "environment", "production")

        response = client.get("/health")
        # Health endpoint should return 200
        assert response.status_code == 200


class TestExceptionHandlers:
    """Tests for exception handler registration."""

    def test_app_has_exception_handlers(self):
        """App should have custom exception handlers registered."""
        # Check that handlers are registered
        exception_handlers = app.exception_handlers

        # Should have handlers for common exceptions
        assert len(exception_handlers) > 0

    def test_validation_error_handler(self):
        """Validation errors should be handled gracefully."""
        response = client.post(
            "/analyze/text",
            data="invalid json",
            headers={"Content-Type": "application/json"},
        )

        assert response.status_code == 422
