"""Rota para análise multimodal.

Endpoint para processamento simultâneo de texto, áudio e vídeo,
combinando resultados via late fusion ponderado por confiança.
"""

import tempfile
from pathlib import Path

from fastapi import APIRouter, File, Form, HTTPException, UploadFile, status
from structlog import get_logger

from src.core.rate_limit import RATE_LIMITS, check_and_increment_quota
from src.models.schemas import MultimodalResponse
from src.services.multimodal_fusion import get_fusion_service
from src.utils.file_validation import validate_audio_file, validate_video_file

logger = get_logger()

router = APIRouter(prefix="/analyze", tags=["Multimodal Analysis"])


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

    if audio:
        try:
            await validate_audio_file(audio)
            check_and_increment_quota(
                "audio",
                daily_limit=RATE_LIMITS["audio"]["daily_minutes"],
                monthly_limit=RATE_LIMITS["audio"]["monthly_minutes"],
            )
        except HTTPException:
            raise
        except Exception:
            logger.warning(
                "audio_rate_limit_exceeded",
                correlation_id=correlation_id,
            )
            raise HTTPException(
                status_code=429,
                detail="Rate limit excedido para análise de áudio",
            ) from None

    if video:
        await validate_video_file(video)

    # Diretório temporário para arquivos (LGPD)
    temp_dir = Path(tempfile.mkdtemp(prefix="multimodal_"))

    try:
        service = get_fusion_service()
        response = await service.analyze(
            texto=texto,
            audio=audio,
            video=video,
            patient_id=patient_id,
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

        return response

    except HTTPException:
        raise
    except Exception as e:
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
