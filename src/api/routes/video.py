"""Rota para análise de vídeo.

Endpoint para upload e análise de arquivos de vídeo,
integrando detecção de objetos YOLOv8 com análise de riscos.
"""

import tempfile
from pathlib import Path
from typing import Any

from fastapi import APIRouter, Depends, File, Form, HTTPException, UploadFile, status
from structlog import get_logger

from src.api.routes.dependencies import require_api_key, validate_video_upload
from src.core.cache import get_cache
from src.core.rate_limit import RATE_LIMITS, check_and_increment_quota
from src.models.audit_log import AuditEventType
from src.models.schemas import VideoAnalysisMetadata, VideoAnalysisResponse
from src.utils.audit_logger import get_audit_logger
from src.services.video_analysis import VideoAnalysisService
from src.utils.file_validation import check_video_duration

logger = get_logger()

router = APIRouter(
    prefix="/analyze",
    tags=["Video Analysis"],
    dependencies=[Depends(require_api_key)],  # T018: Require auth for all routes
)


@router.post(
    "/video",
    response_model=VideoAnalysisResponse,
    status_code=status.HTTP_200_OK,
    summary="Analisa arquivo de vídeo",
    description="""
    Analisa vídeo usando YOLOv8 para detecção de objetos e riscos.

    - Detecção de objetos via YOLOv8 (pessoas, instrumentos)
    - Detecção de sangramento via análise de cor HSV
    - Cálculo de risco de violência e saúde mental

    **Limites:**
    - Formatos: MP4, AVI, MOV
    - Tamanho máximo: 50MB
    - Duração máxima: 2 minutos
    - Processamento local (sem custo Azure)
    """,
    responses={
        200: {"description": "Análise concluída com sucesso"},
        400: {"description": "Arquivo inválido ou formato não suportado"},
        413: {"description": "Arquivo excede o limite de 50MB"},
        429: {"description": "Rate limit excedido"},
        504: {"description": "Timeout no processamento"},
    },
)
async def analyze_video(
    video: UploadFile = File(..., description="Arquivo de vídeo (MP4, AVI, MOV)"),
    tipo: str = Form(
        default="consulta",
        description="Tipo de análise: consulta, procedimento, exame",
    ),
    patient_id: str | None = Form(
        default=None,
        description="ID anônimo do paciente (UUID recomendado, opcional)",
    ),
) -> VideoAnalysisResponse:
    """Analisa arquivo de vídeo para detecção de objetos e riscos.

    Args:
        video: Arquivo de vídeo para análise
        tipo: Tipo de análise (consulta, procedimento, exame)
        patient_id: ID anônimo opcional do paciente

    Returns:
        VideoAnalysisResponse com detecções e riscos

    Raises:
        HTTPException: 400 para arquivo inválido, 413 para tamanho excedido
    """
    import shutil
    import time

    start_time = time.perf_counter()
    correlation_id = f"video-{int(start_time * 1000)}"

    logger.info(
        "video_analysis_request",
        correlation_id=correlation_id,
        filename=video.filename,
        tipo=tipo,
        patient_id=patient_id,
    )

    # Rate limiting check
    try:
        check_and_increment_quota(
            "video_analysis",
            daily_limit=RATE_LIMITS["video_analysis"]["daily"],
            monthly_limit=RATE_LIMITS["video_analysis"]["monthly"],
        )
    except Exception:
        logger.warning(
            "video_rate_limit_exceeded",
            correlation_id=correlation_id,
        )
        raise HTTPException(
            status_code=429,
            detail="Rate limit exceeded for video analysis",
        ) from None

    # Validação do arquivo (segurança: filename, magic bytes, tamanho)
    try:
        await validate_video_upload(video)
    except HTTPException as e:
        logger.warning(
            "video_validation_failed",
            correlation_id=correlation_id,
            error=e.detail,
        )
        raise

    # Salvar arquivo temporariamente
    temp_dir = Path(tempfile.mkdtemp())
    video_path = temp_dir / "input.mp4"

    try:
        # Salvar vídeo
        with open(video_path, "wb") as f:
            shutil.copyfileobj(video.file, f)

        logger.debug(
            "video_saved",
            correlation_id=correlation_id,
            path=str(video_path),
        )

        # Verificar cache
        cache = get_cache()
        cached_result = cache.get(video_path)
        if cached_result:
            logger.info(
                "video_cache_hit",
                correlation_id=correlation_id,
            )
            return VideoAnalysisResponse(
                risco_violencia=cached_result["risco_violencia"],
                risco_saude_mental=cached_result["risco_saude_mental"],
                detecoes=cached_result["detecoes"],
                alertas=cached_result["alertas"],
                metadata=VideoAnalysisMetadata(
                    correlation_id=correlation_id,
                    tempo_processamento_ms=0,
                    cache_hit=True,
                    frames_analisados=cached_result.get("frames_processados", 0),
                    duracao_video_segundos=cached_result.get("duracao", 0),
                    modelo="yolov8n",
                    local_processing=True,
                ),
            )

        # Verificar duração
        try:
            duration = check_video_duration(video_path)
        except HTTPException as e:
            logger.warning(
                "video_duration_check_failed",
                correlation_id=correlation_id,
                error=e.detail,
            )
            raise

        logger.debug(
            "video_duration_checked",
            correlation_id=correlation_id,
            duration_seconds=duration,
        )

        # Processar vídeo
        analysis_service = VideoAnalysisService()
        result = await analysis_service.analyze(
            video_path=video_path,
            duration_seconds=duration,
            temp_dir=temp_dir,
        )

        # Armazenar no cache
        cache.set(video_path, {**result, "duracao": duration})

        processing_time_ms = int((time.perf_counter() - start_time) * 1000)

        logger.info(
            "video_analysis_complete",
            correlation_id=correlation_id,
            processing_time_ms=processing_time_ms,
            frames_analisados=result["frames_processados"],
            risco_violencia=result["risco_violencia"],
            risco_saude_mental=result["risco_saude_mental"],
        )

        # Log audit event
        audit = get_audit_logger()
        audit.log_analysis_created(
            correlation_id=correlation_id,
            resource="/analyze/video",
            patient_id=patient_id,
            modalities=["video"],
            risk_detected=(
                result["risco_violencia"] == "alto"
                or result["risco_saude_mental"] == "alto"
            ),
            ip_address=None,  # Not available in this context
        )

        # Montar resposta
        return VideoAnalysisResponse(
            risco_violencia=result["risco_violencia"],
            risco_saude_mental=result["risco_saude_mental"],
            detecoes=result["detecoes"],
            alertas=result["alertas"],
            metadata=VideoAnalysisMetadata(
                correlation_id=correlation_id,
                tempo_processamento_ms=processing_time_ms,
                cache_hit=False,
                frames_analisados=result["frames_processados"],
                duracao_video_segundos=duration,
                modelo="yolov8n",
                local_processing=True,
            ),
        )

    except HTTPException:
        # Log failed analysis
        audit = get_audit_logger()
        audit.log(
            event_type=AuditEventType.ANALYSIS_CREATED,
            correlation_id=correlation_id,
            action="POST /analyze/video",
            resource="/analyze/video",
            result="failure",
            patient_id=patient_id,
            details={"modalities": ["video"]},
        )
        raise
    except Exception as e:
        # Log failed analysis
        audit = get_audit_logger()
        audit.log(
            event_type=AuditEventType.ANALYSIS_CREATED,
            correlation_id=correlation_id,
            action="POST /analyze/video",
            resource="/analyze/video",
            result="error",
            patient_id=patient_id,
            details={"error": str(e), "modalities": ["video"]},
        )
        logger.error(
            "video_analysis_error",
            correlation_id=correlation_id,
            error=str(e),
            exc_info=True,
        )
        raise HTTPException(
            status_code=500,
            detail=f"Erro ao processar vídeo: {str(e)}",
        ) from None
    finally:
        # Limpar arquivos temporários (LGPD)
        shutil.rmtree(temp_dir, ignore_errors=True)
        logger.debug(
            "temp_files_cleaned",
            correlation_id=correlation_id,
            temp_dir=str(temp_dir),
        )


@router.get(
    "/video/formats",
    summary="Retorna formatos de vídeo suportados",
    description="Retorna informações sobre formatos, tamanhos e limites suportados",
)
async def get_video_formats() -> dict[str, Any]:
    """Retorna informações sobre formatos de vídeo suportados."""
    return {
        "formatos_suportados": ["MP4", "AVI", "MOV"],
        "extensoes": [".mp4", ".avi", ".mov"],
        "tamanho_maximo_mb": 50,
        "duracao_maxima_segundos": 120,
        "duracao_maxima_minutos": 2,
        "fps_adaptativo": {
            "ate_30s": "1 FPS (1 frame/segundo)",
            "acima_30s": "0.2 FPS (1 frame/5 segundos)",
        },
    }


@router.get(
    "/video/cache/stats",
    summary="Retorna estatísticas do cache de vídeo",
    description="Retorna informações sobre o cache de análises de vídeo em memória.",
    responses={
        200: {
            "description": "Estatísticas do cache",
            "content": {
                "application/json": {
                    "example": {
                        "entries": 50,
                        "ttl_minutes": 60.0,
                    }
                }
            },
        },
    },
)
async def get_video_cache_stats() -> dict[str, Any]:
    """Retorna estatísticas do cache de análises de vídeo.

    Returns:
        Dicionário com estatísticas do cache
    """
    cache = get_cache()
    return cache.get_stats()


@router.post(
    "/video/cache/clear",
    summary="Limpa o cache de vídeo",
    description="Remove todas as entradas do cache de análises de vídeo.",
    responses={
        200: {
            "description": "Cache limpo com sucesso",
            "content": {
                "application/json": {
                    "example": {
                        "message": "Cache de vídeo limpo com sucesso",
                    }
                }
            },
        },
    },
)
async def clear_video_cache() -> dict[str, str]:
    """Limpa todas as entradas do cache de vídeo.

    Returns:
        Confirmação de limpeza do cache
    """
    cache = get_cache()
    cache.clear_all()
    logger.info("video_cache_cleared")
    return {"message": "Cache de vídeo limpo com sucesso"}
