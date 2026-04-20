"""Validação de arquivos com magic numbers.

Este módulo valida arquivos de áudio usando magic numbers (conteúdo real),
além da extensão, para prevenir spoofing de tipo de arquivo.
"""

from pathlib import Path
from typing import TYPE_CHECKING, Optional

if TYPE_CHECKING:
    from structlog.stdlib import BoundLogger

from fastapi import HTTPException, UploadFile

# ===========================================
# Constantes (devem ser definidas antes de usadas)
# ===========================================

# Tamanho máximo: 50MB
MAX_FILE_SIZE = 50 * 1024 * 1024  # 50MB em bytes

# Tipos MIME permitidos e suas extensões correspondentes
ALLOWED_AUDIO_TYPES = {
    "audio/wav": ".wav",
    "audio/x-wav": ".wav",
    "audio/mpeg": ".mp3",
    "audio/ogg": ".ogg",
}

ALLOWED_VIDEO_TYPES = {
    "video/mp4": ".mp4",
    "video/x-msvideo": ".avi",
    "video/quicktime": ".mov",
}

# Extensões permitidas (para validação inicial)
ALLOWED_EXTENSIONS = {".wav", ".mp3", ".ogg"}
ALLOWED_VIDEO_EXTENSIONS = {".mp4", ".avi", ".mov"}

# Limite de duração de vídeo: 2 minutos (120 segundos)
MAX_VIDEO_DURATION_SECONDS = 120

# python-magic pode não estar disponível no Windows
MAGIC_AVAILABLE = False
magic = None
try:
    import magic as _magic_module
    magic = _magic_module
    MAGIC_AVAILABLE = True
except (ImportError, OSError):
    pass

# Logger lazy
_logger: Optional["BoundLogger"] = None


def _get_logger() -> "BoundLogger":
    """Lazy initialization do logger."""
    global _logger
    if _logger is None:
        from structlog import get_logger
        _logger = get_logger()
        if not MAGIC_AVAILABLE:
            _logger.warning("python-magic não disponível, usando validação por extensão apenas")
    return _logger


async def check_upload_size(file: UploadFile, max_size: int = MAX_FILE_SIZE) -> None:
    """Verifica tamanho do upload antes de salvar em disco.

    Args:
        file: UploadFile do FastAPI
        max_size: Tamanho máximo em bytes (padrão: 50MB)

    Raises:
        HTTPException: 400 se arquivo muito grande
    """
    logger = _get_logger()

    # Verifica file.size (disponível em UploadFile se setado pelo client)
    if file.size and file.size > max_size:
        logger.warning(
            "audio_validation_failed",
            reason="file_too_large",
            size_bytes=file.size,
            max_size=max_size,
        )
        raise HTTPException(
            status_code=400,
            detail=f"Arquivo muito grande ({file.size / (1024*1024):.1f}MB). Máximo: {max_size / (1024*1024):.0f}MB",
        )

    # Fallback: ler conteúdo parcial para estimar tamanho se file.size não disponível
    # Nota: Isso não é 100% preciso mas evita salvar arquivos muito grandes
    if not file.size:
        # Lê uma amostra para verificar se arquivo tem conteúdo
        sample = await file.read(1)
        await file.seek(0)
        if len(sample) == 0:
            raise HTTPException(status_code=400, detail="Arquivo vazio")


async def validate_audio_file(file: UploadFile) -> None:
    """Valida arquivo de áudio.

    Realiza três validações:
    1. Extensão do arquivo
    2. Magic numbers (tipo MIME real) ou assinatura
    3. Tamanho do arquivo

    Args:
        file: UploadFile do FastAPI

    Raises:
        HTTPException: 400 se arquivo inválido
    """
    logger = _get_logger()

    # 1. Validar extensão
    ext = Path(file.filename or "").suffix.lower()
    if ext not in ALLOWED_EXTENSIONS:
        logger.warning(
            "audio_validation_failed",
            reason="invalid_extension",
            extension=ext,
            filename=file.filename,
        )
        raise HTTPException(
            status_code=400,
            detail=f"Extensão não permitida: {ext}. Use: {', '.join(ALLOWED_EXTENSIONS)}",
        )

    # 2. Verificar magic numbers (conteúdo real) - se disponível
    if MAGIC_AVAILABLE and magic is not None:
        content = await file.read(8192)  # Primeiros 8KB (suficiente para magic)
        await file.seek(0)  # Reset para leitura posterior

        mime = magic.from_buffer(content, mime=True)
        if mime not in ALLOWED_AUDIO_TYPES:
            logger.warning(
                "audio_validation_failed",
                reason="invalid_mime_type",
                mime_type=mime,
                filename=file.filename,
            )
            raise HTTPException(
                status_code=400,
                detail=f"Tipo de arquivo não suportado: {mime}. Use: WAV, MP3 ou OGG",
            )

        # Verificar se extensão corresponde ao MIME
        expected_ext = ALLOWED_AUDIO_TYPES[mime]
        if ext != expected_ext:
            logger.warning(
                "audio_validation_warning",
                reason="extension_mime_mismatch",
                extension=ext,
                mime_type=mime,
                expected_extension=expected_ext,
            )

        logger.debug(
            "audio_validation_passed",
            filename=file.filename,
            mime_type=mime,
            extension=ext,
        )
    else:
        # Fallback: validação básica por assinatura de arquivo
        content = await file.read(8)
        await file.seek(0)

        # Verificar assinaturas básicas
        is_valid = False
        if ext == ".wav" and content.startswith(b"RIFF") or ext == ".mp3" and (content.startswith(b"\xff\xfb") or content.startswith(b"ID3")) or ext == ".ogg" and content.startswith(b"OggS"):
            is_valid = True

        if not is_valid and len(content) > 0:
            logger.warning(
                "audio_validation_failed",
                reason="invalid_signature",
                extension=ext,
                filename=file.filename,
            )
            raise HTTPException(
                status_code=400,
                detail=f"Arquivo {ext} tem assinatura inválida",
            )

        logger.debug(
            "audio_validation_passed_fallback",
            filename=file.filename,
            extension=ext,
        )


def check_file_size(file_path: Path) -> None:
    """Verifica tamanho do arquivo salvo.

    Deve ser chamado após salvar o arquivo temporário.

    Args:
        file_path: Caminho do arquivo salvo

    Raises:
        HTTPException: 400 se arquivo muito grande
    """
    logger = _get_logger()
    size = file_path.stat().st_size
    if size > MAX_FILE_SIZE:
        logger.warning(
            "audio_validation_failed",
            reason="file_too_large",
            size_bytes=size,
            max_size=MAX_FILE_SIZE,
        )
        raise HTTPException(
            status_code=400,
            detail=f"Arquivo muito grande ({size / (1024*1024):.1f}MB). Máximo: 50MB",
        )

    logger.debug("audio_size_validated", size_bytes=size)


async def validate_video_file(file: UploadFile) -> None:
    """Valida arquivo de vídeo.

    Realiza três validações:
    1. Extensão do arquivo
    2. Magic numbers (tipo MIME real) ou assinatura
    3. Tamanho do arquivo

    Args:
        file: UploadFile do FastAPI

    Raises:
        HTTPException: 400 se arquivo inválido
    """
    logger = _get_logger()

    # 1. Validar extensão
    ext = Path(file.filename or "").suffix.lower()
    if ext not in ALLOWED_VIDEO_EXTENSIONS:
        logger.warning(
            "video_validation_failed",
            reason="invalid_extension",
            extension=ext,
            filename=file.filename,
        )
        raise HTTPException(
            status_code=400,
            detail=f"Formato de vídeo não suportado: {ext}. Use: MP4, AVI ou MOV",
        )

    # 2. Verificar magic numbers (conteúdo real) - se disponível
    if MAGIC_AVAILABLE and magic is not None:
        content = await file.read(8192)  # Primeiros 8KB (suficiente para magic)
        await file.seek(0)  # Reset para leitura posterior

        mime = magic.from_buffer(content, mime=True)
        if mime not in ALLOWED_VIDEO_TYPES:
            logger.warning(
                "video_validation_failed",
                reason="invalid_mime_type",
                mime_type=mime,
                filename=file.filename,
            )
            raise HTTPException(
                status_code=400,
                detail=f"Tipo de vídeo não suportado: {mime}. Use: MP4, AVI ou MOV",
            )

        logger.debug(
            "video_validation_passed",
            filename=file.filename,
            mime_type=mime,
            extension=ext,
        )
    else:
        # Fallback: validação básica por assinatura de arquivo
        content = await file.read(8)
        await file.seek(0)

        # Verificar assinaturas básicas de vídeo
        is_valid = False
        if ext == ".mp4" and content[4:8] == b"ftyp" or ext == ".avi" and content.startswith(b"RIFF") or ext == ".mov" and content[4:8] == b"ftyp":
            is_valid = True

        if not is_valid and len(content) > 0:
            logger.warning(
                "video_validation_failed",
                reason="invalid_signature",
                extension=ext,
                filename=file.filename,
            )
            raise HTTPException(
                status_code=400,
                detail=f"Arquivo {ext} tem assinatura inválida",
            )

        logger.debug(
            "video_validation_passed_fallback",
            filename=file.filename,
            extension=ext,
        )


def check_video_duration(file_path: Path) -> float:
    """Verifica duração do vídeo usando OpenCV.

    Args:
        file_path: Caminho do arquivo de vídeo

    Returns:
        Duração do vídeo em segundos

    Raises:
        HTTPException: 400 se duração exceder o limite ou arquivo inválido
    """
    logger = _get_logger()

    try:
        import cv2

        cap = cv2.VideoCapture(str(file_path))
        if not cap.isOpened():
            raise HTTPException(
                status_code=400,
                detail="Não foi possível abrir o vídeo. Verifique se o formato é suportado.",
            )

        fps = cap.get(cv2.CAP_PROP_FPS)
        frame_count = int(cap.get(cv2.CAP_PROP_FRAME_COUNT))
        duration = frame_count / fps if fps > 0 else 0

        cap.release()

        if duration > MAX_VIDEO_DURATION_SECONDS:
            logger.warning(
                "video_validation_failed",
                reason="duration_exceeded",
                duration_seconds=duration,
                max_duration=MAX_VIDEO_DURATION_SECONDS,
            )
            raise HTTPException(
                status_code=400,
                detail=f"Vídeo excede o limite de {MAX_VIDEO_DURATION_SECONDS // 60} minutos.",
            )

        logger.debug("video_duration_validated", duration_seconds=duration)
        return duration

    except ImportError:
        logger.error("opencv_not_available")
        raise HTTPException(
            status_code=500,
            detail="OpenCV não disponível para validação de vídeo",
        ) from None
    except HTTPException:
        raise
    except Exception as e:
        logger.error("video_duration_check_failed", error=str(e))
        raise HTTPException(
            status_code=400,
            detail=f"Erro ao verificar duração do vídeo: {str(e)}",
        ) from e
