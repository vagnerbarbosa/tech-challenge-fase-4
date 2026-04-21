"""Testes de integração para o endpoint multimodal.

Estes testes requerem que a API esteja rodando (via docker-compose.mock.yml).
"""

import time
from pathlib import Path

import httpx
import pytest

BASE_URL = "http://localhost:8000"


@pytest.fixture
def client() -> httpx.AsyncClient:
    return httpx.AsyncClient(base_url=BASE_URL, timeout=30.0)


@pytest.mark.asyncio
async def test_endpoint_texto_apenas(client: httpx.AsyncClient) -> None:
    """T042: POST /analyze/multimodal com texto=string -> 200."""
    response = await client.post(
        "/analyze/multimodal",
        data={"texto": "Estou me sentindo muito ansiosa e com medo"},
    )
    assert response.status_code == 200
    body = response.json()
    assert "fusao" in body
    assert body["texto"] is not None


@pytest.mark.asyncio
async def test_endpoint_texto_audio(client: httpx.AsyncClient) -> None:
    """T043: Multipart com texto e arquivo de áudio -> 200."""
    # Usar fixture de áudio de teste existente
    audio_path = Path("tests/fixtures/audio_test.wav")
    if not audio_path.exists():
        pytest.skip("Fixture de áudio não encontrada")

    with open(audio_path, "rb") as f:
        response = await client.post(
            "/analyze/multimodal",
            data={"texto": "Estou muito ansiosa"},
            files={"audio": ("audio_test.wav", f, "audio/wav")},
        )
    assert response.status_code == 200
    body = response.json()
    assert "fusao" in body


@pytest.mark.asyncio
async def test_endpoint_3_modalidades(client: httpx.AsyncClient) -> None:
    """T044: Multipart com texto, áudio e vídeo -> 200, verificar estrutura."""
    audio_path = Path("tests/fixtures/audio_test.wav")
    video_path = Path("tests/fixtures/video_test.mp4")
    if not audio_path.exists() or not video_path.exists():
        pytest.skip("Fixtures não encontradas")

    with open(audio_path, "rb") as af, open(video_path, "rb") as vf:
        response = await client.post(
            "/analyze/multimodal",
            data={"texto": "Estou com medo"},
            files={
                "audio": ("audio_test.wav", af, "audio/wav"),
                "video": ("video_test.mp4", vf, "video/mp4"),
            },
        )
    assert response.status_code == 200
    body = response.json()
    assert "fusao" in body
    assert "texto" in body
    assert "audio" in body
    assert "video" in body
    assert "metadata" in body
    assert body["metadata"]["modalidades_processadas"] is not None


@pytest.mark.asyncio
async def test_endpoint_sem_modalidade(client: httpx.AsyncClient) -> None:
    """T045: POST sem nenhuma modalidade -> 400."""
    response = await client.post("/analyze/multimodal", data={})
    assert response.status_code == 400


@pytest.mark.asyncio
async def test_campos_obrigatorios_resposta(client: httpx.AsyncClient) -> None:
    """T046: Verificar que response sempre contém risco_violencia e risco_saude_mental."""
    response = await client.post(
        "/analyze/multimodal",
        data={"texto": "Estou muito ansiosa"},
    )
    assert response.status_code == 200
    body = response.json()
    fusion = body["fusao"]
    assert "risco_violencia" in fusion
    assert "risco_saude_mental" in fusion
    assert fusion["risco_violencia"] in {"baixo", "medio", "alto"}
    assert fusion["risco_saude_mental"] in {"baixo", "medio", "alto"}


@pytest.mark.asyncio
async def test_latencia_15s(client: httpx.AsyncClient) -> None:
    """T047: Medir tempo de resposta com texto apenas (mock)."""
    start = time.perf_counter()
    response = await client.post(
        "/analyze/multimodal",
        data={"texto": "Estou me sentindo muito ansiosa e com medo quando ele chega em casa"},
    )
    elapsed = time.perf_counter() - start
    assert response.status_code == 200
    assert elapsed < 15.0, f"Latência {elapsed:.2f}s excedeu 15s"
