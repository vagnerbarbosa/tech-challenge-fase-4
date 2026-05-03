"""
Fixtures para testes E2E com Docker.
"""
import subprocess
import time

import pytest
import requests

# Configurações E2E
E2E_API_URL = "http://localhost:9000"
MOCK_SERVER_URL = "http://localhost:3004"
ADMIN_API_KEY = "test-admin-key"


@pytest.fixture(scope="session")
def docker_services():
    """
    Fixture que gerencia os serviços Docker para E2E.
    """
    compose_file = "/home/vagner-barbosa/Documentos/DevZone/tech-challenge-fase-4/tests/e2e/fixtures/docker-compose.e2e.yml"

    # Subir serviços
    subprocess.run(
        ["docker-compose", "-f", compose_file, "up", "-d", "--build"],
        check=True,
        capture_output=True
    )

    # Aguardar serviços ficarem prontos
    max_retries = 30
    for _ in range(max_retries):
        try:
            response = requests.get(f"{E2E_API_URL}/health", timeout=5)
            if response.status_code == 200:
                break
        except requests.exceptions.ConnectionError:
            pass
        time.sleep(2)
    else:
        # Derrubar serviços se não conseguir conectar
        subprocess.run(
            ["docker-compose", "-f", compose_file, "down", "-v"],
            capture_output=True
        )
        pytest.fail("Não foi possível conectar à API E2E")

    yield

    # Derrubar serviços no teardown
    subprocess.run(
        ["docker-compose", "-f", compose_file, "down", "-v"],
        capture_output=True
    )


@pytest.fixture
def api_url() -> str:
    """
    URL base da API E2E.
    """
    return E2E_API_URL


@pytest.fixture
def mock_server_url() -> str:
    """
    URL do mock server WireMock.
    """
    return MOCK_SERVER_URL


@pytest.fixture
def admin_headers() -> dict[str, str]:
    """
    Headers de autenticação admin para E2E.
    """
    return {
        "X-API-Key": ADMIN_API_KEY,
        "Content-Type": "application/json"
    }


@pytest.fixture
def e2e_client():
    """
    Client HTTP configurado para E2E.
    """
    session = requests.Session()
    session.headers.update({
        "X-API-Key": ADMIN_API_KEY,
        "Content-Type": "application/json"
    })
    yield session
    session.close()


@pytest.fixture
def sample_audio_path() -> str:
    """
    Path para o arquivo de áudio de exemplo.
    """
    return "/home/vagner-barbosa/Documentos/DevZone/tech-challenge-fase-4/tests/e2e/fixtures/sample_files/sample.wav"


@pytest.fixture
def sample_text_payload() -> dict:
    """
    Payload de exemplo para análise de texto.
    """
    return {
        "text": "Estou me sentindo muito ansiosa e preocupada com a gravidez.",
        "patient_id": "E2E-TEST-001",
        "metadata": {"source": "e2e-test"}
    }
