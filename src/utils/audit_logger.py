"""Logging de auditoria compatível com LGPD com rotação de logs e imutabilidade.

Este módulo fornece logging de auditoria à prova de violação para conformidade
com os requisitos da LGPD (Lei Geral de Proteção de Dados) brasileira.

Features:
- Logging estruturado em JSON com checksums de integridade
- Rotação de logs por tamanho e tempo
- Entradas de log imutáveis com verificação de checksum
- Formato de exportação compatível com ANPD
- Limpeza automática de logs expirados
- Operações thread-safe

Usage:
    from src.utils.audit_logger import get_audit_logger
    from src.models.audit_log import AuditEventType

    audit_logger = get_audit_logger()
    audit_logger.log(
        event_type=AuditEventType.ANALYSIS_CREATED,
        correlation_id="req-123",
        action="POST /analyze/text",
        resource="/analyze/text",
        result="success",
        patient_id="patient-uuid",
        details={"modalities": ["text"]},
    )
"""

from __future__ import annotations

import gzip
import hashlib
import json
import os
import shutil
import threading
from datetime import datetime, timedelta
from pathlib import Path
from typing import Any, Final

from src.core.logging_config import get_logger
from src.models.audit_log import AuditEventType, AuditLogEntry

logger = get_logger(__name__)

# Constants for log management
DEFAULT_LOG_DIR: Final[str] = "logs/audit"
MAX_LOG_SIZE_BYTES: Final[int] = 10 * 1024 * 1024  # 10 MB
MAX_LOG_AGE_DAYS: Final[int] = 365  # LGPD requires 1 year retention
MAX_ARCHIVED_LOGS: Final[int] = 100


def _hash_sensitive_data(data: str) -> str:
    """Faz hash de dados sensíveis usando SHA-256.

    Args:
        data: Dados sensíveis brutos para fazer hash.

    Returns:
        Hash SHA-256 prefixado com identificador do algoritmo.
    """
    if not data:
        return ""
    hash_value = hashlib.sha256(data.encode("utf-8")).hexdigest()[:32]
    return f"sha256:{hash_value}"


class AuditLogger:
    """Logger de auditoria thread-safe com rotação de logs e imutabilidade.

    Esta classe fornece logging de auditoria compatível com LGPD com:
    - Rotação automática de logs baseada no tamanho do arquivo
    - Entradas de log à prova de violação com checksums
    - Operações thread-safe
    - Formato de exportação compatível com ANPD

    Attributes:
        log_dir: Diretório onde os logs de auditoria são armazenados
        current_log_file: Caminho para o arquivo de log ativo atual
        _lock: Lock de threading para acesso concorrente seguro
        _current_size: Tamanho atual do arquivo de log ativo
    """

    _instance: AuditLogger | None = None
    _instance_lock = threading.Lock()

    def __new__(cls, *args: Any, **kwargs: Any) -> AuditLogger:
        """Padrão singleton para garantir instância única do logger de auditoria."""
        if cls._instance is None:
            with cls._instance_lock:
                if cls._instance is None:
                    cls._instance = super().__new__(cls)
        return cls._instance

    def __init__(
        self,
        log_dir: str | None = None,
        max_size_bytes: int = MAX_LOG_SIZE_BYTES,
        max_age_days: int = MAX_LOG_AGE_DAYS,
    ) -> None:
        """Inicializa o logger de auditoria.

        Args:
            log_dir: Diretório para arquivos de log de auditoria (padrão: logs/audit)
            max_size_bytes: Tamanho máximo do arquivo de log antes da rotação (padrão: 10MB)
            max_age_days: Idade máxima dos logs arquivados antes da exclusão (padrão: 365)
        """
        # Avoid re-initialization if already initialized
        if hasattr(self, "_initialized"):
            return

        self.log_dir = Path(log_dir or DEFAULT_LOG_DIR)
        self.max_size_bytes = max_size_bytes
        self.max_age_days = max_age_days
        self._lock = threading.Lock()
        self._current_size = 0
        self._initialized = True

        # Ensure log directory exists
        self._ensure_log_directory()

        # Initialize current log file
        self.current_log_file = self._get_current_log_file()
        self._current_size = self._get_file_size(self.current_log_file)

        logger.info(
            "Audit logger initialized",
            log_dir=str(self.log_dir),
            max_size_bytes=max_size_bytes,
            max_age_days=max_age_days,
        )

    def _ensure_log_directory(self) -> None:
        """Cria diretório de logs se não existir."""
        try:
            self.log_dir.mkdir(parents=True, exist_ok=True)
        except OSError as e:
            # Fallback to local directory if unable to create system log dir
            fallback_dir = Path("./logs/audit")
            fallback_dir.mkdir(parents=True, exist_ok=True)
            self.log_dir = fallback_dir
            logger.warning(
                "Failed to create system log directory, using fallback",
                original_dir=str(self.log_dir),
                fallback_dir=str(fallback_dir),
                error=str(e),
            )

    def _get_current_log_file(self) -> Path:
        """Obtém ou cria o arquivo de log ativo atual.

        Returns:
            Caminho para o arquivo de log ativo atual.
        """
        today = datetime.utcnow().strftime("%Y-%m-%d")
        log_file = self.log_dir / f"audit-{today}.log"

        # If file exists and is too large, rotate it
        if log_file.exists() and log_file.stat().st_size >= self.max_size_bytes:
            self._rotate_log(log_file)

        return log_file

    def _get_file_size(self, file_path: Path) -> int:
        """Obtém tamanho do arquivo em bytes.

        Args:
            file_path: Caminho para o arquivo.

        Returns:
            Tamanho do arquivo em bytes, ou 0 se o arquivo não existir.
        """
        if file_path.exists():
            return file_path.stat().st_size
        return 0

    def _rotate_log(self, log_file: Path) -> None:
        """Rotaciona o arquivo de log atual.

        Comprime o log atual e renomeia com timestamp.

        Args:
            log_file: Caminho para o arquivo de log a ser rotacionado.
        """
        if not log_file.exists():
            return

        timestamp = datetime.utcnow().strftime("%Y%m%d_%H%M%S")
        rotated_file = self.log_dir / f"audit-{timestamp}.log.gz"

        try:
            # Compress and move the log file
            with open(log_file, "rb") as f_in, gzip.open(rotated_file, "wb") as f_out:
                shutil.copyfileobj(f_in, f_out)

            # Remove original file
            log_file.unlink()

            logger.info(
                "Log rotated",
                rotated_file=str(rotated_file),
                original_size=os.path.getsize(rotated_file),
            )

            # Clean up old archived logs
            self._cleanup_old_logs()

        except OSError as e:
            logger.error("Failed to rotate log", error=str(e), log_file=str(log_file))

    def _cleanup_old_logs(self) -> None:
        """Remove logs arquivados mais antigos que max_age_days."""
        cutoff_date = datetime.utcnow() - timedelta(days=self.max_age_days)

        try:
            for log_file in self.log_dir.glob("audit-*.log.gz"):
                try:
                    mtime = datetime.fromtimestamp(log_file.stat().st_mtime)
                    if mtime < cutoff_date:
                        log_file.unlink()
                        logger.info("Deleted old audit log", file=str(log_file))
                except OSError:
                    continue
        except OSError as e:
            logger.error("Failed to cleanup old logs", error=str(e))

    def _write_entry_with_integrity(self, entry: AuditLogEntry) -> bytes:
        """Converte entrada para bytes JSON com checksum de integridade.

        Adiciona um checksum SHA-256 para detectar violações.

        Args:
            entry: A entrada de log de auditoria para serializar.

        Returns:
            Bytes JSON com checksum de integridade.
        """
        entry_dict = entry.model_dump(mode="json")

        # Remove existing checksum if present
        entry_dict.pop("_checksum", None)

        # Calculate checksum
        json_str = json.dumps(entry_dict, sort_keys=True, ensure_ascii=False)
        checksum = hashlib.sha256(json_str.encode("utf-8")).hexdigest()

        # Add checksum to entry
        entry_dict["_checksum"] = checksum

        # Return as JSON bytes with newline
        return (json.dumps(entry_dict, ensure_ascii=False) + "\n").encode("utf-8")

    def _verify_entry_integrity(self, entry_line: str) -> bool:
        """Verifica a integridade de uma entrada de log.

        Args:
            entry_line: String JSON da entrada de log.

        Returns:
            True se a integridade da entrada for válida, False caso contrário.
        """
        try:
            entry_dict = json.loads(entry_line)
            stored_checksum = entry_dict.pop("_checksum", None)

            if not stored_checksum:
                return False

            # Recalculate checksum
            json_str = json.dumps(entry_dict, sort_keys=True, ensure_ascii=False)
            calculated_checksum = hashlib.sha256(json_str.encode("utf-8")).hexdigest()

            return stored_checksum == calculated_checksum
        except (json.JSONDecodeError, KeyError):
            return False

    def log(
        self,
        event_type: AuditEventType,
        correlation_id: str,
        action: str,
        resource: str,
        result: str,
        user_id: str | None = None,
        patient_id: str | None = None,
        details: dict[str, Any] | None = None,
        ip_address: str | None = None,
        user_agent: str | None = None,
        consent_reference: str | None = None,
    ) -> AuditLogEntry:
        """Cria e registra uma entrada de auditoria.

        Args:
            event_type: Tipo de evento de auditoria
            correlation_id: ID de correlação da requisição
            action: Descrição da ação realizada
            resource: Recurso sendo acessado
            result: Resultado (success/failure/denied/error)
            user_id: ID do usuário (será hasheado)
            patient_id: ID do paciente (será hasheado)
            details: Dados estruturados adicionais (sem PII)
            ip_address: Endereço IP (será hasheado)
            user_agent: String do user agent (será hasheado)
            consent_reference: Referência ao registro de consentimento

        Returns:
            A AuditLogEntry criada.
        """
        # Hash sensitive fields
        hashed_user_id = _hash_sensitive_data(user_id) if user_id else None
        hashed_patient_id = _hash_sensitive_data(patient_id) if patient_id else None
        hashed_ip = _hash_sensitive_data(ip_address) if ip_address else None
        hashed_ua = _hash_sensitive_data(user_agent) if user_agent else None

        # Calculate retention date (1 year from now per LGPD)
        retention_until = datetime.utcnow() + timedelta(days=365)

        entry = AuditLogEntry(
            event_type=event_type,
            correlation_id=correlation_id,
            action=action,
            resource=resource,
            result=result,
            user_id=hashed_user_id,
            patient_id=hashed_patient_id,
            details=details or {},
            ip_address=hashed_ip,
            user_agent=hashed_ua,
            consent_reference=consent_reference,
            data_retention_until=retention_until,
        )

        self._write_entry(entry)
        return entry

    def _write_entry(self, entry: AuditLogEntry) -> None:
        """Escreve entrada no arquivo de log com thread safety.

        Args:
            entry: A entrada de log de auditoria para escrever.
        """
        with self._lock:
            # Check if rotation is needed
            if self._current_size >= self.max_size_bytes:
                self._rotate_log(self.current_log_file)
                self.current_log_file = self._get_current_log_file()
                self._current_size = 0

            # Write entry with integrity checksum
            entry_bytes = self._write_entry_with_integrity(entry)

            try:
                with open(self.current_log_file, "ab") as f:
                    f.write(entry_bytes)
                    f.flush()
                    os.fsync(f.fileno())  # Ensure durable write
                    self._current_size += len(entry_bytes)
            except OSError as e:
                logger.error(
                    "Failed to write audit log entry",
                    error=str(e),
                    event_type=entry.event_type.value,
                )

    def log_auth(
        self,
        success: bool,
        correlation_id: str,
        ip_address: str | None = None,
        user_id: str | None = None,
        reason: str | None = None,
    ) -> AuditLogEntry:
        """Registra evento de autenticação.

        Args:
            success: Se a autenticação teve sucesso
            correlation_id: ID de correlação da requisição
            ip_address: Endereço IP do cliente (será hasheado)
            user_id: ID do usuário (será hasheado)
            reason: Motivo da falha (se aplicável)

        Returns:
            A AuditLogEntry criada.
        """
        event_type = AuditEventType.AUTHENTICATION if success else AuditEventType.AUTHORIZATION_FAILURE
        details: dict[str, Any] = {"success": success}
        if reason:
            details["reason"] = reason

        return self.log(
            event_type=event_type,
            correlation_id=correlation_id,
            action="authentication" if success else "authentication_failure",
            resource="/auth",
            result="success" if success else "denied",
            user_id=user_id,
            ip_address=ip_address,
            details=details,
        )

    def log_data_access(
        self,
        resource: str,
        action: str,
        correlation_id: str,
        patient_id: str | None = None,
        user_id: str | None = None,
        ip_address: str | None = None,
        details: dict[str, Any] | None = None,
    ) -> AuditLogEntry:
        """Registra evento de acesso a dados.

        Args:
            resource: Recurso sendo acessado (ex: 'text_analysis')
            action: Ação realizada (ex: 'read', 'write')
            correlation_id: ID de correlação da requisição
            patient_id: ID do paciente (será hasheado)
            user_id: ID do usuário (será hasheado)
            ip_address: Endereço IP do cliente (será hasheado)
            details: Detalhes adicionais do evento

        Returns:
            A AuditLogEntry criada.
        """
        merged_details = {"resource": resource, "action": action}
        if details:
            merged_details.update(details)

        return self.log(
            event_type=AuditEventType.DATA_ACCESS,
            correlation_id=correlation_id,
            action=f"{action}_{resource}",
            resource=resource,
            result="success",
            user_id=user_id,
            patient_id=patient_id,
            ip_address=ip_address,
            details=merged_details,
        )

    def log_analysis_created(
        self,
        correlation_id: str,
        resource: str,
        patient_id: str | None = None,
        modalities: list[str] | None = None,
        risk_detected: bool = False,
        user_id: str | None = None,
        ip_address: str | None = None,
    ) -> AuditLogEntry:
        """Registra evento de criação de análise.

        Args:
            correlation_id: ID de correlação da requisição
            resource: Caminho do recurso (ex: '/analyze/text')
            patient_id: ID do paciente (será hasheado)
            modalities: Lista de modalidades processadas
            risk_detected: Se algum risco foi detectado
            user_id: ID do usuário (será hasheado)
            ip_address: Endereço IP do cliente (será hasheado)

        Returns:
            A AuditLogEntry criada.
        """
        return self.log(
            event_type=AuditEventType.ANALYSIS_CREATED,
            correlation_id=correlation_id,
            action="POST",
            resource=resource,
            result="success",
            user_id=user_id,
            patient_id=patient_id,
            ip_address=ip_address,
            details={
                "modalities": modalities or [],
                "risk_detected": risk_detected,
            },
        )

    def log_security_alert(
        self,
        alert_type: str,
        severity: str,
        correlation_id: str,
        details: dict[str, Any] | None = None,
        ip_address: str | None = None,
    ) -> AuditLogEntry:
        """Registra alerta/evento de segurança.

        Args:
            alert_type: Tipo de evento de segurança (ex: 'rate_limit_exceeded')
            severity: Nível de severidade ('low', 'medium', 'high', 'critical')
            correlation_id: ID de correlação da requisição
            details: Detalhes adicionais do evento
            ip_address: Endereço IP do cliente (será hasheado)

        Returns:
            A AuditLogEntry criada.
        """
        merged_details: dict[str, Any] = {"alert_type": alert_type, "severity": severity}
        if details:
            merged_details.update(details)

        return self.log(
            event_type=AuditEventType.SECURITY_ALERT,
            correlation_id=correlation_id,
            action=alert_type,
            resource="security",
            result="alert",
            ip_address=ip_address,
            details=merged_details,
        )

    def get_entries(
        self,
        start_date: datetime | None = None,
        end_date: datetime | None = None,
        event_type: AuditEventType | None = None,
        patient_id: str | None = None,
        limit: int = 1000,
        verify_integrity: bool = True,
    ) -> list[AuditLogEntry]:
        """Recupera entradas de log de auditoria com filtros opcionais.

        Args:
            start_date: Filtrar entradas a partir desta data
            end_date: Filtrar entradas até esta data
            event_type: Filtrar por tipo de evento
            patient_id: Filtrar por ID do paciente (será hasheado)
            limit: Número máximo de entradas para retornar
            verify_integrity: Se deve verificar os checksums das entradas

        Returns:
            Lista de entradas de log de auditoria que correspondem aos filtros.
        """
        entries: list[AuditLogEntry] = []
        hashed_patient_id = _hash_sensitive_data(patient_id) if patient_id else None

        # Collect all log files (current and archived)
        log_files = sorted(self.log_dir.glob("audit-*.log"), reverse=True)
        archived_files = sorted(self.log_dir.glob("audit-*.log.gz"), reverse=True)

        for log_file in log_files:
            entries.extend(
                self._read_log_file(
                    log_file,
                    start_date,
                    end_date,
                    event_type,
                    hashed_patient_id,
                    verify_integrity,
                )
            )
            if len(entries) >= limit:
                break

        # Read archived logs if needed
        if len(entries) < limit:
            for archived_file in archived_files:
                entries.extend(
                    self._read_archived_log_file(
                        archived_file,
                        start_date,
                        end_date,
                        event_type,
                        hashed_patient_id,
                        verify_integrity,
                    )
                )
                if len(entries) >= limit:
                    break

        return entries[:limit]

    def _read_log_file(
        self,
        log_file: Path,
        start_date: datetime | None,
        end_date: datetime | None,
        event_type: AuditEventType | None,
        hashed_patient_id: str | None,
        verify_integrity: bool,
    ) -> list[AuditLogEntry]:
        """Lê entradas de um único arquivo de log.

        Args:
            log_file: Caminho para o arquivo de log
            start_date: Filtrar a partir desta data
            end_date: Filtrar até esta data
            event_type: Filtrar por tipo de evento
            hashed_patient_id: Filtrar por ID do paciente hasheado
            verify_integrity: Se deve verificar checksums

        Returns:
            Lista de entradas correspondentes.
        """
        entries = []

        try:
            with open(log_file, encoding="utf-8") as f:
                for line in f:
                    line = line.strip()
                    if not line:
                        continue

                    try:
                        if verify_integrity and not self._verify_entry_integrity(line):
                            logger.warning("Integrity check failed for log entry", line=line[:100])
                            continue

                        entry_dict = json.loads(line)
                        entry_dict.pop("_checksum", None)  # Remove checksum before parsing

                        entry = AuditLogEntry.model_validate(entry_dict)

                        # Apply filters
                        if start_date and entry.timestamp < start_date:
                            continue
                        if end_date and entry.timestamp > end_date:
                            continue
                        if event_type and entry.event_type != event_type:
                            continue
                        if hashed_patient_id and entry.patient_id != hashed_patient_id:
                            continue

                        entries.append(entry)
                    except (json.JSONDecodeError, ValueError) as e:
                        logger.warning("Failed to parse audit log entry", error=str(e))
                        continue
        except OSError as e:
            logger.error("Failed to read audit log file", error=str(e), file=str(log_file))

        return entries

    def _read_archived_log_file(
        self,
        archived_file: Path,
        start_date: datetime | None,
        end_date: datetime | None,
        event_type: AuditEventType | None,
        hashed_patient_id: str | None,
        verify_integrity: bool,
    ) -> list[AuditLogEntry]:
        """Lê entradas de um arquivo de log arquivado gzipped.

        Args:
            archived_file: Caminho para o arquivo de log gzipped
            start_date: Filtrar a partir desta data
            end_date: Filtrar até esta data
            event_type: Filtrar por tipo de evento
            hashed_patient_id: Filtrar por ID do paciente hasheado
            verify_integrity: Se deve verificar checksums

        Returns:
            Lista de entradas correspondentes.
        """
        entries = []

        try:
            with gzip.open(archived_file, "rt", encoding="utf-8") as f:
                for line in f:
                    line = line.strip()
                    if not line:
                        continue

                    try:
                        if verify_integrity and not self._verify_entry_integrity(line):
                            logger.warning(
                                "Integrity check failed for archived log entry",
                                file=str(archived_file),
                            )
                            continue

                        entry_dict = json.loads(line)
                        entry_dict.pop("_checksum", None)

                        entry = AuditLogEntry.model_validate(entry_dict)

                        # Apply filters
                        if start_date and entry.timestamp < start_date:
                            continue
                        if end_date and entry.timestamp > end_date:
                            continue
                        if event_type and entry.event_type != event_type:
                            continue
                        if hashed_patient_id and entry.patient_id != hashed_patient_id:
                            continue

                        entries.append(entry)
                    except (json.JSONDecodeError, ValueError) as e:
                        logger.warning("Failed to parse archived audit log entry", error=str(e))
                        continue
        except OSError as e:
            logger.error(
                "Failed to read archived audit log file",
                error=str(e),
                file=str(archived_file),
            )

        return entries

    def export_for_anpd(
        self,
        start_date: datetime | None = None,
        end_date: datetime | None = None,
        format: str = "ndjson",
    ) -> str | list[dict[str, Any]]:
        """Exporta logs de auditoria em formato compatível com ANPD.

        Args:
            start_date: Data inicial para o intervalo de exportação
            end_date: Data final para o intervalo de exportação
            format: Formato de exportação ("ndjson" ou "json")

        Returns:
            String NDJSON ou lista de dicionários.

        Raises:
            ValueError: Se o formato não for suportado.
        """
        entries = self.get_entries(
            start_date=start_date,
            end_date=end_date,
            limit=100000,  # High limit for exports
            verify_integrity=True,
        )

        if format == "ndjson":
            return "".join(entry.to_ndjson_line() for entry in entries)
        elif format == "json":
            return [entry.to_anpd_format() for entry in entries]
        else:
            raise ValueError(f"Unsupported export format: {format}")

    def get_stats(self) -> dict[str, Any]:
        """Obtém estatísticas sobre o log de auditoria.

        Returns:
            Dicionário com estatísticas do log de auditoria.
        """
        total_size = 0
        file_count = 0
        archived_count = 0

        for log_file in self.log_dir.glob("audit-*.log"):
            total_size += log_file.stat().st_size
            file_count += 1

        for archived_file in self.log_dir.glob("audit-*.log.gz"):
            total_size += archived_file.stat().st_size
            archived_count += 1

        return {
            "log_directory": str(self.log_dir),
            "active_log_files": file_count,
            "archived_log_files": archived_count,
            "total_size_bytes": total_size,
            "total_size_mb": round(total_size / (1024 * 1024), 2),
            "max_size_bytes": self.max_size_bytes,
            "max_age_days": self.max_age_days,
            "current_log_file": str(self.current_log_file),
        }


def get_audit_logger(
    log_dir: str | None = None,
    max_size_bytes: int = MAX_LOG_SIZE_BYTES,
    max_age_days: int = MAX_LOG_AGE_DAYS,
) -> AuditLogger:
    """Obtém ou cria a instância singleton do logger de auditoria.

    Args:
        log_dir: Diretório para arquivos de log de auditoria
        max_size_bytes: Tamanho máximo do arquivo de log antes da rotação
        max_age_days: Idade máxima dos logs arquivados

    Returns:
        Instância singleton de AuditLogger.
    """
    return AuditLogger(log_dir, max_size_bytes, max_age_days)
