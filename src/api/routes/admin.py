"""Rotas administrativas para exportação de logs de auditoria e compliance LGPD.

Este módulo fornece endpoints administrativos para gerenciamento de logs de auditoria
e exportação de dados em formato compatível com ANPD conforme exigido pela LGPD.
"""

from __future__ import annotations

import secrets
from datetime import datetime, timezone
from typing import Annotated, Any

from fastapi import APIRouter, Depends, HTTPException, Query, Request, status
from fastapi.responses import PlainTextResponse
from pydantic import BaseModel, Field

from src.core.config import settings
from src.models.audit_log import AuditEventType
from src.utils.audit_logger import AuditLogger, get_audit_logger

router = APIRouter(prefix="/admin", tags=["Admin"])


class APIKeyResponse(BaseModel):
    """Resposta para geração de API key."""

    api_key: str = Field(..., description="A API key gerada (só é mostrada uma vez)")
    key_id: str = Field(..., description="ID da chave para referência")
    created_at: str = Field(..., description="Data de criação ISO 8601")
    description: str | None = Field(None, description="Descrição da chave")


class APIKeyListResponse(BaseModel):
    """Resposta para listagem de API keys."""

    keys: list[dict[str, Any]] = Field(..., description="Lista de API keys")
    total: int = Field(..., description="Total de chaves")


def verify_admin_access(request: Request) -> bool:
    """Verifica acesso administrativo para endpoints protegidos.

    Em produção, deve validar um token/API key de administrador adequado.
    Por enquanto, verifica um header-based admin key.

    Args:
        request: Objeto de requisição FastAPI

    Returns:
        True se acesso de administrador for concedido

    Raises:
        HTTPException: Se acesso de administrador for negado
    """
    # Verifica header de admin API key
    admin_key = request.headers.get("X-Admin-Key")

    # Em produção, deve verificar contra uma chave segura
    # Para desenvolvimento, permite check simples
    expected_key = getattr(settings, "admin_api_key", None)

    if not expected_key:
        # Se não há chave configurada, nega acesso em produção
        if settings.environment == "production":
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Admin access not configured",
            )
        # Em desenvolvimento, permite sem chave para testes
        return True

    if admin_key != expected_key:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Invalid admin credentials",
        )

    return True


def _generate_api_key() -> tuple[str, str]:
    """Gera uma API key segura e seu ID de referência.

    Returns:
        Tupla (api_key, key_id) onde key_id é um prefixo único da chave
    """
    # Gera 32 bytes aleatórios e converte para hex (64 caracteres = 256 bits entropia)
    raw_key = secrets.token_hex(32)
    api_key = f"ak_{raw_key}"
    # Key ID é prefixo da chave para referência em logs (não usa hash)
    key_id = raw_key[:16]
    return api_key, key_id


@router.post(
    "/api-keys",
    response_model=APIKeyResponse,
    summary="Gera nova API key",
    description="""Gera uma nova API key para cliente/usuário. A chave só é exibida uma vez.

    ⚠️ SECURITY WARNING: Este endpoint é automaticamente DESABILITADO em produção.
    Para gerar keys em produção, use o script CLI: `python scripts/generate-api-key.py`
    """,
    responses={
        201: {
            "description": "API key gerada com sucesso",
            "model": APIKeyResponse,
        },
        403: {"description": "Acesso de administrador necessário ou endpoint desabilitado em produção"},
        500: {"description": "Erro ao gerar chave"},
    },
    status_code=status.HTTP_201_CREATED,
)
async def generate_api_key(
    request: Request,
    _: Annotated[bool, Depends(verify_admin_access)],
    audit_logger: Annotated[AuditLogger, Depends(get_audit_logger)],
    description: str | None = Query(
        None,
        description="Descrição da chave (ex: 'Cliente Hospital XYZ')",
    ),
) -> APIKeyResponse:
    """Gera uma nova API key para autenticação.

    A chave gerada só é exibida uma vez. Guarde-a em local seguro.
    Em produção, armazene apenas o hash da chave.

    ⚠️ SECURITY: Este endpoint é automaticamente bloqueado em produção.
    Use o script CLI `scripts/generate-api-key.py` para gerar keys em produção.

    Args:
        request: Objeto de requisição FastAPI
        _: Verificação de acesso administrativo
        audit_logger: Instância do audit logger
        description: Descrição opcional da chave

    Returns:
        APIKeyResponse com a chave gerada

    Raises:
        HTTPException: Se houver erro na geração ou em ambiente de produção
    """
    # 🔒 BLOQUEIO DE SEGURANÇA: Endpoint desabilitado em produção
    # Motivo: Evitar exposição de geração de keys via HTTP
    # Alternativa: Use o script CLI scripts/generate-api-key.py
    if settings.environment == "production":
        audit_logger.log(
            event_type=AuditEventType.ADMIN_EXPORT,
            correlation_id=str(id(request)),
            action="POST /admin/api-keys",
            resource="/admin/api-keys",
            result="blocked",
            details={
                "reason": "Endpoint disabled in production",
                "description": description,
                "suggestion": "Use CLI script: python scripts/generate-api-key.py",
            },
        )
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="API key generation via HTTP is disabled in production. "
                   "Use the CLI script: python scripts/generate-api-key.py",
        )

    try:
        api_key, key_id = _generate_api_key()
        created_at = datetime.now(timezone.utc).isoformat()

        # Loga a criação (sem expor a chave completa)
        audit_logger.log(
            event_type=AuditEventType.ADMIN_EXPORT,
            correlation_id=str(id(request)),
            action="POST /admin/api-keys",
            resource="/admin/api-keys",
            result="success",
            details={
                "key_id": key_id,
                "description": description,
                "key_prefix": api_key[:8] + "...",
            },
        )

        return APIKeyResponse(
            api_key=api_key,
            key_id=key_id,
            created_at=created_at,
            description=description,
        )

    except Exception as e:
        audit_logger.log(
            event_type=AuditEventType.ADMIN_EXPORT,
            correlation_id=str(id(request)),
            action="POST /admin/api-keys",
            resource="/admin/api-keys",
            result="error",
            details={"error": str(e)},
        )
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Erro ao gerar API key: {str(e)}",
        ) from e


@router.get(
    "/api-keys",
    response_model=APIKeyListResponse,
    summary="Lista API keys ativas",
    description="Retorna lista de API keys geradas (sem expor as chaves completas).",
    responses={
        200: {"description": "Lista de API keys", "model": APIKeyListResponse},
        403: {"description": "Acesso de administrador necessário"},
    },
)
async def list_api_keys(
    request: Request,
    _: Annotated[bool, Depends(verify_admin_access)],
    audit_logger: Annotated[AuditLogger, Depends(get_audit_logger)],
) -> APIKeyListResponse:
    """Lista API keys cadastradas (método placeholder).

    Em uma implementação completa, isso consultaria um banco de dados
    de chaves. Por enquanto, retorna apenas a chave master configurada.

    Args:
        request: Objeto de requisição FastAPI
        _: Verificação de acesso administrativo
        audit_logger: Instância do audit logger

    Returns:
        Lista de API keys
    """
    # Loga o acesso
    audit_logger.log(
        event_type=AuditEventType.DATA_ACCESS,
        correlation_id=str(id(request)),
        action="GET /admin/api-keys",
        resource="/admin/api-keys",
        result="success",
        details={"message": "Listed API keys"},
    )

    # Retorna apenas a chave master configurada (máscara)
    master_key = settings.security_config.api_key
    masked_key = master_key[:8] + "..." + master_key[-4:] if master_key else "N/A"

    return APIKeyListResponse(
        keys=[
            {
                "key_id": "master",
                "description": "Master API Key (environment)",
                "masked": masked_key,
                "type": "environment",
            }
        ],
        total=1,
    )


@router.get(
    "/audit/stats",
    summary="Obtém estatísticas de logs de auditoria",
    description="Retorna estatísticas sobre o sistema de logs de auditoria incluindo contagens e tamanhos de arquivos.",
    responses={
        200: {
            "description": "Estatísticas de logs de auditoria",
            "content": {
                "application/json": {
                    "example": {
                        "log_directory": "/var/log/health-api/audit",
                        "active_log_files": 5,
                        "archived_log_files": 10,
                        "total_size_mb": 45.5,
                        "max_size_bytes": 10485760,
                        "max_age_days": 365,
                    }
                }
            },
        },
        403: {"description": "Acesso de administrador necessário"},
    },
)
async def get_audit_stats(
    request: Request,
    _: Annotated[bool, Depends(verify_admin_access)],
    audit_logger: Annotated[AuditLogger, Depends(get_audit_logger)],
) -> dict[str, Any]:
    """Obtém estatísticas sobre o sistema de logs de auditoria.

    Args:
        request: Objeto de requisição FastAPI
        _: Verificação de acesso administrativo
        audit_logger: Instância do audit logger

    Returns:
        Dicionário com estatísticas de logs de auditoria.
    """
    stats = audit_logger.get_stats()

    # Loga este acesso administrativo
    audit_logger.log(
        event_type=AuditEventType.DATA_ACCESS,
        correlation_id=str(id(request)),
        action="GET /admin/audit/stats",
        resource="/admin/audit/stats",
        result="success",
        details={"stats": stats},
    )

    return stats


@router.get(
    "/audit/export",
    response_class=PlainTextResponse,
    summary="Exporta logs de auditoria em formato ANPD",
    description="Exporta logs de auditoria em formato NDJSON compatível com requisitos da ANPD para auditorias LGPD.",
    responses={
        200: {
            "description": "Logs de auditoria em formato NDJSON",
            "content": {"text/plain": {}},
        },
        403: {"description": "Acesso de administrador necessário"},
        400: {"description": "Intervalo de datas inválido"},
    },
)
async def export_audit_logs(
    request: Request,
    _: Annotated[bool, Depends(verify_admin_access)],
    audit_logger: Annotated[AuditLogger, Depends(get_audit_logger)],
    start_date: datetime | None = Query(
        None,
        description="Data de início para exportação (formato ISO 8601)",
        examples=["2026-01-01T00:00:00Z"],
    ),
    end_date: datetime | None = Query(
        None,
        description="Data de fim para exportação (formato ISO 8601)",
        examples=["2026-04-23T23:59:59Z"],
    ),
    event_type: AuditEventType | None = Query(
        None,
        description="Filtrar por tipo de evento",
    ),
    format: str = Query(
        "ndjson",
        pattern="^(ndjson|json)$",
        description="Formato de exportação (ndjson ou array json)",
    ),
) -> str:
    """Exporta logs de auditoria em formato compatível com ANPD.

    Este endpoint exporta logs de auditoria em formato adequado para submissão
    à Autoridade Nacional de Proteção de Dados (ANPD) conforme exigido
    pelo Artigo 46 da LGPD.

    Args:
        request: Objeto de requisição FastAPI
        _: Verificação de acesso administrativo
        audit_logger: Instância do audit logger
        start_date: Filtro de data de início (inclusivo)
        end_date: Filtro de data de fim (inclusivo)
        event_type: Filtrar por tipo específico de evento
        format: Formato de exportação (ndjson ou json)

    Returns:
        String NDJSON ou JSON contendo entradas de log de auditoria.

    Raises:
        HTTPException: Se intervalo de datas for inválido ou exportação falhar.
    """
    # Valida intervalo de datas
    if start_date and end_date and start_date > end_date:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="start_date deve ser anterior a end_date",
        )

    try:
        # Gera ID de correlação para esta exportação
        correlation_id = f"export-{id(request)}-{datetime.now(timezone.utc).isoformat()}"

        # Obtém entradas filtradas (com ou sem tipo de evento)
        entries = audit_logger.get_entries(
            start_date=start_date,
            end_date=end_date,
            event_type=event_type,
            limit=100000,
            verify_integrity=True,
        )

        if format == "ndjson":
            result = "".join(entry.to_ndjson_line() for entry in entries)
        else:
            import json

            result = json.dumps(
                [entry.to_anpd_format() for entry in entries],
                ensure_ascii=False,
                indent=2,
            )

        # Loga esta operação de exportação
        audit_logger.log(
            event_type=AuditEventType.ADMIN_EXPORT,
            correlation_id=correlation_id,
            action="GET /admin/audit/export",
            resource="/admin/audit/export",
            result="success",
            details={
                "start_date": start_date.isoformat() if start_date else None,
                "end_date": end_date.isoformat() if end_date else None,
                "event_type": event_type.value if event_type else None,
                "format": format,
                "entries_exported": len(entries),
            },
        )

        return result

    except Exception as e:
        logger = get_audit_logger()
        logger.log(
            event_type=AuditEventType.ADMIN_EXPORT,
            correlation_id=f"export-error-{id(request)}",
            action="GET /admin/audit/export",
            resource="/admin/audit/export",
            result="error",
            details={"error": str(e)},
        )
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Falha ao exportar logs de auditoria: {str(e)}",
        ) from e


@router.get(
    "/audit/verify",
    summary="Verifica integridade de logs de auditoria",
    description="Verifica a integridade de entradas de log de auditoria verificando checksums.",
    responses={
        200: {
            "description": "Resultados de verificação de integridade",
            "content": {
                "application/json": {
                    "example": {
                        "total_entries": 1000,
                        "valid_entries": 998,
                        "corrupted_entries": 2,
                        "integrity_percentage": 99.8,
                        "status": "warning",
                    }
                }
            },
        },
        403: {"description": "Acesso de administrador necessário"},
    },
)
async def verify_audit_integrity(
    request: Request,
    _: Annotated[bool, Depends(verify_admin_access)],
    audit_logger: Annotated[AuditLogger, Depends(get_audit_logger)],
    limit: int = Query(10000, ge=1, le=100000, description="Máximo de entradas para verificar"),
) -> dict[str, Any]:
    """Verifica integridade de entradas de log de auditoria.

    Verifica checksums para detectar adulteração.

    Args:
        request: Objeto de requisição FastAPI
        _: Verificação de acesso administrativo
        audit_logger: Instância do audit logger
        limit: Número máximo de entradas para verificar

    Returns:
        Dicionário com resultados de verificação de integridade.
    """
    entries = audit_logger.get_entries(limit=limit, verify_integrity=True)

    # Obtém total de entradas incluindo corrompidas
    all_entries = audit_logger.get_entries(limit=limit, verify_integrity=False)

    total = len(all_entries)
    valid = len(entries)
    corrupted = total - valid

    integrity_pct = (valid / total * 100) if total > 0 else 100.0

    status_label = "ok"
    if corrupted > 0:
        status_label = "critical" if corrupted > 10 else "warning"

    result = {
        "total_entries_checked": total,
        "valid_entries": valid,
        "corrupted_entries": corrupted,
        "integrity_percentage": round(integrity_pct, 2),
        "status": status_label,
        "message": (
            "Todas as entradas verificadas" if corrupted == 0
            else f"{corrupted} entradas corrompidas detectadas"
        ),
    }

    # Loga a verificação
    audit_logger.log(
        event_type=AuditEventType.DATA_ACCESS,
        correlation_id=str(id(request)),
        action="GET /admin/audit/verify",
        resource="/admin/audit/verify",
        result="success",
        details={
            "total_checked": total,
            "corrupted_found": corrupted,
            "integrity_percentage": integrity_pct,
        },
    )

    return result
