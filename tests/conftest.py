"""Pytest fixtures and configuration.

Provides shared fixtures for all test modules.
"""

import pytest
from fastapi.testclient import TestClient

from src.api.main import app


@pytest.fixture(scope="session")
def client():
    """Create a TestClient instance for the FastAPI app."""
    return TestClient(app)


@pytest.fixture(scope="session")
def api_client(client):
    """Alias for client fixture."""
    return client


@pytest.fixture
def sample_text():
    """Sample text for testing."""
    return "Estou me sentindo ansiosa e com medo"


@pytest.fixture
def sample_analysis_result():
    """Sample analysis result for testing."""
    return {
        "risco_violencia": 0.2,
        "risco_saude_mental": 0.7,
        "sentimento": "negativo",
        "confianca": 0.85,
    }
