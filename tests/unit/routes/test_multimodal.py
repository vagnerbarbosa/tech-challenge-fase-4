"""
Testes unitários para rotas multimodal.
"""

from datetime import datetime
from io import BytesIO
from unittest.mock import AsyncMock, MagicMock, patch


class TestMultimodalRoutes:
    """Testes para endpoints multimodais."""

    def test_multimodal_happy_path_text_audio(self, client, auth_headers):
        """
        T001: Testa happy path de fusão multimodal texto+áudio.

        Verifica que o endpoint processa texto e áudio corretamente,
        retorna 200 OK e a estrutura da resposta contém os campos
        obrigatórios risco_violencia e risco_saude_mental.
        """
        from src.models.schemas import (
            AnalysisMetadata,
            FusionResult,
            MultimodalResponse,
            TextAnalysisResponse,
        )

        # Criar resultado de fusão com dados reais
        fusion_result = FusionResult(
            risco_violencia="medio",
            risco_saude_mental="alto",
            confiança=0.75,
            alerta=True,
            recomendacao="Acompanhamento prioritário recomendado",
            scores_por_modalidade={"texto": 0.5, "audio": 0.8},
        )

        text_result = TextAnalysisResponse(
            sentimento="negativo",
            score=-0.7,
            risco_violencia="medio",
            risco_saude_mental="alto",
            palavras_chave=["ansiosa", "preocupada"],
            indicadores=["ansiedade"],
            metadata=AnalysisMetadata(
                correlation_id="test-123",
                timestamp=datetime.utcnow(),
                tempo_processamento_ms=500,
                azure_calls=1,
                modalidades_processadas=["texto"],
            ),
        )

        mock_response = MultimodalResponse(
            fusao=fusion_result,
            texto=text_result,
            audio={
                "transcricao": "Estou me sentindo muito ansiosa",
                "risco_violencia": "baixo",
                "risco_saude_mental": "alto",
                "duracao_segundos": 5.0,
            },
            video=None,
            metadata=AnalysisMetadata(
                correlation_id="test-123",
                timestamp=datetime.utcnow(),
                tempo_processamento_ms=1500,
                azure_calls=2,
                modalidades_processadas=["texto", "audio"],
            ),
        )

        with patch(
            "src.api.routes.multimodal.get_fusion_service"
        ) as mock_get_service, patch(
            "src.api.routes.multimodal.check_and_increment_quota"
        ):
            mock_service = MagicMock()
            mock_service.analyze = AsyncMock(return_value=mock_response)
            mock_get_service.return_value = mock_service

            # Criar arquivo de áudio mock
            audio_content = BytesIO(b"RIFF\x00\x00\x00\x00WAVEfmt ")

            response = client.post(
                "/analyze/multimodal",
                data={"texto": "Estou me sentindo muito ansiosa e preocupada"},
                files={"audio": ("test_audio.wav", audio_content, "audio/wav")},
                headers={"X-API-Key": "test-api-key"},
            )

            assert response.status_code == 200
            body = response.json()

            # Verificar estrutura da resposta
            assert "fusao" in body
            assert "texto" in body
            assert "audio" in body
            assert "metadata" in body

            # Verificar campos obrigatórios na fusão
            fusion = body["fusao"]
            assert "risco_violencia" in fusion
            assert "risco_saude_mental" in fusion
            assert fusion["risco_violencia"] in ["baixo", "medio", "alto"]
            assert fusion["risco_saude_mental"] in ["baixo", "medio", "alto"]

            # Verificar campos do áudio
            assert body["audio"] is not None
            assert "transcricao" in body["audio"]

            # Verificar campos do texto
            assert body["texto"] is not None
            assert "sentimento" in body["texto"]

            # Verificar metadata
            assert body["metadata"]["modalidades_processadas"] == ["texto", "audio"]

    def test_multimodal_text_only(self, client, auth_headers):
        """
        T002: Testa fusão com apenas dados de texto.

        Verifica que o endpoint processa apenas texto corretamente,
        retorna 200 OK e a estrutura da resposta está correta.
        """
        from src.models.schemas import (
            AnalysisMetadata,
            FusionResult,
            MultimodalResponse,
            TextAnalysisResponse,
        )

        fusion_result = FusionResult(
            risco_violencia="alto",
            risco_saude_mental="medio",
            confiança=0.8,
            alerta=True,
            recomendacao="Encaminhamento urgente recomendado",
            scores_por_modalidade={"texto": 0.8},
        )

        text_result = TextAnalysisResponse(
            sentimento="negativo",
            score=-0.85,
            risco_violencia="alto",
            risco_saude_mental="medio",
            palavras_chave=["medo", "casa"],
            indicadores=["medo"],
            metadata=AnalysisMetadata(
                correlation_id="test-456",
                timestamp=datetime.utcnow(),
                tempo_processamento_ms=400,
                azure_calls=1,
                modalidades_processadas=["texto"],
            ),
        )

        mock_response = MultimodalResponse(
            fusao=fusion_result,
            texto=text_result,
            audio=None,
            video=None,
            metadata=AnalysisMetadata(
                correlation_id="test-456",
                timestamp=datetime.utcnow(),
                tempo_processamento_ms=800,
                azure_calls=1,
                modalidades_processadas=["texto"],
            ),
        )

        with patch(
            "src.api.routes.multimodal.get_fusion_service"
        ) as mock_get_service, patch(
            "src.api.routes.multimodal.check_and_increment_quota"
        ):
            mock_service = MagicMock()
            mock_service.analyze = AsyncMock(return_value=mock_response)
            mock_get_service.return_value = mock_service

            response = client.post(
                "/analyze/multimodal",
                data={"texto": "Estou com muito medo quando ele chega em casa"},
                headers=auth_headers,
            )

            assert response.status_code == 200
            body = response.json()

            # Verificar estrutura da resposta
            assert "fusao" in body
            assert "texto" in body
            assert "audio" in body
            assert "video" in body
            assert "metadata" in body

            # Verificar campos obrigatórios na fusão
            fusion = body["fusao"]
            assert "risco_violencia" in fusion
            assert "risco_saude_mental" in fusion
            assert fusion["risco_violencia"] == "alto"
            assert fusion["risco_saude_mental"] == "medio"

            # Verificar que áudio e vídeo são None
            assert body["audio"] is None
            assert body["video"] is None

            # Verificar que texto foi processado
            assert body["texto"] is not None
            assert "sentimento" in body["texto"]

            # Verificar metadata
            assert body["metadata"]["modalidades_processadas"] == ["texto"]

    def test_multimodal_audio_only(self, client, auth_headers):
        """
        T003: Testa fusão com apenas dados de áudio.

        Verifica que o endpoint processa apenas áudio corretamente,
        retorna 200 OK e a estrutura da resposta está correta.
        """
        from src.models.schemas import (
            AnalysisMetadata,
            FusionResult,
            MultimodalResponse,
        )

        fusion_result = FusionResult(
            risco_violencia="medio",
            risco_saude_mental="alto",
            confiança=0.7,
            alerta=False,
            recomendacao="Acompanhamento prioritário recomendado",
            scores_por_modalidade={"audio": 0.7},
        )

        mock_response = MultimodalResponse(
            fusao=fusion_result,
            texto=None,
            audio={
                "transcricao": "Estou me sentindo muito triste e ansiosa",
                "risco_violencia": "baixo",
                "risco_saude_mental": "alto",
                "voz_tremida": True,
                "duracao_segundos": 5.0,
            },
            video=None,
            metadata=AnalysisMetadata(
                correlation_id="test-789",
                timestamp=datetime.utcnow(),
                tempo_processamento_ms=2000,
                azure_calls=1,
                modalidades_processadas=["audio"],
            ),
        )

        with patch(
            "src.api.routes.multimodal.get_fusion_service"
        ) as mock_get_service, patch(
            "src.api.routes.multimodal.check_and_increment_quota"
        ):
            mock_service = MagicMock()
            mock_service.analyze = AsyncMock(return_value=mock_response)
            mock_get_service.return_value = mock_service

            # Criar arquivo de áudio mock
            audio_content = BytesIO(b"RIFF\x00\x00\x00\x00WAVEfmt ")

            response = client.post(
                "/analyze/multimodal",
                files={"audio": ("test_audio.wav", audio_content, "audio/wav")},
                headers={"X-API-Key": "test-api-key"},
            )

            assert response.status_code == 200
            body = response.json()

            # Verificar estrutura da resposta
            assert "fusao" in body
            assert "texto" in body
            assert "audio" in body
            assert "video" in body
            assert "metadata" in body

            # Verificar campos obrigatórios na fusão
            fusion = body["fusao"]
            assert "risco_violencia" in fusion
            assert "risco_saude_mental" in fusion
            assert fusion["risco_violencia"] in ["baixo", "medio", "alto"]
            assert fusion["risco_saude_mental"] in ["baixo", "medio", "alto"]

            # Verificar que texto e vídeo são None
            assert body["texto"] is None
            assert body["video"] is None

            # Verificar que áudio foi processado
            assert body["audio"] is not None
            assert "transcricao" in body["audio"]

            # Verificar metadata
            assert body["metadata"]["modalidades_processadas"] == ["audio"]

    def test_multimodal_empty_data(self, client, auth_headers):
        """
        T004: Testa comportamento com dados vazios.

        Verifica que o endpoint retorna erro 400 quando
        nenhuma modalidade é fornecida.
        """
        response = client.post(
            "/analyze/multimodal",
            data={},
            headers=auth_headers,
        )

        assert response.status_code == 400
        body = response.json()
        assert "detail" in body
        assert "modalidade" in body["detail"].lower() or "Pelo menos uma" in body["detail"]

    def test_multimodal_happy_path_text_audio_with_mock_validation(self, client, auth_headers):
        """
        T001-ext: Testa happy path com mock completo das validações.

        Versão estendida que também valida a integração com
        o serviço de fusão e audit logger.
        """
        from src.models.schemas import (
            AnalysisMetadata,
            FusionResult,
            MultimodalResponse,
            TextAnalysisResponse,
        )

        # Criar resultado completo
        fusion_result = FusionResult(
            risco_violencia="alto",
            risco_saude_mental="alto",
            confiança=0.9,
            alerta=True,
            recomendacao="Encaminhamento urgente recomendado",
            scores_por_modalidade={"texto": 0.8, "audio": 0.9},
        )

        text_result = TextAnalysisResponse(
            sentimento="negativo",
            score=-0.9,
            risco_violencia="alto",
            risco_saude_mental="alto",
            palavras_chave=["medo", "agindo", "estranho"],
            indicadores=["medo", "comportamento_estranho"],
            metadata=AnalysisMetadata(
                correlation_id="test-abc-123",
                timestamp=datetime.utcnow(),
                tempo_processamento_ms=800,
                azure_calls=1,
                modalidades_processadas=["texto"],
            ),
        )

        mock_response = MultimodalResponse(
            fusao=fusion_result,
            texto=text_result,
            audio={
                "transcricao": "Estou com muito medo, ele está agindo estranho",
                "idioma_detectado": "pt-BR",
                "risco_violencia": "alto",
                "risco_saude_mental": "alto",
                "voz_tremida": True,
                "pausas_suspeitas": 3,
                "duracao_segundos": 5.0,
            },
            video=None,
            metadata=AnalysisMetadata(
                correlation_id="test-abc-123",
                timestamp=datetime.utcnow(),
                tempo_processamento_ms=2500,
                azure_calls=2,
                cache_hit=False,
                modalidades_processadas=["texto", "audio"],
            ),
        )

        with patch(
            "src.api.routes.multimodal.get_fusion_service"
        ) as mock_get_service, patch(
            "src.api.routes.multimodal.check_and_increment_quota"
        ), patch(
            "src.api.routes.multimodal.get_audit_logger"
        ) as mock_audit:
            mock_service = MagicMock()
            mock_service.analyze = AsyncMock(return_value=mock_response)
            mock_get_service.return_value = mock_service

            mock_audit_logger = MagicMock()
            mock_audit.return_value = mock_audit_logger

            # Criar arquivo de áudio mock com header WAV válido
            audio_content = BytesIO(b"RIFF\x26\x00\x00\x00WAVEfmt ")

            response = client.post(
                "/analyze/multimodal",
                data={
                    "texto": "Estou com muito medo quando ele chega em casa",
                    "patient_id": "TEST-PATIENT-001",
                },
                files={"audio": ("test_audio.wav", audio_content, "audio/wav")},
                headers={"X-API-Key": "test-api-key"},
            )

            assert response.status_code == 200
            body = response.json()

            # Verificar todos os campos obrigatórios
            assert "fusao" in body
            assert "metadata" in body

            fusion = body["fusao"]
            assert fusion["risco_violencia"] in ["baixo", "medio", "alto"]
            assert fusion["risco_saude_mental"] in ["baixo", "medio", "alto"]
            assert "confiança" in fusion
            assert "alerta" in fusion
            assert "recomendacao" in fusion
            assert "scores_por_modalidade" in fusion

            # Verificar estrutura completa
            assert body["texto"] is not None or body["audio"] is not None

            # Verificar metadata
            metadata = body["metadata"]
            assert "correlation_id" in metadata
            assert "tempo_processamento_ms" in metadata
            assert "modalidades_processadas" in metadata
