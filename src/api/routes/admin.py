"""Admin routes for audit log export and LGPD compliance.

This module provides administrative endpoints for managing audit logs
and exporting data in ANPD-compliant format as required by LGPD.
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
    """Verify admin access for protected endpoints.

    In production, this should validate a proper admin token/API key.
    For now, it checks for a header-based admin key.

    Args:
        request: FastAPI request object

    Returns:
        True if admin access is granted

    Raises:
        HTTPException: If admin access is denied
    """
    # Check for admin API key header
    admin_key = request.headers.get("X-Admin-Key")

    # In production, this should check against a secure admin key
    # For development, we allow a simple check
    expected_key = getattr(settings, "admin_api_key", None)

    if not expected_key:
        # If no admin key is configured, deny access in production
        if settings.environment == "production":
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Admin access not configured",
            )
        # In development, allow without key for testing
        return True

    if admin_key != expected_key:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Invalid admin credentials",
        )

    return True


@router.get(
    "/audit/stats",
    summary="Get audit log statistics",
    description="Returns statistics about the audit log system including file counts and sizes.",
    responses={
        200: {
            "description": "Audit log statistics",
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
        403: {"description": "Admin access required"},
    },
)
async def get_audit_stats(
    request: Request,
    _: Annotated[bool, Depends(verify_admin_access)],
    audit_logger: Annotated[AuditLogger, Depends(get_audit_logger)],
) -> dict[str, Any]:
    """Get statistics about the audit log system.

    Args:
        request: FastAPI request object
        _: Admin access verification
        audit_logger: Audit logger instance

    Returns:
        Dictionary with audit log statistics.
    """
    stats = audit_logger.get_stats()

    # Log this admin access
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
    summary="Export audit logs in ANPD format",
    description="Exports audit logs in NDJSON format compliant with ANPD requirements for LGPD audits.",
    responses={
        200: {
            "description": "Audit logs in NDJSON format",
            "content": {"text/plain": {}},
        },
        403: {"description": "Admin access required"},
        400: {"description": "Invalid date range"},
    },
)
async def export_audit_logs(
    request: Request,
    _: Annotated[bool, Depends(verify_admin_access)],
    audit_logger: Annotated[AuditLogger, Depends(get_audit_logger)],
    start_date: datetime | None = Query(
        None,
        description="Start date for export (ISO 8601 format)",
        example="2026-01-01T00:00:00Z",
    ),
    end_date: datetime | None = Query(
        None,
        description="End date for export (ISO 8601 format)",
        example="2026-04-23T23:59:59Z",
    ),
    event_type: AuditEventType | None = Query(
        None,
        description="Filter by event type",
    ),
    format: str = Query(
        "ndjson",
        pattern="^(ndjson|json)$",
        description="Export format (ndjson or json array)",
    ),
) -> str:
    """Export audit logs in ANPD-compliant format.

    This endpoint exports audit logs in a format suitable for submission
to the Brazilian National Data Protection Authority (ANPD) as required
    by LGPD Article 46.

    Args:
        request: FastAPI request object
        _: Admin access verification
        audit_logger: Audit logger instance
        start_date: Start date filter (inclusive)
        end_date: End date filter (inclusive)
        event_type: Filter by specific event type
        format: Export format (ndjson or json)

    Returns:
        NDJSON or JSON string containing audit log entries.

    Raises:
        HTTPException: If date range is invalid or export fails.
    """
    # Validate date range
    if start_date and end_date and start_date > end_date:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="start_date must be before end_date",
        )

    try:
        # Generate correlation ID for this export
        correlation_id = f"export-{id(request)}-{datetime.utcnow().isoformat()}"

        if event_type:
            # Get entries filtered by event type
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
            # Use the built-in export function
            result = audit_logger.export_for_anpd(
                start_date=start_date,
                end_date=end_date,
                format=format,
            )

        # Log this export operation
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
            detail=f"Failed to export audit logs: {str(e)}",
        ) from e


@router.get(
    "/audit/verify",
    summary="Verify audit log integrity",
    description="Verifies the integrity of audit log entries by checking checksums.",
    responses={
        200: {
            "description": "Integrity check results",
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
        403: {"description": "Admin access required"},
    },
)
async def verify_audit_integrity(
    request: Request,
    _: Annotated[bool, Depends(verify_admin_access)],
    audit_logger: Annotated[AuditLogger, Depends(get_audit_logger)],
    limit: int = Query(10000, ge=1, le=100000, description="Maximum entries to verify"),
) -> dict[str, Any]:
    """Verify integrity of audit log entries.

    Checks checksums for audit log entries to detect tampering.

    Args:
        request: FastAPI request object
        _: Admin access verification
        audit_logger: Audit logger instance
        limit: Maximum number of entries to verify

    Returns:
        Dictionary with integrity verification results.
    """
    entries = audit_logger.get_entries(limit=limit, verify_integrity=True)

    # Get total entries including corrupted ones
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
            "All entries verified" if corrupted == 0
            else f"{corrupted} corrupted entries detected"
        ),
    }

    # Log the verification
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
