"""Rotas administrativas para exportação de logs de auditoria e compliance LGPD.

Este módulo fornece endpoints administrativos para gerenciamento de logs de auditoria
e exportação de dados em formato compatível com ANPD conforme exigido pela LGPD.
"""

from __future__ import annotations

from datetime import datetime
from typing import Annotated, Any

from fastapi import APIRouter, Depends, HTTPException, Query, Request, status
from fastapi.responses import PlainTextResponse

from src.core.config import settings
from src.models.audit_log import AuditEventType
from src.utils.audit_logger import AuditLogger, get_audit_logger

router = APIRouter(prefix="/admin", tags=["Admin"])


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
        correlation_id = f"export-{id(request)}-{datetime.utcnow().isoformat()}"

        if event_type:
            # Obtém entradas filtradas por tipo de evento
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
        else:
            # Usa a função de exportação interna
            result = audit_logger.export_for_anpd(
                start_date=start_date,
                end_date=end_date,
                format=format,
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
                "entries_exported": len(entries) if isinstance(result, str) and event_type else None,
            },
        )

        return result if isinstance(result, str) else str(result)

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
