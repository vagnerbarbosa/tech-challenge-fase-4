"""Fixtures e configuração do Pytest.

Fornece fixtures compartilhadas para todos os módulos de teste.
"""

import pytest
from fastapi.testclient import TestClient
from httpx import ASGITransport, AsyncClient

from src.api.main import app


@pytest.fixture(scope="session")
def client():
    """Cria uma instância de TestClient para o app FastAPI."""
    return TestClient(app)


@pytest.fixture(scope="session")
def api_client(client):
    """Alias para a fixture client."""
    return client


@pytest.fixture
async def async_client():
    """Cria uma instância de AsyncClient para testes async."""
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as ac:
        yield ac


@pytest.fixture
def sample_text():
    """Texto de exemplo para testes."""
    return "Estou me sentindo ansiosa e com medo"


@pytest.fixture
def sample_analysis_result():
    """Resultado de análise de exemplo para testes."""
    return {
        "risco_violencia": 0.2,
        "risco_saude_mental": 0.7,
        "sentimento": "negativo",
        "confianca": 0.85,
    }
