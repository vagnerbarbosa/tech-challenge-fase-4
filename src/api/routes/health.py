"""Endpoints de health check.

Fornece endpoints para verificar saúde e prontidão da API.
"""

from datetime import datetime
from typing import Any

from fastapi import APIRouter, status

from src.core.config import settings
from src.core.logging_config import get_logger
from src.core.rate_limit import get_quota_status

router = APIRouter()
logger = get_logger(__name__)


@router.get(
    "/health",
    status_code=status.HTTP_200_OK,
    tags=["Health"],
    summary="Health check",
    description="Verifica se a API está rodando e saudável.",
)
async def health_check() -> dict[str, Any]:
    """Endpoint de health check.

    Retorna informações básicas de saúde da API.
    """
    # Quota status para Azure Free Tier
    quotas = {
        "text": get_quota_status("text"),
        "audio": get_quota_status("audio"),
        "vision": get_quota_status("vision"),
    }

    return {
        "status": "healthy",
        "timestamp": datetime.utcnow().isoformat(),
        "version": settings.app_version,
        "environment": settings.environment,
        "quotas": quotas,
    }


@router.get(
    "/ready",
    status_code=status.HTTP_200_OK,
    tags=["Health"],
    summary="Readiness check",
    description="Verifica se a API está pronta para receber requisições.",
)
async def readiness_check() -> dict[str, Any]:
    """Endpoint de readiness check.

    Retorna status de prontidão para health checks do Kubernetes/Docker.
    """
    # TODO: Verificar conexão com banco de dados
    # TODO: Verificar disponibilidade dos serviços Azure
    return {
        "status": "ready",
        "timestamp": datetime.utcnow().isoformat(),
    }
