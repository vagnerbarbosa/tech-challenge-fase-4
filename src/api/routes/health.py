"""Health check endpoints.

Provides endpoints for checking API health and readiness.
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
    description="Check if the API is running and healthy.",
)
async def health_check():
    """Health check endpoint.

    Returns basic health information about the API.
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
    description="Check if the API is ready to receive requests.",
)
async def readiness_check():
    """Readiness check endpoint.

    Returns readiness status for Kubernetes/Docker health checks.
    """
    # TODO: Check database connection
    # TODO: Check Azure services availability
    return {
        "status": "ready",
        "timestamp": datetime.utcnow().isoformat(),
    }
