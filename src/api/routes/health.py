"""Endpoints de health check.

Fornece endpoints para verificar saúde e prontidão da API.
"""

from datetime import datetime
from typing import Annotated, Any

from fastapi import APIRouter, Depends, Request, status

from src.api.routes.dependencies import require_api_key, require_api_key_optional
from src.core.config import settings
from src.core.logging_config import get_logger
from src.core.rate_limit import get_quota_status
from src.core.security.models import SecurityContext

router = APIRouter()
logger = get_logger(__name__)


# Dependencies for health check auth
async def _health_auth_dependency(
    request: Request,
) -> SecurityContext | None:
    """Conditional auth for health endpoint.

    In production, requires valid API key.
    In development/staging, authentication is optional.
    """
    if settings.security_config.is_production:
        # Production: require auth
        return await require_api_key(request)
    # Development: optional auth
    return await require_api_key_optional(request)


@router.get(
    "/health",
    status_code=status.HTTP_200_OK,
    tags=["Health"],
    summary="Health check",
    description="Verifica se a API está rodando e saudável.",
)
async def health_check(
    ctx: Annotated[SecurityContext | None, Depends(_health_auth_dependency)],
) -> dict[str, Any]:
    """Endpoint de health check.

    Retorna informações básicas de saúde da API.
    Em produção, requer API key válida.

    Args:
        ctx: Optional security context (required in production)

    Returns:
        Informações de saúde da API
    """
    # Quota status para Azure Free Tier
    quotas = {
        "text": get_quota_status("text"),
        "audio": get_quota_status("audio"),
        "vision": get_quota_status("vision"),
    }

    response = {
        "status": "healthy",
        "timestamp": datetime.utcnow().isoformat(),
        "version": settings.app_version,
        "environment": settings.environment,
        "quotas": quotas,
    }

    # Include auth info if available
    if ctx and ctx.is_authenticated:
        response["authenticated"] = True
        response["roles"] = ctx.roles

    return response


@router.get(
    "/ready",
    status_code=status.HTTP_200_OK,
    tags=["Health"],
    summary="Readiness check",
    description="Verifica se a API está pronta para receber requisições.",
)
async def readiness_check(
    ctx: Annotated[SecurityContext | None, Depends(_health_auth_dependency)],
) -> dict[str, Any]:
    """Endpoint de readiness check.

    Retorna status de prontidão para health checks do Kubernetes/Docker.
    Em produção, requer API key válida.

    Args:
        ctx: Optional security context (required in production)

    Returns:
        Status de prontidão da API
    """
    # TODO: Verificar conexão com banco de dados
    # TODO: Verificar disponibilidade dos serviços Azure
    response = {
        "status": "ready",
        "timestamp": datetime.utcnow().isoformat(),
    }

    if ctx and ctx.is_authenticated:
        response["authenticated"] = True

    return response
