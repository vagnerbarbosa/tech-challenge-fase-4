"""Integration tests for security headers middleware.

Tests T048: Verify security headers are present in all API responses.
"""

import pytest
from fastapi.testclient import TestClient

from src.api.main import app


@pytest.fixture
def client():
    """Test client for FastAPI application."""
    return TestClient(app)


class TestSecurityHeaders:
    """Integration tests for security headers in API responses."""

    def test_strict_transport_security_header(self, client):
        """Must include Strict-Transport-Security header."""
        response = client.get("/health")

        assert "strict-transport-security" in response.headers
        hsts = response.headers["strict-transport-security"]
        assert "max-age" in hsts
        assert "includeSubDomains" in hsts

    def test_x_content_type_options_header(self, client):
        """Must include X-Content-Type-Options: nosniff header."""
        response = client.get("/health")

        assert response.headers.get("x-content-type-options") == "nosniff"

    def test_x_frame_options_header(self, client):
        """Must include X-Frame-Options: DENY header."""
        response = client.get("/health")

        assert response.headers.get("x-frame-options") == "DENY"

    def test_referrer_policy_header(self, client):
        """Must include Referrer-Policy header."""
        response = client.get("/health")

        assert "referrer-policy" in response.headers
        assert response.headers["referrer-policy"] == "strict-origin-when-cross-origin"

    def test_content_security_policy_header(self, client):
        """Must include Content-Security-Policy header."""
        response = client.get("/health")

        assert "content-security-policy" in response.headers
        csp = response.headers["content-security-policy"]
        # Basic CSP directives
        assert "default-src" in csp
        assert "script-src" in csp
        assert "style-src" in csp

    def test_x_xss_protection_header(self, client):
        """Must include X-XSS-Protection header."""
        response = client.get("/health")

        assert response.headers.get("x-xss-protection") == "1; mode=block"

    def test_permissions_policy_header(self, client):
        """Must include Permissions-Policy header."""
        response = client.get("/health")

        assert "permissions-policy" in response.headers

    def test_security_headers_on_all_endpoints(self, client):
        """Security headers must be present on all endpoints."""
        endpoints = [
            ("/", "GET"),
            ("/health", "GET"),
            ("/analyze/text", "POST"),
        ]

        required_headers = [
            "strict-transport-security",
            "x-content-type-options",
            "x-frame-options",
            "referrer-policy",
            "content-security-policy",
            "x-xss-protection",
            "permissions-policy",
        ]

        for path, method in endpoints:
            if method == "GET":
                response = client.get(path)
            elif method == "POST":
                response = client.post(path, json={"texto": "test"})
            else:
                continue

            for header in required_headers:
                assert header in response.headers, f"Missing {header} on {path}"

    def test_no_server_header_version_disclosure(self, client):
        """Should not expose detailed server version information."""
        response = client.get("/health")

        # Server header should not contain detailed version info
        server = response.headers.get("server", "")
        if server:
            # Should not expose Python version or detailed framework version
            assert "python" not in server.lower() or "uvicorn" in server.lower()
