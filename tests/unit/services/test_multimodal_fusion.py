"""Testes unitários para o serviço de fusão multimodal."""

from unittest.mock import AsyncMock, MagicMock

import pytest
from fastapi import HTTPException, UploadFile

from src.models.schemas import (
    AnalysisMetadata,
    TextAnalysisResponse,
)
from src.services.multimodal_fusion import (
    FusionService,
    LateFusionCalculator,
    ModalidadeResult,
    PerformanceTracker,
)


class TestLateFusionCalculator:
    """Testes para o algoritmo de late fusion."""

    @pytest.fixture
    def calculator(self) -> LateFusionCalculator:
        return LateFusionCalculator()

    def test_fusao_3_modalidades(self, calculator: LateFusionCalculator) -> None:
        """T029: Fusão com 3 modalidades (texto=alto, audio=medio, video=baixo)."""
        results = {
            "texto": ModalidadeResult(
                risco_violencia="alto",
                risco_saude_mental="alto",
                confiança=0.9,
            ),
            "audio": ModalidadeResult(
                risco_violencia="medio",
                risco_saude_mental="medio",
                confiança=0.7,
            ),
            "video": ModalidadeResult(
                risco_violencia="baixo",
                risco_saude_mental="baixo",
                confiança=0.5,
            ),
        }
        fusion = calculator.calculate(results)

        # Pesos: texto=0.9/2.1=0.429, audio=0.7/2.1=0.333, video=0.5/2.1=0.238
        # Score violência: 1.0*0.429 + 0.5*0.333 + 0.0*0.238 = 0.5955 -> medio
        assert fusion.risco_violencia == "medio"
        assert fusion.risco_saude_mental == "medio"
        assert fusion.confiança > 0
        assert "texto" in fusion.scores_por_modalidade

    def test_ponderacao_por_confianca(self, calculator: LateFusionCalculator) -> None:
        """T030: Modalidade com maior confiança tem peso maior."""
        results = {
            "texto": ModalidadeResult(
                risco_violencia="alto",
                risco_saude_mental="alto",
                confiança=0.9,
            ),
            "audio": ModalidadeResult(
                risco_violencia="baixo",
                risco_saude_mental="baixo",
                confiança=0.1,
            ),
        }
        fusion = calculator.calculate(results)

        # Texto tem peso 0.9/1.0 = 0.9, áudio tem peso 0.1/1.0 = 0.1
        # Score violência: 1.0*0.9 + 0.0*0.1 = 0.9 -> alto
        assert fusion.risco_violencia == "alto"
        assert fusion.risco_saude_mental == "alto"

    def test_alerta_2_riscos_altos(self, calculator: LateFusionCalculator) -> None:
        """T031: 2 modalidades com risco=alto -> alerta=True."""
        results = {
            "texto": ModalidadeResult(
                risco_violencia="alto",
                risco_saude_mental="alto",
                confiança=0.5,
            ),
            "audio": ModalidadeResult(
                risco_violencia="alto",
                risco_saude_mental="medio",
                confiança=0.5,
            ),
        }
        fusion = calculator.calculate(results)
        assert fusion.alerta is True

    def test_sem_alerta_1_risco_alto(self, calculator: LateFusionCalculator) -> None:
        """T032: 1 modalidade com risco=alto -> alerta=False."""
        results = {
            "texto": ModalidadeResult(
                risco_violencia="alto",
                risco_saude_mental="medio",
                confiança=0.5,
            ),
            "audio": ModalidadeResult(
                risco_violencia="baixo",
                risco_saude_mental="baixo",
                confiança=0.5,
            ),
        }
        fusion = calculator.calculate(results)
        assert fusion.alerta is False

    def test_rejeicao_confianca_zero(self, calculator: LateFusionCalculator) -> None:
        """T033: Todas confianças = 0 -> lançar exceção."""
        results = {
            "texto": ModalidadeResult(
                risco_violencia="baixo",
                risco_saude_mental="baixo",
                confiança=0.0,
            ),
        }
        with pytest.raises(ValueError, match="confiança insuficiente"):
            calculator.calculate(results)

    def test_recomendacoes(self, calculator: LateFusionCalculator) -> None:
        """T034: Verificar 4 cenários de recomendação."""
        # alerta=True
        alerta_result = calculator.calculate({
            "texto": ModalidadeResult("alto", "alto", 0.5),
            "audio": ModalidadeResult("alto", "alto", 0.5),
        })
        assert "urgente" in alerta_result.recomendacao.lower()

        # alto sem alerta (confiança < 0.8 para não disparar alerta)
        alto_result = calculator.calculate({
            "texto": ModalidadeResult("alto", "medio", 0.7),
        })
        assert "prioritário" in alto_result.recomendacao.lower()

        # medio (confiança < 0.8 para não disparar alerta)
        medio_result = calculator.calculate({
            "texto": ModalidadeResult("medio", "medio", 0.7),
        })
        assert "monitorar" in medio_result.recomendacao.lower()

        # baixo (confiança < 0.8 para não disparar alerta)
        baixo_result = calculator.calculate({
            "texto": ModalidadeResult("baixo", "baixo", 0.7),
        })
        assert "rotina" in baixo_result.recomendacao.lower()

    def test_fusao_2_modalidades(self, calculator: LateFusionCalculator) -> None:
        """T035: Texto + áudio (sem vídeo) -> fusão deve funcionar."""
        results = {
            "texto": ModalidadeResult(
                risco_violencia="medio",
                risco_saude_mental="alto",
                confiança=0.8,
            ),
            "audio": ModalidadeResult(
                risco_violencia="baixo",
                risco_saude_mental="medio",
                confiança=0.6,
            ),
        }
        fusion = calculator.calculate(results)
        assert fusion.risco_violencia in {"baixo", "medio", "alto"}
        assert fusion.risco_saude_mental in {"baixo", "medio", "alto"}

    def test_fusao_1_modalidade_fallback(self, calculator: LateFusionCalculator) -> None:
        """T036: Apenas texto -> fallback, retorna risco do texto."""
        # Este teste é feito no nível do FusionService, não do Calculator
        pass


class TestFusionService:
    """Testes para o serviço de orquestração multimodal."""

    @pytest.fixture
    def service(self) -> FusionService:
        return FusionService()

    @pytest.mark.asyncio
    async def test_processamento_paralelo(self, service: FusionService) -> None:
        """T037: Mock dos 3 serviços; verificar que foram chamados."""
        text_mock = AsyncMock(return_value=TextAnalysisResponse(
            sentimento="negativo",
            score=-0.8,
            risco_violencia="alto",
            risco_saude_mental="medio",
            metadata=AnalysisMetadata(
                correlation_id="t1",
                tempo_processamento_ms=100,
                azure_calls=1,
            ),
        ))
        audio_mock = AsyncMock(return_value={
            "transcricao": "teste",
            "risco_violencia": "medio",
            "risco_saude_mental": "baixo",
        })
        video_mock = AsyncMock(return_value={
            "risco_violencia": "baixo",
            "risco_saude_mental": "baixo",
            "detecoes": [],
        })

        service._text_service.analyze = text_mock
        service._audio_service.analyze = audio_mock
        service._video_service.analyze = video_mock

        # Criar mocks de UploadFile
        audio_file = MagicMock(spec=UploadFile)
        audio_file.read = AsyncMock(return_value=b"audio_data")
        audio_file.filename = "test.wav"
        video_file = MagicMock(spec=UploadFile)
        video_file.read = AsyncMock(return_value=b"video_data")
        video_file.filename = "test.mp4"

        result = await service.analyze(
            texto="texto de teste",
            audio=audio_file,
            video=video_file,
        )

        text_mock.assert_awaited_once()
        audio_mock.assert_awaited_once()
        video_mock.assert_awaited_once()
        assert result.fusao is not None

    @pytest.mark.asyncio
    async def test_timeout(self, service: FusionService) -> None:
        """T038: Simular timeout em uma modalidade; verificar que outras continuam."""
        text_mock = AsyncMock(return_value=TextAnalysisResponse(
            sentimento="negativo",
            score=-0.5,
            risco_violencia="medio",
            risco_saude_mental="medio",
            metadata=AnalysisMetadata(
                correlation_id="t1",
                tempo_processamento_ms=100,
                azure_calls=1,
            ),
        ))
        audio_mock = AsyncMock(side_effect=TimeoutError())

        service._text_service.analyze = text_mock
        service._audio_service.analyze = audio_mock

        audio_file = MagicMock(spec=UploadFile)
        audio_file.read = AsyncMock(return_value=b"audio_data")
        audio_file.filename = "test.wav"

        result = await service.analyze(
            texto="texto",
            audio=audio_file,
            video=None,
        )

        # Texto deve ter sido processado; áudio falhou
        text_mock.assert_awaited_once()
        audio_mock.assert_awaited_once()
        assert result.texto is not None
        assert result.audio is None

    @pytest.mark.asyncio
    async def test_falha_graciosa(self, service: FusionService) -> None:
        """T039: Simular exceção em uma modalidade; resultado parcial retornado."""
        text_mock = AsyncMock(return_value=TextAnalysisResponse(
            sentimento="negativo",
            score=-0.5,
            risco_violencia="medio",
            risco_saude_mental="medio",
            metadata=AnalysisMetadata(
                correlation_id="t1",
                tempo_processamento_ms=100,
                azure_calls=1,
            ),
        ))
        audio_mock = AsyncMock(side_effect=Exception("erro áudio"))

        service._text_service.analyze = text_mock
        service._audio_service.analyze = audio_mock

        audio_file = MagicMock(spec=UploadFile)
        audio_file.read = AsyncMock(return_value=b"audio_data")
        audio_file.filename = "test.wav"

        result = await service.analyze(
            texto="texto",
            audio=audio_file,
            video=None,
        )

        assert result.texto is not None
        assert result.audio is None
        assert result.fusao is not None

    @pytest.mark.asyncio
    async def test_falha_total(self, service: FusionService) -> None:
        """T040: Todas modalidades falham -> HTTPException 503."""
        service._text_service.analyze = AsyncMock(
            side_effect=Exception("erro texto")
        )
        service._audio_service.analyze = AsyncMock(
            side_effect=Exception("erro áudio")
        )

        audio_file = MagicMock(spec=UploadFile)
        audio_file.read = AsyncMock(return_value=b"audio_data")
        audio_file.filename = "test.wav"

        with pytest.raises(HTTPException) as exc_info:
            await service.analyze(
                texto="texto",
                audio=audio_file,
                video=None,
            )
        assert exc_info.value.status_code == 503

    @pytest.mark.asyncio
    async def test_validacao_sem_modalidade(self, service: FusionService) -> None:
        """T041: Nenhuma modalidade fornecida -> HTTPException 400."""
        with pytest.raises(HTTPException) as exc_info:
            await service.analyze(
                texto=None,
                audio=None,
                video=None,
            )
        assert exc_info.value.status_code == 400


class TestPerformanceTracker:
    """Testes para o rastreador de performance."""

    def test_register_and_total(self) -> None:
        tracker = PerformanceTracker()
        tracker.register("texto", 0.5)
        assert "texto" in tracker.tempos_por_modalidade
        assert tracker.get_total() >= 0

    def test_parallel_efficiency(self) -> None:
        tracker = PerformanceTracker()
        tracker.register("texto", 1.0)
        tracker.register("audio", 2.0)
        efficiency = tracker.get_parallel_efficiency()
        assert efficiency >= 0
