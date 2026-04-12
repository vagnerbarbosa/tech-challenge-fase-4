"""Rota para análise de áudio.

Endpoint para upload e análise de arquivos de áudio,
integrando transcrição Azure Speech com análise prosódica librosa.
"""

from fastapi import APIRouter, File, Form, HTTPException, UploadFile, status
from structlog import get_logger

from src.api.routes.dependencies import get_temp_manager
from src.core.exceptions import (
    AzureAuthenticationError,
    AzureQuotaExceededError,
    AzureServiceError,
)
from src.core.rate_limit import check_and_increment_quota
from src.core.temp_file_manager import TempFileManager
from src.models.schemas import AnalysisMetadata, AudioAnalysisResponse
from src.services.audio_analysis import AudioAnalysisService
from src.utils.file_validation import (
    check_file_size,
    check_upload_size,
    validate_audio_file,
)

logger = get_logger()

router = APIRouter(prefix="/analyze", tags=["audio"])

# Rate limits do Azure Free Tier
AUDIO_DAILY_LIMIT = 10  # minutos por dia
AUDIO_MONTHLY_LIMIT = 300  # minutos por mês


@router.post(
    "/audio",
    response_model=AudioAnalysisResponse,
    status_code=status.HTTP_200_OK,
    summary="Analisa arquivo de áudio",
    description="""
    Transcreve áudio e analisa features prosódicas para identificar riscos.

    - Transcrição via Azure Speech Services
    - Análise prosódica (pitch, energia, pausas) via librosa
    - Detecção de risco de violência e saúde mental

    **Limites:**
    - Formatos: WAV, MP3, OGG
    - Tamanho máximo: 50MB
    - Duração máxima: 5 minutos (Free Tier)
    """,
    responses={
        200: {"description": "Análise concluída com sucesso"},
        400: {"description": "Arquivo inválido"},
        429: {"description": "Quota Azure excedida"},
        503: {"description": "Serviço indisponível"},
    },
)
async def analyze_audio(
    file: UploadFile = File(..., description="Arquivo de áudio (WAV, MP3, OGG)"),
    patient_id: str | None = Form(
        default=None,
        description="ID anônimo do paciente (UUID recomendado, opcional)",
    ),
) -> AudioAnalysisResponse:
    """Analisa arquivo de áudio para transcrição e riscos.

    Args:
        file: Arquivo de áudio para análise
        patient_id: ID anônimo opcional do paciente

    Returns:
        AudioAnalysisResponse com transcrição, prosódia e riscos

    Raises:
        HTTPException: 400 para arquivo inválido, 429 para quota excedida
    """
    import asyncio
    import time
    from datetime import UTC, datetime

    start_time = time.perf_counter()
    correlation_id = f"audio-{int(start_time * 1000)}"

    logger.info(
        "audio_analysis_request",
        correlation_id=correlation_id,
        filename=file.filename,
        patient_id=patient_id,
    )

    # Validação do arquivo
    try:
        await validate_audio_file(file)
        await check_upload_size(file)  # Valida tamanho antes de salvar
    except HTTPException as e:
        logger.warning(
            "audio_validation_failed",
            correlation_id=correlation_id,
            error=e.detail,
            status_code=e.status_code,
        )
        raise

    # Verifica e incrementa quota (por minuto de áudio)
    # Estimativa: 1 minuto por arquivo (conservador)
    try:
        quota_status = check_and_increment_quota(
            "audio", AUDIO_DAILY_LIMIT, AUDIO_MONTHLY_LIMIT, increment=1
        )
        logger.debug(
            "audio_rate_limit_checked",
            correlation_id=correlation_id,
            quota_remaining=quota_status["daily_remaining"],
        )
    except Exception as e:
        logger.warning(
            "audio_rate_limit_exceeded",
            correlation_id=correlation_id,
            error=str(e),
        )
        raise HTTPException(
            status_code=status.HTTP_429_TOO_MANY_REQUESTS,
            detail="Quota do Azure Speech excedida. Tente novamente amanhã.",
        ) from e

    temp_manager: TempFileManager = get_temp_manager()
    temp_path = None
    azure_calls = 0

    try:
        # Salva arquivo temporariamente (com hash do patient_id no nome - LGPD)
        temp_path = await temp_manager.save_temp(file, patient_id)
        logger.debug(
            "audio_file_saved",
            correlation_id=correlation_id,
            temp_path=str(temp_path),
        )

        # Verifica tamanho do arquivo salvo
        check_file_size(temp_path)

        # Análise do áudio (com timeout de 30s para todo o processamento)
        service = AudioAnalysisService()

        try:
            result = await asyncio.wait_for(
                service.analyze(temp_path, patient_id),
                timeout=30
            )
            azure_calls = 1

        except AzureQuotaExceededError as e:
            logger.error(
                "azure_quota_exceeded",
                correlation_id=correlation_id,
                error=str(e),
            )
            raise HTTPException(
                status_code=status.HTTP_429_TOO_MANY_REQUESTS,
                detail="Quota do Azure Speech excedida. Tente novamente amanhã.",
            ) from e

        except AzureAuthenticationError as e:
            logger.error(
                "azure_auth_error",
                correlation_id=correlation_id,
                error=str(e),
            )
            raise HTTPException(
                status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                detail="Erro de autenticação Azure. Serviço temporariamente indisponível.",
            ) from e

        except AzureServiceError as e:
            logger.error(
                "azure_service_error",
                correlation_id=correlation_id,
                error=str(e),
            )
            raise HTTPException(
                status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                detail="Serviço de transcrição indisponível. Tente novamente mais tarde.",
            ) from e

        except TimeoutError as e:
            logger.error(
                "audio_analysis_timeout",
                correlation_id=correlation_id,
                timeout_seconds=30,
            )
            raise HTTPException(
                status_code=status.HTTP_504_GATEWAY_TIMEOUT,
                detail="Tempo limite excedido para processamento do áudio. Tente novamente mais tarde.",
            ) from e

        except Exception as e:
            logger.error(
                "audio_analysis_error",
                correlation_id=correlation_id,
                error=str(e),
                error_type=type(e).__name__,
            )
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail=f"Erro interno durante análise: {str(e)}",
            ) from e

        # Prepara resposta
        processing_time_ms = int((time.perf_counter() - start_time) * 1000)

        metadata = AnalysisMetadata(
            correlation_id=correlation_id,
            timestamp=datetime.now(UTC),
            tempo_processamento_ms=processing_time_ms,
            cache_hit=False,
            azure_calls=azure_calls,
        )

        response = AudioAnalysisResponse(
            transcricao=result.get("transcricao", ""),
            idioma_detectado=result.get("idioma_detectado", "pt-BR"),
            sentimento=result.get("sentimento", "neutro"),
            entonação=result.get("entonação", "normal"),
            voz_tremida=result.get("voz_tremida", False),
            pausas_suspeitas=result.get("pausas_suspeitas", 0),
            duracao_segundos=result.get("duracao_segundos", 0.0),
            risco_violencia=result.get("risco_violencia", "baixo"),
            risco_saude_mental=result.get("risco_saude_mental", "baixo"),
            metadata=metadata,
        )

        logger.info(
            "audio_analysis_completed",
            correlation_id=correlation_id,
            processing_time_ms=processing_time_ms,
            risco_violencia=response.risco_violencia,
            risco_saude_mental=response.risco_saude_mental,
            sentimento=response.sentimento,
            entonação=response.entonação,
        )

        return response

    finally:
        # Cleanup LGPD: sempre remove arquivo temporário
        if temp_path:
            temp_manager.cleanup(temp_path)
            logger.debug(
                "audio_temp_file_cleaned",
                correlation_id=correlation_id,
                temp_path=str(temp_path),
            )


@router.get(
    "/audio/formats",
    summary="Formatos de áudio suportados",
    description="Retorna lista de formatos de áudio aceitos e limites.",
)
async def get_audio_formats() -> dict[str, list[str] | int | dict[str, int]]:
    """Retorna informações sobre formatos suportados."""
    return {
        "formats": ["audio/wav", "audio/x-wav", "audio/mpeg", "audio/ogg"],
        "extensions": [".wav", ".mp3", ".ogg"],
        "max_file_size_mb": 50,
        "max_duration_minutes": 5,
        "rate_limits": {
            "daily_minutes": AUDIO_DAILY_LIMIT,
            "monthly_minutes": AUDIO_MONTHLY_LIMIT,
        },
    }
