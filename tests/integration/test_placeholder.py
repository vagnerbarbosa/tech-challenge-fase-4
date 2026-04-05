"""Testes de integração placeholder.

Estes testes verificam se a infraestrutura de testes de integração está funcionando.
"""

import pytest


class TestIntegrationSetup:
    """Testes placeholder básicos de integração."""

    def test_integration_environment(self, client):
        """Verifica se o ambiente de testes de integração está configurado."""
        response = client.get("/")
        assert response.status_code == 200
        data = response.json()
        assert "name" in data
        assert "version" in data
