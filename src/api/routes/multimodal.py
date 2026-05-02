"""Rota para análise multimodal.

Endpoint para processamento simultâneo de texto, áudio e vídeo,
combinando resultados via late fusion ponderado por confiança.
"""

import asyncio
import tempfile
from pathlib import Path

from fastapi import APIRouter, Depends, File, Form, HTTPException, UploadFile, status
from structlog import get_logger

from src.api.routes.dependencies import require_api_key
from src.core.rate_limit import RATE_LIMITS, check_and_increment_quota
from src.models.audit_log import AuditEventType
from src.models.schemas import MultimodalResponse
from src.services.multimodal_fusion import get_fusion_service
from src.utils.audit_logger import get_audit_logger
from src.utils.file_validation import validate_audio_file, validate_video_file

logger = get_logger()

router = APIRouter(
    prefix="/analyze",
    tags=["Multimodal Analysis"],
    dependencies=[Depends(require_api_key)],  # T018: Require auth for all routes
)


@router.post(
    "/multimodal",
    response_model=MultimodalResponse,
    status_code=status.HTTP_200_OK,
    summary="Analisa múltiplas modalidades simultaneamente",
    description="""
    Processa texto, áudio e/ou vídeo em paralelo, combinando resultados
    via late fusion ponderado por confiança de cada modalidade.

    - **Texto**: Azure AI Language (sentimento + risco)
    - **Áudio**: Azure AI Speech (transcrição + prosódica)
    - **Vídeo**: YOLOv8 local (detecção de objetos + postura)

    **Regras:**
    - Pelo menos uma modalidade deve ser fornecida
    - Áudio e vídeo são opcionais (multipart)
    - Texto pode ser enviado como campo de formulário
    - Vídeo não consome quota Azure (processamento local)
    """,
    responses={
        200: {"description": "Análise multimodal concluída com sucesso"},
        400: {"description": "Nenhuma modalidade fornecida ou arquivo inválido"},
        429: {"description": "Rate limit excedido para texto ou áudio"},
        503: {"description": "Todas as modalidades falharam"},
    },
)
async def analyze_multimodal(
    texto: str | None = Form(
        default=None,
        description="Texto para análise (opcional, 10-5000 caracteres)",
    ),
    audio: UploadFile | None = File(
        default=None,
        description="Arquivo de áudio para análise (opcional)",
    ),
    video: UploadFile | None = File(
        default=None,
        description="Arquivo de vídeo para análise (opcional)",
    ),
    patient_id: str | None = Form(
        default=None,
        description="ID anônimo do paciente (UUID recomendado, opcional)",
    ),
) -> MultimodalResponse:
    """Processa múltiplas modalidades em paralelo com late fusion.

    Args:
        texto: Texto para análise (opcional)
        audio: Arquivo de áudio (opcional)
        video: Arquivo de vídeo (opcional)
        patient_id: ID anônimo do paciente (opcional)

    Returns:
        MultimodalResponse com fusão + resultados individuais

    Raises:
        HTTPException: 400 se nenhuma modalidade, 429 se quota excedida
    """
    correlation_id = f"mm-{int(__import__('time').perf_counter() * 1000)}"

    logger.info(
        "multimodal_request_received",
        correlation_id=correlation_id,
        has_text=texto is not None,
        has_audio=audio is not None,
        has_video=video is not None,
    )

    # Timeout global para análise multimodal (90s = 60s processamento + margem)
    request_timeout_seconds = 90

    # Validação: pelo menos uma modalidade
    if texto is None and audio is None and video is None:
        logger.warning(
            "multimodal_no_input",
            correlation_id=correlation_id,
        )
        raise HTTPException(
            status_code=400,
            detail="Pelo menos uma modalidade deve ser fornecida (texto, áudio ou vídeo)",
        )

    # Rate limiting para texto e áudio (vídeo é local)
    if texto:
        try:
            check_and_increment_quota(
                "text",
                daily_limit=RATE_LIMITS["text"]["daily"],
                monthly_limit=RATE_LIMITS["text"]["monthly"],
            )
        except Exception:
            logger.warning(
                "text_rate_limit_exceeded",
                correlation_id=correlation_id,
            )
            raise HTTPException(
                status_code=429,
                detail="Rate limit excedido para análise de texto",
            ) from None

    # Diretório temporário para arquivos (LGPD) - CRIAR ANTES DA VALIDAÇÃO
    temp_dir = Path(tempfile.mkdtemp(prefix="multimodal_"))

    # Salvar arquivos em disco IMEDIATAMENTE após receber (antes de qualquer validação
    # que consuma o stream), pois UploadFile é de única leitura
    audio_path: Path | None = None
    video_path: Path | None = None

    try:
        if audio:
            audio_path = temp_dir / "audio_input"
            content = await audio.read()
            audio_path.write_bytes(content)
            logger.debug(
                "audio_saved_temp",
                correlation_id=correlation_id,
                size_bytes=len(content),
            )

            # Validar arquivo salvo
            from io import BytesIO

            from fastapi import UploadFile as UploadFileType

            # Criar UploadFile temporário para validação
            validation_file = UploadFileType(
                filename=audio.filename,
                file=BytesIO(content),
            )
            await validate_audio_file(validation_file)
            check_and_increment_quota(
                "audio",
                daily_limit=RATE_LIMITS["audio"]["daily_minutes"],
                monthly_limit=RATE_LIMITS["audio"]["monthly_minutes"],
            )

        if video:
            video_path = temp_dir / "video_input"
            content = await video.read()
            video_path.write_bytes(content)
            logger.debug(
                "video_saved_temp",
                correlation_id=correlation_id,
                size_bytes=len(content),
            )

            # Validar arquivo salvo
            from io import BytesIO

            from fastapi import UploadFile as UploadFileType

            validation_file = UploadFileType(
                filename=video.filename,
                file=BytesIO(content),
            )
            await validate_video_file(validation_file)

    except HTTPException:
        raise
    except Exception as e:
        logger.error(
            "file_save_error",
            correlation_id=correlation_id,
            error=str(e),
        )
        raise HTTPException(
            status_code=400,
            detail=f"Erro ao processar arquivo: {str(e)}",
        ) from None

    try:
        service = get_fusion_service()
        # Timeout global para evitar requisições travadas (ex: vídeos muito grandes)
        async with asyncio.timeout(request_timeout_seconds):
            response = await service.analyze(
                texto=texto,
                audio_path=audio_path,
                video_path=video_path,
                patient_id=patient_id,
                temp_base_dir=temp_dir,  # Passar diretório temporário para cópia do áudio
            )

        # Atualizar correlation_id no metadata
        response.metadata.correlation_id = correlation_id

        logger.info(
            "multimodal_response_ready",
            correlation_id=correlation_id,
            risco_violencia=response.fusao.risco_violencia,
            risco_saude_mental=response.fusao.risco_saude_mental,
            alerta=response.fusao.alerta,
        )

        # Log audit event
        modalities = []
        if texto:
            modalities.append("text")
        if audio_path:
            modalities.append("audio")
        if video_path:
            modalities.append("video")

        audit = get_audit_logger()
        audit.log_analysis_created(
            correlation_id=correlation_id,
            resource="/analyze/multimodal",
            patient_id=patient_id,
            modalities=modalities,
            risk_detected=(
                response.fusao.risco_violencia == "alto"
                or response.fusao.risco_saude_mental == "alto"
            ),
            ip_address=None,
        )

        return response

    except HTTPException:
        # Log failed analysis
        modalities = []
        if texto:
            modalities.append("text")
        if audio:
            modalities.append("audio")
        if video:
            modalities.append("video")

        audit = get_audit_logger()
        audit.log(
            event_type=AuditEventType.ANALYSIS_CREATED,
            correlation_id=correlation_id,
            action="POST /analyze/multimodal",
            resource="/analyze/multimodal",
            result="failure",
            patient_id=patient_id,
            details={"modalities": modalities},
        )
        raise
    except TimeoutError:
        # Log timeout
        modalities = []
        if texto:
            modalities.append("text")
        if audio_path:
            modalities.append("audio")
        if video_path:
            modalities.append("video")

        audit = get_audit_logger()
        audit.log(
            event_type=AuditEventType.ANALYSIS_CREATED,
            correlation_id=correlation_id,
            action="POST /analyze/multimodal",
            resource="/analyze/multimodal",
            result="error",
            patient_id=patient_id,
            details={"error": "timeout", "modalities": modalities},
        )
        logger.error(
            "multimodal_timeout",
            correlation_id=correlation_id,
            timeout_seconds=request_timeout_seconds,
        )
        raise HTTPException(
            status_code=504,
            detail=f"Análise excedeu o tempo limite de {request_timeout_seconds}s. "
                   "Tente com um vídeo menor ou menos modalidades.",
        ) from None
    except Exception as e:
        # Log failed analysis
        modalities = []
        if texto:
            modalities.append("text")
        if audio_path:
            modalities.append("audio")
        if video_path:
            modalities.append("video")

        audit = get_audit_logger()
        audit.log(
            event_type=AuditEventType.ANALYSIS_CREATED,
            correlation_id=correlation_id,
            action="POST /analyze/multimodal",
            resource="/analyze/multimodal",
            result="error",
            patient_id=patient_id,
            details={"error": str(e), "modalities": modalities},
        )
        logger.error(
            "multimodal_error",
            correlation_id=correlation_id,
            error=str(e),
            exc_info=True,
        )
        raise HTTPException(
            status_code=500,
            detail=f"Erro ao processar análise multimodal: {str(e)}",
        ) from None
    finally:
        # Cleanup de arquivos temporários (LGPD)
        import shutil
        if temp_dir.exists():
            shutil.rmtree(temp_dir, ignore_errors=True)
            logger.debug(
                "temp_files_cleaned",
                correlation_id=correlation_id,
                temp_dir=str(temp_dir),
            )
