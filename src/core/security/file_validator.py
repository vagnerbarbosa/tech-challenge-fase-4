"""Componentes de segurança para validação de arquivos.

Fornece validação de arquivos focada em segurança, incluindo verificação de magic bytes
e sanitização de nomes de arquivo para prevenir uploads maliciosos e ataques de path traversal.
"""

from __future__ import annotations

import re
from dataclasses import dataclass
from pathlib import Path
from typing import TYPE_CHECKING

from fastapi import HTTPException, UploadFile

if TYPE_CHECKING:
    from structlog.stdlib import BoundLogger

# ===========================================
# Constants
# ===========================================

# Maximum file size: 50MB
MAX_FILE_SIZE_BYTES = 50 * 1024 * 1024  # 50MB in bytes

# Allowed audio MIME types and their corresponding extensions
ALLOWED_AUDIO_MIME_TYPES = {
    "audio/wav": ".wav",
    "audio/x-wav": ".wav",
    "audio/mpeg": ".mp3",
    "audio/ogg": ".ogg",
    "audio/vorbis": ".ogg",
}

# Allowed video MIME types and their corresponding extensions
ALLOWED_VIDEO_MIME_TYPES = {
    "video/mp4": ".mp4",
    "video/x-msvideo": ".avi",
    "video/quicktime": ".mov",
    "video/x-matroska": ".mkv",
}

# Combined allowed MIME types for general validation
ALLOWED_MIME_TYPES = {**ALLOWED_AUDIO_MIME_TYPES, **ALLOWED_VIDEO_MIME_TYPES}

# File extensions whitelist
ALLOWED_EXTENSIONS = frozenset(ALLOWED_MIME_TYPES.values())

# Magic number signatures for common file types (first bytes)
MAGIC_SIGNATURES: dict[str, list[bytes]] = {
    # Audio formats
    ".wav": [b"RIFF"],  # WAV starts with RIFF....WAVE
    ".mp3": [b"\xff\xfb", b"\xff\xf3", b"\xff\xf2", b"ID3"],  # MP3 with or without ID3
    ".ogg": [b"OggS"],  # Ogg Vorbis
    # Video formats
    ".mp4": [b"\x00\x00\x00\x20ftyp", b"\x00\x00\x00\x18ftyp", b"\x00\x00\x00 ftyp"],
    ".avi": [b"RIFF"],  # AVI starts with RIFF....AVI
    ".mov": [b"\x00\x00\x00\x20ftyp", b"\x00\x00\x00\x18ftyp"],  # QuickTime
}

# Dangerous extensions that should never be accepted
DANGEROUS_EXTENSIONS = frozenset({
    ".exe", ".dll", ".bat", ".cmd", ".sh", ".py", ".php",
    ".jsp", ".asp", ".aspx", ".rb", ".pl", ".cgi", ".jar",
    ".war", ".ear", ".ps1", ".vbs", ".js", ".html", ".htm",
    ".svg", ".xml", ".pdf", ".doc", ".docx", ".xls", ".xlsx",
})

# Path traversal patterns
PATH_TRAVERSAL_PATTERNS = [
    re.compile(r"\.\.[\/\\]"),  # ../ or ..\
    re.compile(r"^[\/\\]"),  # Leading slash (absolute path)
    re.compile(r"^~"),  # Home directory
    re.compile(r"[\x00-\x1f]"),  # Control characters
    re.compile(r"\.", re.IGNORECASE),  # Double dots anywhere
]

# Logger placeholder
_logger: BoundLogger | None = None


def _get_logger() -> BoundLogger:
    """Inicialização preguiçosa do logger."""
    global _logger
    if _logger is None:
        from structlog import get_logger
        _logger = get_logger("security.file_validator")
    return _logger


# ===========================================
# Exceptions
# ===========================================

class FileValidationError(HTTPException):
    """Exceção lançada para erros de validação de arquivo."""

    def __init__(self, detail: str, error_code: str = "file_validation_failed"):
        self.error_code = error_code
        super().__init__(status_code=400, detail=detail)


class FileSizeError(HTTPException):
    """Exceção lançada quando o tamanho do arquivo excede o limite."""

    def __init__(self, size: int, max_size: int):
        self.size = size
        self.max_size = max_size
        super().__init__(
            status_code=400,
            detail=f"Arquivo muito grande ({size / (1024*1024):.1f}MB). "
                   f"Máximo: {max_size / (1024*1024):.0f}MB",
        )


class PathTraversalError(HTTPException):
    """Exceção lançada quando path traversal é detectado."""

    def __init__(self, filename: str):
        super().__init__(
            status_code=400,
            detail="Nome de arquivo contém caracteres inválidos",
        )


# ===========================================
# MagicBytesValidator
# ===========================================

@dataclass(frozen=True)
class ValidationResult:
    """Resultado da validação de arquivo."""

    is_valid: bool
    mime_type: str | None = None
    extension: str | None = None
    error_message: str | None = None
    error_code: str | None = None


class MagicBytesValidator:
    """Valida conteúdo de arquivos usando magic bytes (detecção de MIME type).

    Usa python-magic quando disponível, fazendo fallback para validação
    baseada em assinaturas em ambientes onde libmagic não está instalado.
    """

    def __init__(self) -> None:
        """Inicializa o validador com a biblioteca magic se disponível."""
        self._magic = None
        self._magic_available = False

        try:
            import magic as magic_module
            self._magic = magic_module
            self._magic_available = True
        except (ImportError, OSError):
            _get_logger().warning(
                "python_magic_not_available",
                message="Usando validação por assinatura como fallback",
            )

    def validate_content(
        self,
        content: bytes,
        expected_extension: str | None = None,
        allowed_types: dict[str, str] | None = None,
    ) -> ValidationResult:
        """Valida conteúdo de arquivo usando magic bytes.

        Args:
            content: Primeiros bytes do arquivo para validar
            expected_extension: Extensão esperada do arquivo (para verificação de incompatibilidade)
            allowed_types: Dict de MIME types permitidos para extensões

        Returns:
            ValidationResult com status da validação e detalhes
        """
        if allowed_types is None:
            allowed_types = ALLOWED_MIME_TYPES

        if not content:
            return ValidationResult(
                is_valid=False,
                error_message="Arquivo vazio",
                error_code="empty_file",
            )

        # Use python-magic if available
        if self._magic_available and self._magic is not None:
            return self._validate_with_magic(content, expected_extension, allowed_types)

        # Fallback to signature-based validation
        return self._validate_with_signatures(content, expected_extension)

    def _validate_with_magic(
        self,
        content: bytes,
        expected_extension: str | None,
        allowed_types: dict[str, str],
    ) -> ValidationResult:
        """Valida usando a biblioteca python-magic."""
        assert self._magic is not None, "_magic should not be None when _magic_available is True"
        try:
            mime_type = self._magic.from_buffer(content, mime=True)
        except Exception as e:
            _get_logger().error(
                "magic_detection_failed",
                error=str(e),
            )
            return ValidationResult(
                is_valid=False,
                error_message="Falha ao detectar tipo de arquivo",
                error_code="magic_detection_failed",
            )

        # Check if MIME type is allowed
        if mime_type not in allowed_types:
            return ValidationResult(
                is_valid=False,
                mime_type=mime_type,
                error_message=f"Tipo de arquivo não suportado: {mime_type}",
                error_code="unsupported_mime_type",
            )

        # Check extension matches MIME type
        expected_ext = allowed_types[mime_type]
        if expected_extension and expected_extension.lower() != expected_ext:
            _get_logger().warning(
                "extension_mime_mismatch",
                mime_type=mime_type,
                expected_extension=expected_ext,
                actual_extension=expected_extension,
            )
            return ValidationResult(
                is_valid=False,
                mime_type=mime_type,
                extension=expected_extension,
                error_message=f"Extensão {expected_extension} não corresponde ao tipo {mime_type}",
                error_code="extension_mime_mismatch",
            )

        return ValidationResult(
            is_valid=True,
            mime_type=mime_type,
            extension=expected_extension or expected_ext,
        )

    def _validate_with_signatures(
        self,
        content: bytes,
        expected_extension: str | None,
    ) -> ValidationResult:
        """Valida usando assinaturas de arquivo conhecidas (fallback)."""
        if not expected_extension:
            return ValidationResult(
                is_valid=True,
                error_message="Não foi possível validar sem extensão (magic não disponível)",
                error_code="validation_degraded",
            )

        ext = expected_extension.lower()
        signatures = MAGIC_SIGNATURES.get(ext, [])

        if not signatures:
            return ValidationResult(
                is_valid=False,
                extension=expected_extension,
                error_message=f"Extensão não reconhecida: {ext}",
                error_code="unknown_extension",
            )

        # Check if content starts with any valid signature
        is_valid = any(
            len(content) >= len(sig) and content[:len(sig)] == sig
            for sig in signatures
        )

        if not is_valid:
            return ValidationResult(
                is_valid=False,
                extension=expected_extension,
                error_message=f"Assinatura de arquivo inválida para {ext}",
                error_code="invalid_signature",
            )

        return ValidationResult(
            is_valid=True,
            extension=expected_extension,
        )


# ===========================================
# FilenameSanitizer
# ===========================================

@dataclass(frozen=True)
class SanitizationResult:
    """Resultado da sanitização de nome de arquivo."""

    is_safe: bool
    sanitized_name: str | None = None
    original_name: str | None = None
    error_message: str | None = None


class FilenameSanitizer:
    """Sanitiza nomes de arquivos para prevenir ataques de path traversal.

    Valida e sanitiza nomes de arquivos fornecidos por usuários para garantir:
    - Sem sequências de path traversal (../)
    - Sem caminhos absolutos
    - Sem caracteres de controle
    - Sem extensões perigosas
    """

    # Characters not allowed in filenames
    INVALID_CHARS = re.compile(r'[<>:"|?*\x00-\x1f]')

    # Reserved Windows names
    RESERVED_NAMES = frozenset({
        "con", "prn", "aux", "nul",
        "com1", "com2", "com3", "com4", "com5", "com6", "com7", "com8", "com9",
        "lpt1", "lpt2", "lpt3", "lpt4", "lpt5", "lpt6", "lpt7", "lpt8", "lpt9",
    })

    def sanitize(self, filename: str | None) -> SanitizationResult:
        """Sanitiza um nome de arquivo e verifica path traversal.

        Args:
            filename: Nome de arquivo original da entrada do usuário

        Returns:
            SanitizationResult com status de segurança e nome sanitizado
        """
        if not filename:
            return SanitizationResult(
                is_safe=False,
                original_name=filename,
                error_message="Nome de arquivo vazio",
            )

        original = filename

        # Check for null bytes
        if "\x00" in filename:
            _get_logger().warning(
                "null_byte_in_filename",
                original_name=original,
            )
            return SanitizationResult(
                is_safe=False,
                original_name=original,
                error_message="Nome de arquivo contém caracteres nulos",
            )

        # Normalize path separators
        filename = filename.replace("\\", "/")

        # Extract basename (remove any path components)
        basename = Path(filename).name

        # Check for path traversal in original
        if self._contains_path_traversal(filename):
            _get_logger().warning(
                "path_traversal_detected",
                original_name=original,
                basename=basename,
            )
            # Continue with sanitization but mark as having had traversal

        # Check for dangerous extension
        ext = Path(basename).suffix.lower()
        if ext in DANGEROUS_EXTENSIONS:
            _get_logger().warning(
                "dangerous_extension_blocked",
                original_name=original,
                extension=ext,
            )
            return SanitizationResult(
                is_safe=False,
                original_name=original,
                error_message=f"Extensão de arquivo não permitida: {ext}",
            )

        # Remove invalid characters
        sanitized = self.INVALID_CHARS.sub("_", basename)

        # Check for reserved Windows names
        name_without_ext = Path(sanitized).stem.lower()
        if name_without_ext in self.RESERVED_NAMES:
            sanitized = f"_{sanitized}"

        # Ensure filename is not empty after sanitization
        if not sanitized or sanitized == "." or sanitized.startswith("."):
            sanitized = f"upload_{sanitized}"

        # Limit length
        if len(sanitized) > 255:
            stem = Path(sanitized).stem[:240]
            suffix = Path(sanitized).suffix
            sanitized = f"{stem}{suffix}"

        is_safe = sanitized == basename and not self._contains_path_traversal(filename)

        return SanitizationResult(
            is_safe=is_safe,
            sanitized_name=sanitized,
            original_name=original,
        )

    def _contains_path_traversal(self, filename: str) -> bool:
        """Verifica se o nome de arquivo contém sequências de path traversal.

        Args:
            filename: Nome de arquivo para verificar

        Returns:
            True se path traversal foi detectado
        """
        # Check for parent directory references
        if ".." in filename:
            return True

        # Check for absolute paths
        if filename.startswith("/") or filename.startswith("\\"):
            return True

        # Check for home directory expansion
        if filename.startswith("~"):
            return True

        # Check for URL-encoded traversal
        decoded = filename.replace("%2e%2e%2f", "../").replace("%2e%2e/", "../")
        return ".." in decoded

    def validate_extension(self, filename: str, allowed_extensions: set[str] | frozenset[str] | None = None) -> bool:
        """Valida extensão de arquivo contra lista permitida.

        Args:
            filename: Nome de arquivo para validar
            allowed_extensions: Conjunto de extensões permitidas (padrão: ALLOWED_EXTENSIONS)

        Returns:
            True se a extensão é permitida
        """
        if allowed_extensions is None:
            allowed_extensions = ALLOWED_EXTENSIONS

        ext = Path(filename).suffix.lower()
        return ext in allowed_extensions


# ===========================================
# FastAPI Dependency
# ===========================================

async def validate_upload_file(
    file: UploadFile,
    max_size: int = MAX_FILE_SIZE_BYTES,
    allowed_extensions: set[str] | frozenset[str] | None = None,
) -> UploadFile:
    """FastAPI dependency para validar arquivos enviados.

    Realiza validação abrangente incluindo:
    - Sanitização de nome de arquivo (prevenção de path traversal)
    - Validação de extensão
    - Validação de magic bytes (verificação de MIME type)
    - Validação de tamanho

    Args:
        file: FastAPI UploadFile para validar
        max_size: Tamanho máximo do arquivo em bytes
        allowed_extensions: Conjunto de extensões de arquivo permitidas

    Returns:
        O UploadFile validado (posição resetada para o início)

    Raises:
        FileValidationError: Se a validação do arquivo falhar
        FileSizeError: Se o arquivo exceder o tamanho máximo
        PathTraversalError: Se path traversal for detectado
    """
    logger = _get_logger()

    # Initialize validators
    filename_sanitizer = FilenameSanitizer()
    magic_validator = MagicBytesValidator()

    # Validate filename (path traversal check)
    if file.filename:
        sanitization = filename_sanitizer.sanitize(file.filename)
        if not sanitization.is_safe:
            logger.warning(
                "filename_validation_failed",
                original_name=file.filename,
                reason=sanitization.error_message,
            )
            if "path" in (sanitization.error_message or "").lower():
                raise PathTraversalError(file.filename)
            raise FileValidationError(
                detail=sanitization.error_message or "Nome de arquivo inválido",
                error_code="invalid_filename",
            )

        # Check extension
        if allowed_extensions is None:
            allowed_extensions = ALLOWED_EXTENSIONS

        ext = Path(file.filename).suffix.lower()
        if ext not in allowed_extensions:
            logger.warning(
                "extension_not_allowed",
                filename=file.filename,
                extension=ext,
                allowed=list(allowed_extensions),
            )
            raise FileValidationError(
                detail=f"Extensão não permitida: {ext}. Use: {', '.join(allowed_extensions)}",
                error_code="invalid_extension",
            )
    else:
        raise FileValidationError(
            detail="Nome de arquivo não fornecido",
            error_code="missing_filename",
        )

    # Validate file content with magic bytes
    content = await file.read(8192)  # Read first 8KB
    await file.seek(0)  # Reset position

    validation_result = magic_validator.validate_content(
        content=content,
        expected_extension=Path(file.filename).suffix.lower() if file.filename else None,
    )

    if not validation_result.is_valid:
        logger.warning(
            "magic_validation_failed",
            filename=file.filename,
            reason=validation_result.error_message,
            error_code=validation_result.error_code,
        )
        raise FileValidationError(
            detail=validation_result.error_message or "Arquivo inválido",
            error_code=validation_result.error_code or "validation_failed",
        )

    # Validate file size (streaming check)
    if file.size is not None and file.size > max_size:
        logger.warning(
            "file_size_exceeded",
            filename=file.filename,
            size=file.size,
            max_size=max_size,
        )
        raise FileSizeError(file.size, max_size)

    # If size is not available from client, read content to check
    if file.size is None:
        total_size = len(content)
        # Read remaining content in chunks
        while True:
            chunk = await file.read(8192)
            if not chunk:
                break
            total_size += len(chunk)
            if total_size > max_size:
                await file.seek(0)
                raise FileSizeError(total_size, max_size)

        await file.seek(0)  # Reset position for subsequent handlers

    logger.debug(
        "file_validation_passed",
        filename=file.filename,
        mime_type=validation_result.mime_type,
    )

    return file
