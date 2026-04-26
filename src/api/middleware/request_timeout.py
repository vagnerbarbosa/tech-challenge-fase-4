"""Middleware para timeout global de requisições.

Implementa um middleware que cancela requisições que excedem
um tempo limite configurável, evitando requisições travadas
com uploads grandes ou processamentos demorados.
"""

import os
import time
from typing import Any

from fastapi import Request
from starlette.middleware.base import BaseHTTPMiddleware, RequestResponseEndpoint
from starlette.responses import JSONResponse
from structlog import get_logger

logger = get_logger(__name__)

# Timeout padrão: 5 minutos para uploads grandes
DEFAULT_REQUEST_TIMEOUT_SECONDS = int(
    os.getenv("REQUEST_TIMEOUT_SECONDS", "300")
)

# Endpoints que podem ter timeout maior (uploads)
UPLOAD_ENDPOINTS = {"/analyze/audio", "/analyze/video", "/analyze/multimodal"}

# Timeout estendido para uploads: 10 minutos
UPLOAD_TIMEOUT_SECONDS = int(
    os.getenv("UPLOAD_TIMEOUT_SECONDS", "600")
)

# ===========================================
# Azure Free Tier Limits Protection
# ===========================================
# Áudio: 10 min/dia, 300 min/mês (5 horas) - proteger com limites conservadores
# Vídeo: processamento local (YOLOv8) - não consome quota Azure

# Tamanho máximo de upload por tipo (configurável via env)
# Áudio: limite conservador (máx 10MB = ~10 min em MP3, ~1 min em WAV)
# Protege quota Azure: 10 min/dia = 600s, limite de 5 min por arquivo = 300s
MAX_AUDIO_SIZE_MB = int(os.getenv("MAX_AUDIO_SIZE_MB", "10"))
MAX_AUDIO_SIZE_BYTES = MAX_AUDIO_SIZE_MB * 1024 * 1024

# Limite de duração de áudio (segundos) - protege quota Azure Free Tier
# 5 minutos = metade da quota diária de 10 minutos
MAX_AUDIO_DURATION_SECONDS = int(os.getenv("MAX_AUDIO_DURATION_SECONDS", "300"))

# Vídeo/Multimodal: limite moderado (processamento local, mas upload consome banda)
# 2 minutos é suficiente para análise de postura/instrumentos
MAX_VIDEO_SIZE_MB = int(os.getenv("MAX_VIDEO_SIZE_MB", "50"))
MAX_VIDEO_SIZE_BYTES = MAX_VIDEO_SIZE_MB * 1024 * 1024

# Limite de duração de vídeo (segundos) - já definido em file_validation.py
MAX_VIDEO_DURATION_SECONDS = int(os.getenv("MAX_VIDEO_DURATION_SECONDS", "120"))

# Limite geral legado (mantido para compatibilidade)
MAX_UPLOAD_SIZE_MB = int(os.getenv("MAX_UPLOAD_SIZE_MB", "50"))


class RequestTimeoutMiddleware(BaseHTTPMiddleware):
    """Middleware que impõe timeout global em requisições.

    Características:
    - Timeout configurável via variável de ambiente
    - Timeout estendido para endpoints de upload
    - Retorna HTTP 504 quando o timeout é excedido
    - Logging detalhado para debugging
    """

    def __init__(
        self,
        app: Any,
        default_timeout: int = DEFAULT_REQUEST_TIMEOUT_SECONDS,
        upload_timeout: int = UPLOAD_TIMEOUT_SECONDS,
    ) -> None:
        """Inicializa o middleware com timeouts configuráveis.

        Args:
            app: Aplicação ASGI/FastAPI
            default_timeout: Timeout padrão em segundos
            upload_timeout: Timeout para endpoints de upload em segundos
        """
        super().__init__(app)
        self.default_timeout = default_timeout
        self.upload_timeout = upload_timeout
        logger.info(
            "request_timeout_middleware_initialized",
            default_timeout=default_timeout,
            upload_timeout=upload_timeout,
        )

    async def dispatch(
        self,
        request: Request,
        call_next: RequestResponseEndpoint,
    ) -> Any:
        """Processa a requisição com timeout.

        Args:
            request: Requisição HTTP
            call_next: Próximo middleware/handler na cadeia

        Returns:
            Response da requisição ou erro 504 se timeout
        """
        path = request.url.path
        method = request.method

        # Determina o timeout baseado no endpoint
        if path in UPLOAD_ENDPOINTS and method == "POST":
            timeout_seconds = self.upload_timeout
            endpoint_type = "upload"
        else:
            timeout_seconds = self.default_timeout
            endpoint_type = "default"

        # Validação de tamanho de upload antes de processar (por tipo)
        if endpoint_type == "upload":
            content_length = request.headers.get("content-length")
            if content_length:
                size_bytes = int(content_length)

                # Define limite baseado no endpoint
                if path == "/analyze/audio":
                    max_size_bytes = MAX_AUDIO_SIZE_BYTES
                    max_size_mb = MAX_AUDIO_SIZE_MB
                    upload_type = "audio"
                else:  # video ou multimodal
                    max_size_bytes = MAX_VIDEO_SIZE_BYTES
                    max_size_mb = MAX_VIDEO_SIZE_MB
                    upload_type = "video"

                if size_bytes > max_size_bytes:
                    logger.warning(
                        "upload_size_exceeded",
                        correlation_id=f"req-{int(time.perf_counter() * 1000)}",
                        path=path,
                        upload_type=upload_type,
                        size_bytes=size_bytes,
                        max_size_bytes=max_size_bytes,
                        max_size_mb=max_size_mb,
                    )
                    return JSONResponse(
                        status_code=413,
                        content={
                            "error": "Payload Too Large",
                            "detail": (
                                f"Arquivo {upload_type} muito grande ({size_bytes / (1024*1024):.1f}MB). "
                                f"Máximo permitido: {max_size_mb}MB"
                            ),
                            "upload_type": upload_type,
                            "max_size_mb": max_size_mb,
                        },
                        headers={
                            "X-Max-Upload-Size-MB": str(max_size_mb),
                            "X-Upload-Type": upload_type,
                        },
                    )

        start_time = time.perf_counter()
        correlation_id = f"req-{int(start_time * 1000)}"

        logger.debug(
            "request_started",
            correlation_id=correlation_id,
            path=path,
            method=method,
            endpoint_type=endpoint_type,
            timeout_seconds=timeout_seconds,
        )

        try:
            # Executa com timeout usando asyncio.wait_for
            import asyncio

            response = await asyncio.wait_for(
                call_next(request),
                timeout=timeout_seconds,
            )

            elapsed = time.perf_counter() - start_time
            logger.debug(
                "request_completed",
                correlation_id=correlation_id,
                path=path,
                elapsed_seconds=round(elapsed, 3),
                status_code=response.status_code,
            )

            # Adiciona header de tempo de processamento
            response.headers["X-Response-Time"] = f"{elapsed:.3f}s"

            return response

        except TimeoutError:
            elapsed = time.perf_counter() - start_time
            logger.error(
                "request_timeout",
                correlation_id=correlation_id,
                path=path,
                method=method,
                elapsed_seconds=round(elapsed, 3),
                timeout_configured=timeout_seconds,
                endpoint_type=endpoint_type,
            )

            return JSONResponse(
                status_code=504,
                content={
                    "error": "Gateway Timeout",
                    "detail": (
                        f"Requisição excedeu o tempo limite de {timeout_seconds}s. "
                        "Tente reduzir o tamanho do arquivo ou tente novamente mais tarde."
                    ),
                    "correlation_id": correlation_id,
                    "path": path,
                },
                headers={
                    "X-Request-Timeout": str(timeout_seconds),
                    "X-Elapsed-Time": f"{elapsed:.3f}s",
                },
            )

        except Exception as e:
            elapsed = time.perf_counter() - start_time
            logger.error(
                "request_error",
                correlation_id=correlation_id,
                path=path,
                error_type=type(e).__name__,
                error=str(e),
                elapsed_seconds=round(elapsed, 3),
            )
            raise
