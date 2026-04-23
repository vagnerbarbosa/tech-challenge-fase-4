"""Models for LGPD audit logging.

This module defines the AuditLogEntry model used for compliance logging
to meet Brazilian LGPD (Lei Geral de Proteção de Dados) requirements.
"""

from datetime import datetime
from enum import Enum
from typing import Any
from uuid import UUID, uuid4

from pydantic import BaseModel, Field, field_validator


class AuditEventType(str, Enum):
    """Types of auditable events for LGPD compliance."""

    DATA_ACCESS = "data_access"
    DATA_EXPORT = "data_export"
    DATA_DELETION = "data_deletion"
    CONSENT_GIVEN = "consent_given"
    CONSENT_REVOKED = "consent_revoked"
    ANALYSIS_CREATED = "analysis_created"
    ANALYSIS_ACCESSED = "analysis_accessed"
    ADMIN_EXPORT = "admin_export"
    SECURITY_ALERT = "security_alert"
    AUTHENTICATION = "authentication"
    AUTHORIZATION_FAILURE = "authorization_failure"


class AuditLogEntry(BaseModel):
    """Single audit log entry for LGPD compliance.

    All fields are immutable after creation to ensure log integrity.
    This model represents operations on personal data as required by LGPD Art. 46.

    Attributes:
        event_id: Unique identifier for this audit event (UUID v4)
        timestamp: ISO 8601 timestamp of the event
        event_type: Category of the auditable event
        user_id: ID of the user performing the action (hashed/anonymized)
        patient_id: ID of the patient whose data was accessed (hashed)
        correlation_id: Request correlation ID for tracing
        action: Description of the action performed
        resource: Resource being accessed (e.g., endpoint path)
        result: Outcome of the action (success/failure)
        details: Additional structured data about the event
        ip_address: IP address of the requester (hashed for privacy)
        user_agent: User agent string (hashed/anonymized)
        consent_reference: Reference to consent record if applicable
        data_retention_until: Date until which this log must be retained
    """

    model_config = {
        "frozen": True,  # Makes the model immutable
        "json_schema_extra": {
            "example": {
                "event_id": "550e8400-e29b-41d4-a716-446655440000",
                "timestamp": "2026-04-23T10:30:00Z",
                "event_type": "analysis_created",
                "user_id": "sha256:abc123...",
                "patient_id": "sha256:def456...",
                "correlation_id": "req-abc-123",
                "action": "POST /analyze/text",
                "resource": "/analyze/text",
                "result": "success",
                "details": {"modalities": ["text"], "risk_detected": True},
                "ip_address": "sha256:hash...",
                "user_agent": "sha256:hash...",
                "consent_reference": "consent-uuid-123",
                "data_retention_until": "2027-04-23T10:30:00Z",
            }
        },
    }

    event_id: UUID = Field(
        default_factory=uuid4,
        description="Unique identifier for this audit event (UUID v4)",
    )
    timestamp: datetime = Field(
        default_factory=lambda: datetime.utcnow(),
        description="ISO 8601 timestamp of the event (UTC)",
    )
    event_type: AuditEventType = Field(
        ...,
        description="Category of the auditable event",
    )
    user_id: str | None = Field(
        default=None,
        description="Hashed ID of the user performing the action",
    )
    patient_id: str | None = Field(
        default=None,
        description="Hashed ID of the patient whose data was accessed",
    )
    correlation_id: str = Field(
        ...,
        description="Request correlation ID for distributed tracing",
    )
    action: str = Field(
        ...,
        min_length=1,
        max_length=255,
        description="Description of the action performed",
    )
    resource: str = Field(
        ...,
        min_length=1,
        max_length=255,
        description="Resource being accessed (endpoint path, file, etc.)",
    )
    result: str = Field(
        ...,
        pattern="^(success|failure|denied|error)$",
        description="Outcome of the action",
    )
    details: dict[str, Any] = Field(
        default_factory=dict,
        description="Additional structured data about the event (no PII)",
    )
    ip_address: str | None = Field(
        default=None,
        description="Hashed IP address of the requester",
    )
    user_agent: str | None = Field(
        default=None,
        description="Hashed user agent string",
    )
    consent_reference: str | None = Field(
        default=None,
        description="Reference to consent record if applicable",
    )
    data_retention_until: datetime = Field(
        default_factory=lambda: datetime.utcnow(),
        description="Date until which this log must be retained per LGPD",
    )

    @field_validator("timestamp", mode="before")
    @classmethod
    def ensure_utc_timestamp(cls, v: datetime | None) -> datetime:
        """Ensure timestamp is UTC."""
        if v is None:
            return datetime.utcnow()
        if v.tzinfo is not None:
            from datetime import timezone
            return v.replace(tzinfo=None)
        return v

    @field_validator("data_retention_until", mode="before")
    @classmethod
    def set_retention_period(cls, v: datetime | None, info: Any) -> datetime:
        """Set default retention period to 1 year from timestamp if not provided."""
        if v is None:
            timestamp = info.data.get("timestamp")
            if timestamp:
                from datetime import timedelta
                return timestamp + timedelta(days=365)
            return datetime.utcnow() + timedelta(days=365)
        return v

    def to_anpd_format(self) -> dict[str, Any]:
        """Convert to ANPD (Brazilian Data Protection Authority) export format.

        Returns:
            Dictionary formatted according to ANPD audit requirements.
        """
        return {
            "idEvento": str(self.event_id),
            "dataHora": self.timestamp.isoformat() + "Z",
            "tipoEvento": self.event_type.value,
            "usuario": self.user_id,
            "titularDados": self.patient_id,
            "idCorrelacao": self.correlation_id,
            "acao": self.action,
            "recurso": self.resource,
            "resultado": self.result,
            "detalhes": self.details,
            "enderecoIp": self.ip_address,
            "agenteUsuario": self.user_agent,
            "referenciaConsentimento": self.consent_reference,
            "retencaoAte": self.data_retention_until.isoformat() + "Z",
        }

    def to_ndjson_line(self) -> str:
        """Export as NDJSON (Newline Delimited JSON) line.

        Returns:
            JSON string terminated with newline for NDJSON format.
        """
        import json

        return json.dumps(self.to_anpd_format(), ensure_ascii=False, separators=(",", ":")) + "\n"


class AuditLogExport(BaseModel):
    """Model for audit log export operations.

    Used for bulk export of audit logs in ANPD-compliant format.
    """

    model_config = {"frozen": True}

    entries: list[AuditLogEntry] = Field(
        ...,
        description="List of audit log entries to export",
    )
    export_timestamp: datetime = Field(
        default_factory=lambda: datetime.utcnow(),
        description="Timestamp of the export operation",
    )
    exported_by: str | None = Field(
        default=None,
        description="ID of the user who initiated the export",
    )
    total_entries: int = Field(
        ...,
        ge=0,
        description="Total number of entries in this export",
    )

    def to_ndjson(self) -> str:
        """Export all entries as NDJSON string.

        Returns:
            NDJSON formatted string with all entries.
        """
        return "".join(entry.to_ndjson_line() for entry in self.entries)

    def to_json_array(self) -> list[dict[str, Any]]:
        """Export all entries as JSON array.

        Returns:
            List of dictionaries in ANPD format.
        """
        return [entry.to_anpd_format() for entry in self.entries]
