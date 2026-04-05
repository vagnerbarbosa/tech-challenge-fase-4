"""Endpoints de health check.

Fornece endpoints para verificar saúde e prontidão da API.
"""

from datetime import datetime

from fastapi import APIRouter, status

from src.core.config import settings
from src.core.logging_config import get_logger

router = APIRouter()
logger = get_logger(__name__)


@router.get(
    "/health",
    status_code=status.HTTP_200_OK,
    tags=["Health"],
    summary="Health check",
    description="Verifica se a API está rodando e saudável.",
)
async def health_check():
    """Endpoint de health check.

    Retorna informações básicas de saúde da API.
    """
    return {
        "status": "healthy",
        "timestamp": datetime.utcnow().isoformat(),
        "version": settings.app_version,
        "environment": settings.environment,
    }


@router.get(
    "/ready",
    status_code=status.HTTP_200_OK,
    tags=["Health"],
    summary="Readiness check",
    description="Verifica se a API está pronta para receber requisições.",
)
async def readiness_check():
    """Endpoint de readiness check.

    Retorna status de prontidão para health checks do Kubernetes/Docker.
    """
    # TODO: Verificar conexão com banco de dados
    # TODO: Verificar disponibilidade dos serviços Azure
    return {
        "status": "ready",
        "timestamp": datetime.utcnow().isoformat(),
    }
