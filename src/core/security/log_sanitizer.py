"""Utilitários de sanitização de logs.

Fornece mascaramento de secrets e hash de PII para logging seguro.
Implementa proteção de dados compatível com LGPD para logs e mensagens de erro.
"""

import hashlib
import re
from typing import Any


class SecretMasker:
    """Mascara informações sensíveis em mensagens de log.

    Usa padrões de regex para identificar e mascarar secrets como chaves de API,
    credenciais Azure, tokens e outros dados sensíveis.

    Implementa FR-009 da especificação: mascarar secrets em logs.
    """

    # Patterns for secret detection
    PATTERNS: dict[str, re.Pattern[str]] = {
        # Azure keys (32-64 hex chars or base64-like)
        "azure_key": re.compile(
            r"([a-f0-9]{32,64})|([A-Za-z0-9+/]{40,88}=?)",
            re.IGNORECASE,
        ),
        # API keys with common prefixes
        "api_key": re.compile(
            r"(api[_-]?key|apikey|x-api-key)[\s]*[:=][\s]*([\w-]+)",
            re.IGNORECASE,
        ),
        # Bearer tokens
        "bearer_token": re.compile(
            r"Bearer\s+([A-Za-z0-9-_]+\.[A-Za-z0-9-_]+\.[A-Za-z0-9-_]+)",
            re.IGNORECASE,
        ),
        # Authorization header values
        "auth_header": re.compile(
            r"(authorization|auth)[\s]*[:=][\s]*([\w\s-]+)",
            re.IGNORECASE,
        ),
        # Connection strings with passwords
        "connection_string": re.compile(
            r"(password|pwd|passwd)[\s]*[:=][\s]*([^;\s]+)",
            re.IGNORECASE,
        ),
        # Private keys
        "private_key": re.compile(
            r"(-----BEGIN (RSA |EC |DSA |OPENSSH )?PRIVATE KEY-----)[\s\S]*?(-----END)",
            re.IGNORECASE,
        ),
        # AWS Access Key ID
        "aws_key": re.compile(
            r"AKIA[0-9A-Z]{16}",
            re.IGNORECASE,
        ),
        # JWT tokens
        "jwt_token": re.compile(
            r"eyJ[A-Za-z0-9-_]*\.eyJ[A-Za-z0-9-_]*\.[A-Za-z0-9-_]*",
            re.IGNORECASE,
        ),
    }

    MASK_VALUE = "***REDACTED***"
    MASK_AZURE_KEY = "****-****-****-AZURE"

    @classmethod
    def mask(cls, text: str | None) -> str:
        """Mascara secrets em texto.

        Args:
            text: Texto para sanitizar

        Returns:
            Texto sanitizado com secrets mascarados
        """
        if text is None:
            return ""

        result = text
        for name, pattern in cls.PATTERNS.items():
            if "azure" in name:
                result = pattern.sub(cls.MASK_AZURE_KEY, result)
            else:
                result = pattern.sub(cls.MASK_VALUE, result)
        return result

    @classmethod
    def mask_dict(cls, data: dict[str, Any]) -> dict[str, Any]:
        """Recursivamente mascara secrets em valores de dicionário.

        Args:
            data: Dicionário para sanitizar

        Returns:
            Dicionário sanitizado
        """
        if not isinstance(data, dict):
            return data

        sanitized: dict[str, Any] = {}
        sensitive_keys = {
            "api_key", "apikey", "key", "secret", "password", "token",
            "credential", "auth", "authorization", "azure_text_key",
            "azure_speech_key", "azure_vision_key", "connection_string",
            "private_key", "access_key", "secret_key", "client_secret",
        }

        for key, value in data.items():
            key_lower = key.lower()

            if isinstance(value, str):
                if any(sk in key_lower for sk in sensitive_keys):
                    sanitized[key] = cls.MASK_VALUE
                else:
                    sanitized[key] = cls.mask(value)
            elif isinstance(value, dict):
                sanitized[key] = cls.mask_dict(value)
            elif isinstance(value, list):
                sanitized[key] = cls.mask_list(value)
            else:
                sanitized[key] = value

        return sanitized

    @classmethod
    def mask_list(cls, data: list[Any]) -> list[Any]:
        """Recursivamente mascara secrets em valores de lista.

        Args:
            data: Lista para sanitizar

        Returns:
            Lista sanitizada
        """
        sanitized: list[Any] = []
        for item in data:
            if isinstance(item, str):
                sanitized.append(cls.mask(item))
            elif isinstance(item, dict):
                sanitized.append(cls.mask_dict(item))
            elif isinstance(item, list):
                sanitized.append(cls.mask_list(item))
            else:
                sanitized.append(item)
        return sanitized

    @classmethod
    def mask_exception_message(cls, message: str | None) -> str:
        """Mascara secrets em mensagens de exceção.

        Garante que mensagens de erro não vazem dados sensíveis.

        Args:
            message: Mensagem de exceção para sanitizar

        Returns:
            Mensagem de exceção sanitizada
        """
        return cls.mask(message)


class PatientIdHasher:
    """Faz hash de IDs de paciente para logging seguro.

    Usa SHA256 para hashing consistente e não reversível de identificadores
    de pacientes para manter a privacidade enquanto permite correlação.

    Implementa FR-010 da especificação: hashear patient_id em logs.
    """

    # Salt for additional security (prevents rainbow table attacks)
    # In production, this should come from environment variable
    SALT = "health-api-2026"

    @staticmethod
    def hash(patient_id: str | None) -> str | None:
        """Faz hash de um ID de paciente usando SHA256.

        Args:
            patient_id: Identificador de paciente para fazer hash

        Returns:
            Hash SHA256 ou None se a entrada for None
        """
        if patient_id is None:
            return None

        # Use SHA256 for consistent hashing with salt
        hash_input = f"{patient_id}:{PatientIdHasher.SALT}"
        hash_obj = hashlib.sha256(hash_input.encode("utf-8"))
        # Return first 16 chars of hex digest (sufficient for correlation)
        return hash_obj.hexdigest()[:16]

    @classmethod
    def hash_patient_id_field(cls, data: dict[str, Any]) -> dict[str, Any]:
        """Faz hash do campo patient_id em dicionário.

        Args:
            data: Dicionário contendo patient_id

        Returns:
            Dicionário com patient_id hasheado
        """
        result: dict[str, Any] = {}
        for key, value in data.items():
            if key == "patient_id" and isinstance(value, str):
                result[key] = cls.hash(value)
            elif isinstance(value, dict):
                result[key] = cls.hash_patient_id_field(value)
            elif isinstance(value, list):
                result[key] = cls.hash_list_items(value)
            else:
                result[key] = value
        return result

    @classmethod
    def hash_list_items(cls, data: list[Any]) -> list[Any]:
        """Recursivamente faz hash de patient_id em itens de lista.

        Args:
            data: Lista para processar

        Returns:
            Lista com patient_ids hasheados
        """
        result: list[Any] = []
        for item in data:
            if isinstance(item, dict):
                result.append(cls.hash_patient_id_field(item))
            elif isinstance(item, list):
                result.append(cls.hash_list_items(item))
            else:
                result.append(item)
        return result

    @staticmethod
    def get_hash_prefix(patient_id: str | None) -> str | None:
        """Obtém os primeiros 8 caracteres do hash para exibição/correlação.

        Args:
            patient_id: Identificador de paciente para fazer hash

        Returns:
            Primeiros 8 caracteres do hash ou None
        """
        if patient_id is None:
            return None
        full_hash = PatientIdHasher.hash(patient_id)
        return full_hash[:8] if full_hash else None


class LogSanitizer:
    """Utilitário combinado de sanitização de logs.

    Fornece tanto mascaramento de secrets quanto hash de IDs de paciente
    em uma única interface.
    Implementa logging compatível com LGPD para a API de análise de saúde.
    """

    @staticmethod
    def sanitize(data: Any) -> Any:
        """Sanitiza dados para logging seguro.

        Aplica tanto mascaramento de secrets quanto hash de IDs de paciente.

        Args:
            data: Dados para sanitizar

        Returns:
            Dados sanitizados
        """
        if isinstance(data, str):
            return SecretMasker.mask(data)
        elif isinstance(data, dict):
            # Hash patient IDs first, then mask secrets
            hashed = PatientIdHasher.hash_patient_id_field(data)
            return SecretMasker.mask_dict(hashed)
        elif isinstance(data, list):
            hashed_list = PatientIdHasher.hash_list_items(data)
            return SecretMasker.mask_list(hashed_list)
        return data

    @staticmethod
    def sanitize_for_audit(data: dict[str, Any]) -> dict[str, Any]:
        """Sanitiza dados para logging de auditoria.

        Sanitização mais agressiva para logs de auditoria.
        Remove conteúdo de mídia e faz hash de todos os identificadores.

        Args:
            data: Dicionário para sanitizar

        Returns:
            Dicionário seguro para logs de auditoria
        """
        if not isinstance(data, dict):
            return {}

        sanitized: dict[str, Any] = {}
        sensitive_content_keys = {
            "content", "texto", "transcricao", "text", "raw_content",
            "media", "audio_data", "video_data", "frame", "image",
        }

        for key, value in data.items():
            key_lower = key.lower()

            # Skip media content entirely
            if any(sk in key_lower for sk in sensitive_content_keys):
                sanitized[key] = "[REDACTED_MEDIA_CONTENT]"
            elif key == "patient_id" and isinstance(value, str):
                sanitized[key] = PatientIdHasher.hash(value)
            elif isinstance(value, str):
                sanitized[key] = SecretMasker.mask(value)
            elif isinstance(value, dict):
                sanitized[key] = LogSanitizer.sanitize_for_audit(value)
            elif isinstance(value, list):
                sanitized[key] = [
                    LogSanitizer.sanitize_for_audit(item)
                    if isinstance(item, dict)
                    else SecretMasker.mask(item)
                    if isinstance(item, str)
                    else item
                    for item in value
                ]
            else:
                sanitized[key] = value

        return sanitized


# Module-level convenience functions
def sanitize_log_data(data: Any) -> Any:
    """Função de conveniência para sanitizar dados para logging.

    Args:
        data: Dados para sanitizar

    Returns:
        Dados sanitizados
    """
    return LogSanitizer.sanitize(data)


def hash_patient_id(patient_id: str | None) -> str | None:
    """Função de conveniência para fazer hash de um ID de paciente.

    Args:
        patient_id: ID de paciente para fazer hash

    Returns:
        ID de paciente hasheado ou None
    """
    return PatientIdHasher.hash(patient_id)
