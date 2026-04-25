"""Testes de integração para o endpoint /analyze/video.

Valida upload de vídeos, processamento YOLOv8 e resposta com riscos.
"""

from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from fastapi import status
from httpx import AsyncClient


@pytest.fixture(autouse=True)
def clear_cache_before_tests():
    """Limpa o cache global antes de cada teste."""
    from src.core.cache import get_cache
    cache = get_cache()
    cache.clear_all()
    yield
    cache.clear_all()


class TestVideoEndpointSuccess:
    """Testes de sucesso para análise de vídeo."""

    @pytest.mark.asyncio
    async def test_analyze_video_mock_mode(self, async_client: AsyncClient, tmp_path):
        """Testa análise de vídeo com mock do processamento YOLOv8."""
        # Arrange - Criar arquivo MP4 mínimo válido (ftyp signature em offset 4)
        test_video = tmp_path / "test.mp4"
        test_video.write_bytes(b"\x00\x00\x00\x20ftypisom\x00\x00\x00\x00isommp41" + b"\x00" * 100)

        # Mock do resultado do processamento de vídeo
        mock_analysis_result = {
            "detecoes": [
                {
                    "classe": "person",
                    "confianca": 0.89,
                    "bbox": {"x": 0.1, "y": 0.2, "w": 0.3, "h": 0.5},
                    "frame": 5,
                    "timestamp": 5.0,
                }
            ],
            "risco_violencia": "baixo",
            "risco_saude_mental": "medio",
            "alertas": [
                {
                    "tipo": "postura_incomum",
                    "severidade": "baixa",
                    "descricao": "Postura tensa detectada",
                    "frame_referencia": 5,
                }
            ],
            "frames_processados": 10,
            "tempo_processamento_ms": 1200,
        }

        # Criar mock da instância
        mock_instance = MagicMock()
        mock_instance.analyze = AsyncMock(return_value=mock_analysis_result)

        with (
            patch(
                "src.utils.file_validation.magic.from_buffer", return_value="video/mp4"
            ),
            patch(
                "src.api.routes.video.check_video_duration", return_value=10.0
            ),
            patch(
                "src.api.routes.video.VideoAnalysisService", return_value=mock_instance
            ),
            open(test_video, "rb") as f,
        ):
            response = await async_client.post(
                "/analyze/video",
                files={"video": ("test.mp4", f, "video/mp4")},
                data={"tipo": "consulta", "patient_id": "patient-123"},
            )

        # Assert
        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        assert "risco_violencia" in data
        assert "risco_saude_mental" in data
        assert data["risco_violencia"] in ["baixo", "medio", "alto"]
        assert data["risco_saude_mental"] in ["baixo", "medio", "alto"]
        assert "detecoes" in data
        assert "alertas" in data
        assert "metadata" in data
        assert data["metadata"]["modelo"] == "yolov8n"
        assert data["metadata"]["local_processing"] is True

    @pytest.mark.asyncio
    async def test_analyze_video_no_patient_id(self, async_client: AsyncClient, tmp_path):
        """Testa análise de vídeo sem patient_id (opcional)."""
        # Arrange
        test_video = tmp_path / "test.mp4"
        test_video.write_bytes(b"\x00\x00\x00\x20ftypisom\x00\x00\x00\x00isommp41" + b"\x00" * 100)

        mock_analysis_result = {
            "detecoes": [],
            "risco_violencia": "baixo",
            "risco_saude_mental": "baixo",
            "alertas": [],
            "frames_processados": 5,
            "tempo_processamento_ms": 800,
        }

        mock_instance = MagicMock()
        mock_instance.analyze = AsyncMock(return_value=mock_analysis_result)

        with (
            patch(
                "src.utils.file_validation.magic.from_buffer", return_value="video/mp4"
            ),
            patch(
                "src.api.routes.video.check_video_duration", return_value=5.0
            ),
            patch(
                "src.api.routes.video.VideoAnalysisService", return_value=mock_instance
            ),
            open(test_video, "rb") as f,
        ):
            response = await async_client.post(
                "/analyze/video",
                files={"video": ("test.mp4", f, "video/mp4")},
                data={"tipo": "consulta"},
            )

        # Assert
        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        assert data["risco_violencia"] == "baixo"
        assert data["risco_saude_mental"] == "baixo"

    @pytest.mark.asyncio
    async def test_analyze_video_cache_hit(self, async_client: AsyncClient, tmp_path):
        """Testa que resultados em cache são retornados sem reprocessamento."""
        # Arrange
        test_video = tmp_path / "test.mp4"
        test_video.write_bytes(b"\x00\x00\x00\x20ftypisom\x00\x00\x00\x00isommp41" + b"\x00" * 100)

        mock_cached_result = {
            "risco_violencia": "alto",
            "risco_saude_mental": "alto",
            "detecoes": [
                {
                    "classe": "sangramento",
                    "confianca": 0.75,
                    "bbox": {"x": 0.3, "y": 0.4, "w": 0.2, "h": 0.2},
                    "frame": 3,
                    "timestamp": 3.0,
                }
            ],
            "alertas": [
                {
                    "tipo": "sangramento_detectado",
                    "severidade": "alta",
                    "descricao": "Possível sangramento detectado",
                    "frame_referencia": 3,
                }
            ],
            "frames_processados": 15,
            "duracao": 30.0,
        }

        mock_instance = MagicMock()

        # Criar instância mock do cache
        mock_cache_instance = MagicMock()
        mock_cache_instance.get.return_value = mock_cached_result

        with (
            patch(
                "src.utils.file_validation.magic.from_buffer", return_value="video/mp4"
            ),
            patch(
                "src.api.routes.video.check_video_duration", return_value=30.0
            ),
            patch(
                "src.api.routes.video.get_cache", return_value=mock_cache_instance
            ),
            patch(
                "src.api.routes.video.VideoAnalysisService", return_value=mock_instance
            ),
            open(test_video, "rb") as f,
        ):
            response = await async_client.post(
                "/analyze/video",
                files={"video": ("test.mp4", f, "video/mp4")},
                data={"tipo": "procedimento"},
            )

        # Assert - cache hit não deve chamar analyze
        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        assert data["metadata"]["cache_hit"] is True
        assert data["risco_violencia"] == "alto"
        assert data["risco_saude_mental"] == "alto"
        mock_instance.analyze.assert_not_called()


class TestVideoEndpointValidation:
    """Testes de validação para o endpoint de vídeo."""

    @pytest.mark.asyncio
    async def test_invalid_extension_rejected(self, async_client: AsyncClient, tmp_path):
        """Testa que extensão de vídeo inválida é rejeitada."""
        # Arrange
        test_file = tmp_path / "test.txt"
        test_file.write_text("conteudo invalido")

        with open(test_file, "rb") as f:
            response = await async_client.post(
                "/analyze/video",
                files={"video": ("test.txt", f, "text/plain")},
                data={"tipo": "consulta"},
            )

        # Assert
        assert response.status_code == status.HTTP_400_BAD_REQUEST
        assert "Formato de vídeo não suportado" in response.json()["detail"]

    @pytest.mark.asyncio
    async def test_invalid_mime_type_rejected(self, async_client: AsyncClient, tmp_path):
        """Testa que MIME type de vídeo inválido é rejeitado."""
        # Arrange
        test_video = tmp_path / "test.mp4"
        test_video.write_bytes(b"conteudo fake")

        with (
            patch(
                "src.utils.file_validation.magic.from_buffer",
                return_value="application/octet-stream",
            ),
            open(test_video, "rb") as f,
        ):
            response = await async_client.post(
                "/analyze/video",
                files={"video": ("test.mp4", f, "video/mp4")},
                data={"tipo": "consulta"},
            )

        # Assert
        assert response.status_code == status.HTTP_400_BAD_REQUEST
        assert "Tipo de vídeo não suportado" in response.json()["detail"]

    @pytest.mark.asyncio
    async def test_file_too_large_rejected(self, async_client: AsyncClient, tmp_path):
        """Testa que arquivo de vídeo muito grande é rejeitado pelo middleware (413)."""
        # Arrange - Criar arquivo MP4 maior que MAX_VIDEO_SIZE_MB (50MB)
        test_video = tmp_path / "large.mp4"
        test_video.write_bytes(
            b"\x00\x00\x00\x20ftypisom\x00\x00\x00\x00isommp41" + b"\x00" * (55 * 1024 * 1024)
        )

        with (
            patch(
                "src.utils.file_validation.magic.from_buffer", return_value="video/mp4"
            ),
            open(test_video, "rb") as f,
        ):
            response = await async_client.post(
                "/analyze/video",
                files={"video": ("large.mp4", f, "video/mp4")},
                data={"tipo": "consulta"},
            )

        # Assert - middleware retorna 413 (Payload Too Large)
        assert response.status_code == status.HTTP_413_REQUEST_ENTITY_TOO_LARGE
        assert "Arquivo" in response.json()["detail"]

    @pytest.mark.asyncio
    async def test_video_duration_exceeded(self, async_client: AsyncClient, tmp_path):
        """Testa que vídeo com duração excedida é rejeitado."""
        # Arrange
        test_video = tmp_path / "long.mp4"
        test_video.write_bytes(b"\x00\x00\x00\x20ftypisom\x00\x00\x00\x00isommp41" + b"\x00" * 100)

        from fastapi import HTTPException

        # Criar uma instância de HTTPException para o side_effect
        http_exception = HTTPException(
            status_code=400,
            detail="Vídeo excede o limite de 2 minutos.",
        )

        with (
            patch(
                "src.utils.file_validation.magic.from_buffer", return_value="video/mp4"
            ),
            patch(
                "src.api.routes.video.check_video_duration", side_effect=http_exception
            ),
            open(test_video, "rb") as f,
        ):
            response = await async_client.post(
                "/analyze/video",
                files={"video": ("long.mp4", f, "video/mp4")},
                data={"tipo": "consulta"},
            )

        # Assert
        assert response.status_code == status.HTTP_400_BAD_REQUEST


class TestVideoRequiredFields:
    """Testes para validação de campos obrigatórios na resposta."""

    @pytest.mark.asyncio
    async def test_response_contains_risco_violencia(self, async_client: AsyncClient, tmp_path):
        """Testa que resposta sempre contém campo risco_violencia."""
        # Arrange
        test_video = tmp_path / "test.mp4"
        test_video.write_bytes(b"\x00\x00\x00\x20ftypisom\x00\x00\x00\x00isommp41" + b"\x00" * 100)

        mock_result = {
            "detecoes": [],
            "risco_violencia": "medio",
            "risco_saude_mental": "medio",
            "alertas": [],
            "frames_processados": 5,
            "tempo_processamento_ms": 500,
        }

        mock_instance = MagicMock()
        mock_instance.analyze = AsyncMock(return_value=mock_result)

        with (
            patch(
                "src.utils.file_validation.magic.from_buffer", return_value="video/mp4"
            ),
            patch(
                "src.api.routes.video.check_video_duration", return_value=5.0
            ),
            patch(
                "src.api.routes.video.VideoAnalysisService", return_value=mock_instance
            ),
            open(test_video, "rb") as f,
        ):
            response = await async_client.post(
                "/analyze/video",
                files={"video": ("test.mp4", f, "video/mp4")},
                data={"tipo": "exame"},
            )

        # Assert
        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        assert "risco_violencia" in data
        assert data["risco_violencia"] in ["baixo", "medio", "alto"]
        # Verificar que o campo está presente e válido no schema
        assert isinstance(data["risco_violencia"], str)

    @pytest.mark.asyncio
    async def test_response_contains_risco_saude_mental(self, async_client: AsyncClient, tmp_path):
        """Testa que resposta sempre contém campo risco_saude_mental."""
        # Arrange
        test_video = tmp_path / "test.mp4"
        test_video.write_bytes(b"\x00\x00\x00\x20ftypisom\x00\x00\x00\x00isommp41" + b"\x00" * 100)

        mock_result = {
            "detecoes": [],
            "risco_violencia": "alto",
            "risco_saude_mental": "alto",
            "alertas": [
                {"tipo": "gesto_ameaca", "severidade": "alta", "descricao": "Test", "frame_referencia": 1}
            ],
            "frames_processados": 8,
            "tempo_processamento_ms": 600,
        }

        mock_instance = MagicMock()
        mock_instance.analyze = AsyncMock(return_value=mock_result)

        with (
            patch(
                "src.utils.file_validation.magic.from_buffer", return_value="video/mp4"
            ),
            patch(
                "src.api.routes.video.check_video_duration", return_value=8.0
            ),
            patch(
                "src.api.routes.video.VideoAnalysisService", return_value=mock_instance
            ),
            open(test_video, "rb") as f,
        ):
            response = await async_client.post(
                "/analyze/video",
                files={"video": ("test.mp4", f, "video/mp4")},
                data={"tipo": "consulta"},
            )

        # Assert
        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        assert "risco_saude_mental" in data
        assert data["risco_saude_mental"] in ["baixo", "medio", "alto"]
        assert isinstance(data["risco_saude_mental"], str)


class TestVideoRateLimiting:
    """Testes para rate limiting do endpoint de vídeo."""

    @pytest.mark.asyncio
    async def test_quota_exceeded_returns_429(self, async_client: AsyncClient, tmp_path):
        """Testa retorno 429 quando quota de vídeo é excedida."""
        # Arrange
        test_video = tmp_path / "test.mp4"
        test_video.write_bytes(b"\x00\x00\x00\x20ftypisom\x00\x00\x00\x00isommp41" + b"\x00" * 100)

        with (
            patch(
                "src.utils.file_validation.magic.from_buffer", return_value="video/mp4"
            ),
            patch(
                "src.api.routes.video.check_and_increment_quota",
                side_effect=Exception("Rate limit exceeded"),
            ),
            open(test_video, "rb") as f,
        ):
            response = await async_client.post(
                "/analyze/video",
                files={"video": ("test.mp4", f, "video/mp4")},
                data={"tipo": "consulta"},
            )

        # Assert
        assert response.status_code == status.HTTP_429_TOO_MANY_REQUESTS
        assert "Rate limit exceeded" in response.json()["detail"]

    @pytest.mark.asyncio
    async def test_quota_check_called(self, async_client: AsyncClient, tmp_path):
        """Testa que verificação de quota é chamada corretamente."""
        # Arrange
        test_video = tmp_path / "test.mp4"
        test_video.write_bytes(b"\x00\x00\x00\x20ftypisom\x00\x00\x00\x00isommp41" + b"\x00" * 100)

        mock_result = {
            "detecoes": [],
            "risco_violencia": "baixo",
            "risco_saude_mental": "baixo",
            "alertas": [],
            "frames_processados": 5,
            "tempo_processamento_ms": 500,
        }

        mock_instance = MagicMock()
        mock_instance.analyze = AsyncMock(return_value=mock_result)

        with (
            patch(
                "src.utils.file_validation.magic.from_buffer", return_value="video/mp4"
            ),
            patch(
                "src.api.routes.video.check_video_duration", return_value=5.0
            ),
            patch(
                "src.api.routes.video.check_and_increment_quota", return_value={"daily_remaining": 45}
            ) as mock_quota,
            patch(
                "src.api.routes.video.VideoAnalysisService", return_value=mock_instance
            ),
            open(test_video, "rb") as f,
        ):
            response = await async_client.post(
                "/analyze/video",
                files={"video": ("test.mp4", f, "video/mp4")},
                data={"tipo": "consulta"},
            )

        # Assert
        assert response.status_code == status.HTTP_200_OK
        mock_quota.assert_called_once()


class TestVideoFormatsEndpoint:
    """Testes para endpoint de formatos de vídeo suportados."""

    @pytest.mark.asyncio
    async def test_get_video_formats(self, async_client: AsyncClient):
        """Testa endpoint que retorna formatos de vídeo suportados."""
        response = await async_client.get("/analyze/video/formats")

        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        assert "formatos_suportados" in data
        assert "extensoes" in data
        assert ".mp4" in data["extensoes"]
        assert ".avi" in data["extensoes"]
        assert ".mov" in data["extensoes"]
        assert "tamanho_maximo_mb" in data
        assert data["tamanho_maximo_mb"] == 50

    @pytest.mark.asyncio
    async def test_video_formats_contains_duration_limits(self, async_client: AsyncClient):
        """Testa que formato inclui limites de duração."""
        response = await async_client.get("/analyze/video/formats")

        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        assert "duracao_maxima_segundos" in data
        assert "duracao_maxima_minutos" in data
        assert data["duracao_maxima_segundos"] == 120


class TestVideoCacheEndpoints:
    """Testes para endpoints de cache de vídeo."""

    @pytest.mark.asyncio
    async def test_get_video_cache_stats(self, async_client: AsyncClient):
        """Testa endpoint de estatísticas do cache."""
        response = await async_client.get("/analyze/video/cache/stats")

        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        assert "entries" in data
        assert "ttl_minutes" in data

    @pytest.mark.asyncio
    async def test_clear_video_cache(self, async_client: AsyncClient):
        """Testa endpoint para limpar cache de vídeo."""
        response = await async_client.post("/analyze/video/cache/clear")

        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        assert "message" in data
        assert "limpo" in data["message"].lower()
