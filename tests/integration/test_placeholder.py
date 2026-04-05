"""Placeholder integration tests.

These tests verify that the integration test infrastructure is working.
"""

import pytest


class TestIntegrationSetup:
    """Basic integration test placeholders."""

    def test_integration_environment(self, client):
        """Verify integration test environment is set up."""
        response = client.get("/")
        assert response.status_code == 200
        data = response.json()
        assert "name" in data
        assert "version" in data
