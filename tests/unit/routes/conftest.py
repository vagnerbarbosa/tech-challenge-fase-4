"""
Fixtures específicas para testes de rotas da API.
"""
# Importar a aplicação
import sys
from collections.abc import Generator
from typing import Any
from unittest.mock import MagicMock, patch

import pytest
from fastapi.testclient import TestClient

sys.path.insert(0, '/home/vagner-barbosa/Documentos/DevZone/tech-challenge-fase-4/src')

from api.main import app


@pytest.fixture(scope="session")
def client() -> Generator[TestClient, None, None]:
    """
    Fixture que fornece um TestClient configurado.
    """
    with TestClient(app) as test_client:
        yield test_client


@pytest.fixture
def auth_headers() -> dict[str, str]:
    """
    Fixture que fornece headers de autenticação para testes.
    """
    return {
        "X-API-Key": "test-api-key",
    }


@pytest.fixture
def admin_headers() -> dict[str, str]:
    """
    Fixture que fornece headers de autenticação admin.
    """
    return {
        "X-API-Key": "test-admin-key",
    }


@pytest.fixture(autouse=True)
def mock_azure_services():
    """
    Fixture que automaticamente mocka serviços Azure.
    """
    with patch('src.infrastructure.azure_speech_client.AzureSpeechClient') as mock_speech, \
         patch('src.infrastructure.content_safety_client.ContentSafetyClient') as mock_cs:

        # Configurar mocks padrão
        mock_speech.return_value.transcribe_audio.return_value = {
            "text": "test transcription",
            "language": "pt-BR"
        }
        mock_speech.return_value.transcribe_with_retry.return_value = {
            "transcricao": "test transcription",
            "idioma_detectado": "pt-BR",
            "mock": True
        }
        mock_cs.return_value.analyze_text.return_value = {
            "violence_score": 0.1,
            "self_harm_score": 0.1
        }

        yield


@pytest.fixture(autouse=True)
def mock_auth():
    """
    Fixture que automaticamente mocka a autenticação para testes.
    """
    from src.core.security.models import SecurityContext

    def mock_get_security_context(api_key, request_id, ip_address):
        # Aceitar qualquer API key que comece com 'test-'
        if api_key and api_key.startswith("test-"):
            return SecurityContext(
                is_authenticated=True,
                api_key_id="test-key-id",
                api_key_hash="test-hash",
                roles=["user"],
                permissions=["read", "write"],
                request_id=request_id or "test-request",
                ip_address=ip_address,
                metadata={},
            )
        raise Exception("Invalid API key")

    with patch('src.api.routes.dependencies.get_api_key_validator') as mock_validator:
        mock_instance = MagicMock()
        mock_instance.get_security_context.side_effect = mock_get_security_context
        mock_validator.return_value = mock_instance
        yield


@pytest.fixture
def sample_text_data() -> dict[str, Any]:
    """
    Fixture com dados de texto de exemplo.
    """
    return {
        "text": "Estou me sentindo muito ansiosa e preocupada.",
        "patient_id": "TEST-001",
        "metadata": {"source": "test"}
    }


@pytest.fixture
def sample_audio_file(tmp_path) -> str:
    """
    Fixture que cria um arquivo de áudio temporário para testes.
    """
    import struct
    import wave

    # Criar arquivo WAV válido
    audio_path = tmp_path / "test_audio.wav"

    with wave.open(str(audio_path), 'w') as wav_file:
        wav_file.setnchannels(1)
        wav_file.setsampwidth(2)
        wav_file.setframerate(16000)

        # Gerar 1 segundo de silêncio
        samples = [0] * 16000
        wav_file.writeframes(struct.pack('<' + 'h' * len(samples), *samples))

    return str(audio_path)


@pytest.fixture
def mock_multimodal_fusion():
    """
    Fixture para mockar fusão multimodal.
    """
    return {
        "risco_violencia": 0.3,
        "risco_saude_mental": 0.4,
        "modalidades": ["texto", "audio"],
        "confianca": 0.75
    }
