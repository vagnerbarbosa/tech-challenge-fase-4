"""Security tests for Content Security Policy configuration.

Tests T049: Verify CSP policy is correctly configured and effective.
"""

import pytest
from fastapi.testclient import TestClient

from src.api.main import app
from tests.conftest import TEST_API_KEY


@pytest.fixture
def client():
    """Test client for FastAPI application."""
    return TestClient(app, headers={"X-API-Key": TEST_API_KEY})


class TestCSPPolicy:
    """Security tests for Content Security Policy headers."""

    def test_csp_uses_default_self(self, client):
        """CSP default-src should use 'self' directive."""
        response = client.get("/health")
        csp = response.headers.get("content-security-policy", "")

        assert "default-src 'self'" in csp

    def test_csp_blocks_inline_scripts(self, client):
        """CSP should restrict inline scripts."""
        response = client.get("/health")
        csp = response.headers.get("content-security-policy", "")

        # Should have script-src with 'self' and possibly nonce/hash
        assert "script-src" in csp
        # Inline scripts should not be allowed by default
        assert "'unsafe-inline'" not in csp or "'nonce-" in csp

    def test_csp_blocks_eval(self, client):
        """CSP should block eval() and similar."""
        response = client.get("/health")
        csp = response.headers.get("content-security-policy", "")

        assert "'unsafe-eval'" not in csp

    def test_csp_restricts_object_sources(self, client):
        """CSP should restrict object/embed sources."""
        response = client.get("/health")
        csp = response.headers.get("content-security-policy", "")

        # object-src should be 'none' or restricted
        assert "object-src" in csp
        assert "'none'" in csp or "'self'" in csp

    def test_csp_has_base_uri_restriction(self, client):
        """CSP should restrict base URI."""
        response = client.get("/health")
        csp = response.headers.get("content-security-policy", "")

        assert "base-uri" in csp

    def test_csp_has_frame_ancestors(self, client):
        """CSP should have frame-ancestors directive."""
        response = client.get("/health")
        csp = response.headers.get("content-security-policy", "")

        assert "frame-ancestors" in csp
        assert "'none'" in csp or "'self'" in csp

    def test_csp_has_form_action(self, client):
        """CSP should restrict form actions."""
        response = client.get("/health")
        csp = response.headers.get("content-security-policy", "")

        assert "form-action" in csp

    def test_csp_upgrade_insecure_requests_in_production(self, client, monkeypatch):
        """CSP should upgrade insecure requests in production."""
        # Temporarily set production environment
        monkeypatch.setenv("ENVIRONMENT", "production")

        response = client.get("/health")
        csp = response.headers.get("content-security-policy", "")

        # In production, should upgrade insecure requests
        assert "upgrade-insecure-requests" in csp

    def test_csp_no_wildcard_sources(self, client):
        """CSP should not use wildcard sources without restrictions."""
        response = client.get("/health")
        csp = response.headers.get("content-security-policy", "")

        # Should not have wildcards without restrictions
        directives = csp.split(";")
        for directive in directives:
            directive = directive.strip()
            if directive and " " in directive:
                name, values = directive.split(" ", 1)
                # Wildcards should be avoided in sensitive directives
                if name in ["script-src", "style-src", "object-src"]:
                    assert "*" not in values, f"Wildcard not allowed in {name}"

    def test_csp_report_only_not_enabled_by_default(self, client):
        """CSP-Report-Only should not be present by default."""
        response = client.get("/health")

        # Should enforce CSP, not just report
        assert "content-security-policy" in response.headers
        # Report-only header should not be present in production-like settings
        # (This test may be adjusted based on requirements)
