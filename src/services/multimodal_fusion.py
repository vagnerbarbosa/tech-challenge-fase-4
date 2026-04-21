"""Serviço de fusão multimodal via late fusion ponderado.

Este módulo implementa:
- LateFusionCalculator: algoritmo de fusão ponderada por confiança
- FusionService: orquestração paralela das 3 modalidades
- PerformanceTracker: rastreamento de tempo por modalidade
"""

import asyncio
import os
import time
import uuid
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

from fastapi import HTTPException, UploadFile
from structlog import get_logger

from src.models.schemas import (
    AnalysisMetadata,
    FusionResult,
    MultimodalResponse,
    TextAnalysisResponse,
)
from src.services.audio_analysis import AudioAnalysisService
from src.services.text_analysis import TextAnalysisService
from src.services.video_analysis import VideoAnalysisService

logger = get_logger()

DEFAULT_TIMEOUT_SECONDS = int(os.getenv("MULTIMODAL_TIMEOUT_SECONDS", "30"))


@dataclass
class ModalidadeResult:
    """Resultado normalizado de uma modalidade para fusão."""

    risco_violencia: str
    risco_saude_mental: str
    confiança: float
    raw: Any = None


class LateFusionCalculator:
    """Calcula fusão multimodal via late fusion ponderado por confiança."""

    RISK_SCORES = {"baixo": 0.0, "medio": 0.5, "alto": 1.0}
    SCORE_RISKS = {0.0: "baixo", 0.5: "medio", 1.0: "alto"}

    def calculate(self, results: dict[str, ModalidadeResult]) -> FusionResult:
        """Calcula o resultado de fusão a partir dos resultados das modalidades.

        Args:
            results: Dict mapeando nome da modalidade -> ModalidadeResult

        Returns:
            FusionResult combinado

        Raises:
            ValueError: Se confiança total for zero
        """
        if not results:
            raise ValueError("Nenhuma modalidade para fusão")

        # Mapear riscos para scores
        scores = {
            name: self._risk_to_score(res.risco_violencia)
            for name, res in results.items()
        }
        scores_saude_mental = {
            name: self._risk_to_score(res.risco_saude_mental)
            for name, res in results.items()
        }

        confiances = {name: res.confiança for name, res in results.items()}
        total_confiança = sum(confiances.values())

        if total_confiança == 0:
            raise ValueError(
                "Impossível calcular risco: confiança insuficiente em todas as modalidades"
            )

        # Pesos = confiança / soma_confianças
        pesos = {name: c / total_confiança for name, c in confiances.items()}

        # Score ponderado
        score_fusao = sum(scores[name] * pesos[name] for name in results)
        score_saude_mental = sum(
            scores_saude_mental[name] * pesos[name] for name in results
        )

        # Confiança combinada = média ponderada
        confiança_fusao = sum(confiances[name] * pesos[name] for name in results)

        # Determinar risco combinado
        risco_violencia = self._score_to_risk(score_fusao)
        risco_saude_mental = self._score_to_risk(score_saude_mental)

        # Alerta: 2+ riscos altos OU confiança_fusão > 0.8
        altos = sum(
            1 for res in results.values() if res.risco_violencia == "alto"
        )
        alerta = altos >= 2 or confiança_fusao > 0.8

        # Recomendação
        recomendacao = self._generate_recommendation(
            risco_violencia, alerta
        )

        return FusionResult(
            risco_violencia=risco_violencia,
            risco_saude_mental=risco_saude_mental,
            confiança=round(confiança_fusao, 4),
            alerta=alerta,
            recomendacao=recomendacao,
            scores_por_modalidade={
                name: round(scores[name], 4) for name in results
            },
        )

    def _risk_to_score(self, risco: str) -> float:
        """Mapeia nível de risco para score numérico."""
        return self.RISK_SCORES.get(risco, 0.0)

    def _score_to_risk(self, score: float) -> str:
        """Mapeia score numérico para nível de risco."""
        if score < 0.33:
            return "baixo"
        elif score < 0.66:
            return "medio"
        else:
            return "alto"

    def _generate_recommendation(self, risco: str, alerta: bool) -> str:
        """Gera recomendação clínica baseada no risco combinado."""
        if alerta:
            return "Encaminhamento urgente recomendado"
        if risco == "alto":
            return "Acompanhamento prioritário recomendado"
        if risco == "medio":
            return "Monitorar e reavaliar em breve"
        return "Acompanhamento de rotina"


@dataclass
class PerformanceTracker:
    """Rastreamento de performance do processamento multimodal."""

    tempos_por_modalidade: dict[str, float] = field(default_factory=dict)
    tempo_inicio: float = field(default_factory=time.perf_counter)

    def register(self, modalidade: str, duration: float) -> None:
        """Registra o tempo de uma modalidade."""
        self.tempos_por_modalidade[modalidade] = duration

    def get_total(self) -> float:
        """Retorna o tempo total decorrido desde o início."""
        return time.perf_counter() - self.tempo_inicio

    def get_parallel_efficiency(self) -> float:
        """Calcula eficiência do paralelismo.

        Eficiência = tempo_sequencial / tempo_total
        Valor > 1 indica ganho com paralelismo.
        """
        total = self.get_total()
        if total == 0:
            return 0.0
        return sum(self.tempos_por_modalidade.values()) / total


class FusionService:
    """Orquestra o processamento multimodal com late fusion."""

    def __init__(self) -> None:
        self._text_service = TextAnalysisService()
        self._audio_service = AudioAnalysisService()
        self._video_service = VideoAnalysisService()
        self._fusion_calculator = LateFusionCalculator()

    async def analyze(
        self,
        texto: str | None,
        audio: UploadFile | None,
        video: UploadFile | None,
        patient_id: str | None = None,
    ) -> MultimodalResponse:
        """Processa múltiplas modalidades em paralelo e retorna fusão.

        Args:
            texto: Texto para análise (opcional)
            audio: Arquivo de áudio (opcional)
            video: Arquivo de vídeo (opcional)
            patient_id: ID anônimo do paciente (opcional)

        Returns:
            MultimodalResponse com resultados individuais e fusão

        Raises:
            HTTPException: 400 se nenhuma modalidade fornecida, 503 se todas falharem
        """
        correlation_id = str(uuid.uuid4())[:8]
        tracker = PerformanceTracker()
        modalidades_processadas: list[str] = []

        logger.info(
            "multimodal_analysis_started",
            correlation_id=correlation_id,
            has_text=texto is not None,
            has_audio=audio is not None,
            has_video=video is not None,
            patient_id=patient_id,
        )

        # Validar que pelo menos uma modalidade foi fornecida
        if texto is None and audio is None and video is None:
            logger.warning(
                "multimodal_no_modality",
                correlation_id=correlation_id,
            )
            raise HTTPException(
                status_code=400,
                detail="Pelo menos uma modalidade deve ser fornecida",
            )

        tasks = []
        task_names = []

        # Preparar tarefas
        if texto:
            tasks.append(
                asyncio.wait_for(
                    self._text_service.analyze(texto, tipo="geral", patient_id=patient_id),
                    timeout=DEFAULT_TIMEOUT_SECONDS,
                )
            )
            task_names.append("texto")

        if audio:
            # Salvar áudio temporariamente
            audio_path = Path(f"/tmp/audio_{correlation_id}.wav")
            tasks.append(
                asyncio.wait_for(
                    self._process_audio(audio, audio_path, patient_id),  # type: ignore[arg-type]
                    timeout=DEFAULT_TIMEOUT_SECONDS,
                )
            )
            task_names.append("audio")

        if video:
            # Salvar vídeo temporariamente
            video_path = Path(f"/tmp/video_{correlation_id}.mp4")
            tasks.append(
                asyncio.wait_for(
                    self._process_video(video, video_path),  # type: ignore[arg-type]
                    timeout=DEFAULT_TIMEOUT_SECONDS,
                )
            )
            task_names.append("video")

        # Processar em paralelo com graceful degradation
        results_raw: list[Any] = []
        exceptions: list[BaseException] = []

        if tasks:
            gathered = await asyncio.gather(*tasks, return_exceptions=True)
            for name, result in zip(task_names, gathered, strict=True):
                if isinstance(result, BaseException):
                    exceptions.append(result)
                    logger.warning(
                        "multimodal_modality_failed",
                        correlation_id=correlation_id,
                        modalidade=name,
                        error=str(result),
                    )
                    results_raw.append(None)
                else:
                    results_raw.append(result)
                    modalidades_processadas.append(name)

        # Montar resultados individuais
        text_result: TextAnalysisResponse | None = None
        audio_result: dict[str, Any] | None = None
        video_result: dict[str, Any] | None = None

        modalidade_results: dict[str, ModalidadeResult] = {}

        for name, raw in zip(task_names, results_raw, strict=True):
            if raw is None:
                continue

            if name == "texto" and isinstance(raw, TextAnalysisResponse):
                text_result = raw
                modalidade_results["texto"] = ModalidadeResult(
                    risco_violencia=raw.risco_violencia,
                    risco_saude_mental=raw.risco_saude_mental,
                    confiança=abs(raw.score),  # score como proxy de confiança
                    raw=raw,
                )
            elif name == "audio" and isinstance(raw, dict):
                audio_result = raw
                confiança_audio = 0.6  # default para áudio
                if "voz_tremida" in raw and raw["voz_tremida"]:
                    confiança_audio = 0.7
                modalidade_results["audio"] = ModalidadeResult(
                    risco_violencia=raw.get("risco_violencia", "baixo"),
                    risco_saude_mental=raw.get("risco_saude_mental", "baixo"),
                    confiança=confiança_audio,
                    raw=raw,
                )
            elif name == "video" and isinstance(raw, dict):
                video_result = raw
                confiança_video = 0.5  # default para vídeo
                detecoes = raw.get("detecoes", [])
                if detecoes:
                    # Quanto mais detecções, maior a confiança (até 0.8)
                    confiança_video = min(0.5 + len(detecoes) * 0.01, 0.8)
                modalidade_results["video"] = ModalidadeResult(
                    risco_violencia=raw.get("risco_violencia", "baixo"),
                    risco_saude_mental=raw.get("risco_saude_mental", "baixo"),
                    confiança=confiança_video,
                    raw=raw,
                )

        # Se todas falharam, retornar 503
        if not modalidade_results:
            logger.error(
                "multimodal_all_modalities_failed",
                correlation_id=correlation_id,
                exceptions=[str(e) for e in exceptions],
            )
            raise HTTPException(
                status_code=503,
                detail="Todas as modalidades falharam. Tente novamente mais tarde.",
            )

        # Fallback: se apenas 1 modalidade, retornar resultado dela
        if len(modalidade_results) == 1:
            name, mod_res = next(iter(modalidade_results.items()))
            fusion = FusionResult(
                risco_violencia=mod_res.risco_violencia,
                risco_saude_mental=mod_res.risco_saude_mental,
                confiança=mod_res.confiança,
                alerta=mod_res.risco_violencia == "alto",
                recomendacao=self._fusion_calculator._generate_recommendation(
                    mod_res.risco_violencia, mod_res.risco_violencia == "alto"
                ),
                scores_por_modalidade={name: self._fusion_calculator._risk_to_score(mod_res.risco_violencia)},
            )
        else:
            fusion = self._fusion_calculator.calculate(modalidade_results)

        total_time_ms = int(tracker.get_total() * 1000)

        logger.info(
            "multimodal_analysis_complete",
            correlation_id=correlation_id,
            modalidades_processadas=modalidades_processadas,
            risco_violencia=fusion.risco_violencia,
            risco_saude_mental=fusion.risco_saude_mental,
            alerta=fusion.alerta,
            total_time_ms=total_time_ms,
        )

        return MultimodalResponse(
            fusao=fusion,
            texto=text_result,
            audio=audio_result,
            video=video_result,
            metadata=AnalysisMetadata(
                correlation_id=correlation_id,
                tempo_processamento_ms=total_time_ms,
                azure_calls=0,
                modalidades_processadas=modalidades_processadas,
            ),
        )

    async def _process_audio(
        self,
        audio: UploadFile,
        audio_path: Path,
        patient_id: str | None,
    ) -> dict[str, Any]:
        """Salva áudio temporário e delega para AudioAnalysisService."""
        content = await audio.read()
        audio_path.write_bytes(content)
        try:
            return await self._audio_service.analyze(audio_path, patient_id)
        finally:
            if audio_path.exists():
                audio_path.unlink()

    async def _process_video(
        self,
        video: UploadFile,
        video_path: Path,
    ) -> dict[str, Any]:
        """Salva vídeo temporário e delega para VideoAnalysisService."""
        content = await video.read()
        video_path.write_bytes(content)
        temp_dir = video_path.parent / f"video_tmp_{video_path.stem}"
        temp_dir.mkdir(exist_ok=True)
        try:
            # Após refatoração T057, analyze é async
            return await self._video_service.analyze(
                video_path=video_path,
                duration_seconds=0.0,  # será calculado dentro do serviço se necessário
                temp_dir=temp_dir,
            )
        finally:
            import shutil
            if temp_dir.exists():
                shutil.rmtree(temp_dir, ignore_errors=True)
            if video_path.exists():
                video_path.unlink()


# Instância singleton
_fusion_service: FusionService | None = None


def get_fusion_service() -> FusionService:
    """Obtém instância singleton do FusionService."""
    global _fusion_service
    if _fusion_service is None:
        _fusion_service = FusionService()
    return _fusion_service
