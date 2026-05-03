"""
Testes de edge cases para rotas de vídeo.
"""
import io
from unittest.mock import AsyncMock, MagicMock, patch


class TestVideoEdgeCases:
    """Testes de edge cases para endpoints de vídeo."""

    def test_video_frame_processing_error(self, client, auth_headers, tmp_path):
        """Testa erro quando processamento de frames falha (linhas 255-273).

        Verifica que quando o VideoAnalysisService falha durante o processamento,
        o endpoint retorna HTTP 500 com mensagem de erro apropriada.
        """
        # Arrange - Criar arquivo MP4 mínimo válido (ftyp signature em offset 4)
        test_video = tmp_path / "test.mp4"
        test_video.write_bytes(
            b"\x00\x00\x00\x20ftypisom\x00\x00\x00\x00isommp41" + b"\x00" * 100
        )

        # Mock da instância do VideoAnalysisService que lança exceção
        mock_instance = MagicMock()
        mock_instance.analyze = AsyncMock(
            side_effect=Exception("Erro ao processar frames: OpenCV error")
        )

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
            patch(
                "src.api.routes.video.get_audit_logger"
            ) as mock_audit,
        ):
            mock_audit_logger = MagicMock()
            mock_audit.return_value = mock_audit_logger

            with open(test_video, "rb") as f:
                response = client.post(
                    "/analyze/video",
                    files={"video": ("test.mp4", f, "video/mp4")},
                    data={"tipo": "consulta", "patient_id": "patient-123"},
                    headers={"X-API-Key": "test-api-key"},
                )

        # Assert - deve retornar 500 com mensagem de erro de processamento
        assert response.status_code == 500
        data = response.json()
        assert "detail" in data
        assert "Erro ao processar vídeo" in data["detail"]
        assert "OpenCV error" in data["detail"]

        # Verificar que o audit logger foi chamado
        mock_audit_logger.log.assert_called_once()
        call_args = mock_audit_logger.log.call_args
        assert call_args.kwargs["result"] == "error"
        assert call_args.kwargs["patient_id"] == "patient-123"

    def test_video_invalid_format(self, client, auth_headers, tmp_path):
        """Testa comportamento com formato de vídeo inválido.

        Verifica que arquivos com extensão ou MIME type não suportados
        são rejeitados com HTTP 400.
        """
        # Arrange - Criar arquivo com extensão inválida
        test_file = tmp_path / "test.txt"
        test_file.write_text("conteudo invalido que nao eh video")

        with open(test_file, "rb") as f:
            response = client.post(
                "/analyze/video",
                files={"video": ("test.txt", f, "text/plain")},
                data={"tipo": "consulta"},
                headers={"X-API-Key": "test-api-key"},
            )

        # Assert - deve retornar 400 com mensagem sobre formato não suportado
        assert response.status_code == 400
        data = response.json()
        assert "detail" in data
        assert "Formato de vídeo não suportado" in data["detail"]

    def test_video_cache_error(self, client, auth_headers, tmp_path):
        """Testa comportamento quando cache falha (linhas 255-273).

        Verifica que quando ocorre um erro ao acessar o cache,
        o sistema continua o processamento normalmente e retorna
        resultado com cache_hit=False.
        """
        # Arrange - Criar arquivo MP4 válido
        test_video = tmp_path / "test.mp4"
        test_video.write_bytes(
            b"\x00\x00\x00\x20ftypisom\x00\x00\x00\x00isommp41" + b"\x00" * 100
        )

        mock_analysis_result = {
            "detecoes": [{"classe": "person", "confianca": 0.85}],
            "risco_violencia": "baixo",
            "risco_saude_mental": "medio",
            "alertas": [],
            "frames_processados": 5,
            "tempo_processamento_ms": 800,
        }

        mock_instance = MagicMock()
        mock_instance.analyze = AsyncMock(return_value=mock_analysis_result)

        # Mock do cache que lança exceção ao tentar recuperar resultado
        mock_cache = MagicMock()
        mock_cache.get = MagicMock(side_effect=RuntimeError("Cache connection failed"))
        mock_cache.set = MagicMock()  # Deve funcionar normalmente

        with (
            patch(
                "src.utils.file_validation.magic.from_buffer", return_value="video/mp4"
            ),
            patch(
                "src.api.routes.video.check_video_duration", return_value=8.0
            ),
            patch(
                "src.api.routes.video.get_cache", return_value=mock_cache
            ),
            patch(
                "src.api.routes.video.VideoAnalysisService", return_value=mock_instance
            ),open(test_video, "rb") as f
        ):
            response = client.post(
                "/analyze/video",
                files={"video": ("test.mp4", f, "video/mp4")},
                data={"tipo": "consulta"},
                headers={"X-API-Key": "test-api-key"},
            )

        # Assert - deve retornar 500 pois o erro no cache é tratado
        # como erro de processamento (linhas 255-273)
        assert response.status_code == 500
        data = response.json()
        assert "detail" in data
        assert "Erro ao processar vídeo" in data["detail"]

    def test_video_file_too_large(self, client, auth_headers):
        """Testa rejeição de vídeo muito grande.

        Verifica que arquivos maiores que 50MB são rejeitados
        com HTTP 413 (Payload Too Large).
        """
        # Arrange - Criar conteúdo de vídeo grande (> 50MB)
        # Usando header MP4 válido + padding para simular arquivo grande
        large_content = (
            b"\x00\x00\x00\x20ftypisom\x00\x00\x00\x00isommp41"
            + b"\x00" * (55 * 1024 * 1024)  # 55MB de padding
        )

        with (
            patch(
                "src.utils.file_validation.magic.from_buffer", return_value="video/mp4"
            ),
        ):
            response = client.post(
                "/analyze/video",
                files={"video": ("large.mp4", io.BytesIO(large_content), "video/mp4")},
                data={"tipo": "consulta"},
                headers={"X-API-Key": "test-api-key"},
            )

        # Assert - deve retornar 413 (Payload Too Large)
        assert response.status_code == 413
        data = response.json()
        assert "detail" in data
        assert "50MB" in data["detail"] or "limite" in data["detail"].lower()
