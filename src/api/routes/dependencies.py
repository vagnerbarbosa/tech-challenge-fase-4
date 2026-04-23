"""Dependências FastAPI para injeção de recursos.

Gerencia singletons como TempFileManager para uso em rotas.
"""

from __future__ import annotations

from typing import Annotated

from fastapi import Depends, HTTPException, Header, Request, UploadFile, status

from src.core.security.auth import (
    get_api_key_validator,
    get_bola_protector,
    get_rbac_validator,
)
from src.core.security.file_validator import (
    ALLOWED_EXTENSIONS,
    MAX_FILE_SIZE_BYTES,
    validate_upload_file as _validate_upload_file,
)
from src.core.security.models import SecurityContext
from src.core.temp_file_manager import TempFileManager

# Singleton para TempFileManager
_temp_manager: TempFileManager | None = None


def get_temp_manager() -> TempFileManager:
    """Retorna instância singleton do TempFileManager.

    Returns:
        TempFileManager singleton
    """
    global _temp_manager
    if _temp_manager is None:
        _temp_manager = TempFileManager()
    return _temp_manager


async def validate_upload_file(
    file: UploadFile,
    max_size: int = MAX_FILE_SIZE_BYTES,
    allowed_extensions: set[str] | frozenset[str] | None = None,
) -> UploadFile:
    """Valida arquivo enviado via upload.

    Realiza validações de segurança:
    - Sanitização de nome (path traversal)
    - Extensão permitida
    - Magic bytes (conteúdo real do arquivo)
    - Tamanho máximo

    Args:
        file: Arquivo FastAPI UploadFile
        max_size: Tamanho máximo em bytes (padrão: 50MB)
        allowed_extensions: Conjunto de extensões permitidas

    Returns:
        UploadFile validado (posição resetada)

    Raises:
        HTTPException: 400 para arquivo inválido, 413 para tamanho excedido
    """
    if allowed_extensions is None:
        allowed_extensions = ALLOWED_EXTENSIONS

    return await _validate_upload_file(
        file=file,
        max_size=max_size,
        allowed_extensions=allowed_extensions,
    )


async def validate_audio_upload(
    file: UploadFile,
    max_size: int = MAX_FILE_SIZE_BYTES,
) -> UploadFile:
    """Valida upload de arquivo de áudio.

    Args:
        file: Arquivo FastAPI UploadFile
        max_size: Tamanho máximo em bytes

    Returns:
        UploadFile validado
    """
    from src.core.security.file_validator import ALLOWED_AUDIO_MIME_TYPES

    audio_extensions = set(ALLOWED_AUDIO_MIME_TYPES.values())
    return await validate_upload_file(
        file=file,
        max_size=max_size,
        allowed_extensions=audio_extensions,
    )


async def validate_video_upload(
    file: UploadFile,
    max_size: int = MAX_FILE_SIZE_BYTES,
) -> UploadFile:
    """Valida upload de arquivo de vídeo.

    Args:
        file: Arquivo FastAPI UploadFile
        max_size: Tamanho máximo em bytes

    Returns:
        UploadFile validado
    """
    from src.core.security.file_validator import ALLOWED_VIDEO_MIME_TYPES

    video_extensions = set(ALLOWED_VIDEO_MIME_TYPES.values())
    return await validate_upload_file(
        file=file,
        max_size=max_size,
        allowed_extensions=video_extensions,
    )


# =============================================================================
# Authentication Dependencies (T016)
# =============================================================================

async def require_api_key(
    request: Request,
    x_api_key: Annotated[str | None, Header()] = None,
) -> SecurityContext:
    """Dependency to require valid API key for endpoint access.

    Validates the API key from X-API-Key header and returns
    a security context with authentication information.

    Args:
        request: FastAPI request object
        x_api_key: API key from X-API-Key header

    Returns:
        SecurityContext with authentication details

    Raises:
        HTTPException: 401 if API key is missing or invalid
    """
    # Get client IP address
    ip_address = request.client.host if request.client else None

    # Generate or get request ID
    request_id = getattr(request.state, "request_id", None)
    if request_id is None:
        import uuid
        request_id = str(uuid.uuid4())

    validator = get_api_key_validator()

    try:
        ctx = validator.get_security_context(
            api_key=x_api_key,
            request_id=request_id,
            ip_address=ip_address,
        )
        # Store context in request state for later use
        request.state.security_context = ctx
        return ctx
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="API key inválida ou ausente",
            headers={"WWW-Authenticate": "ApiKey"},
        ) from e


async def require_api_key_optional(
    request: Request,
    x_api_key: Annotated[str | None, Header()] = None,
) -> SecurityContext | None:
    """Dependency for optional API key authentication.

    Similar to require_api_key but returns None instead of raising
    exception when key is missing/invalid.

    Args:
        request: FastAPI request object
        x_api_key: API key from X-API-Key header

    Returns:
        SecurityContext if valid key provided, None otherwise
    """
    try:
        return await require_api_key(request, x_api_key)
    except HTTPException:
        return None


async def require_role(
    role: str,
    ctx: SecurityContext = Depends(require_api_key),
) -> SecurityContext:
    """Dependency factory to require specific role.

    Usage:
        @router.get("/admin")
        async def admin_endpoint(ctx: SecurityContext = Depends(require_role("admin"))):
            pass

    Args:
        role: Required role
        ctx: Security context from require_api_key

    Returns:
        SecurityContext if role present

    Raises:
        HTTPException: 403 if role missing
    """
    rbac = get_rbac_validator()
    if not rbac.has_role(ctx, role):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail=f"Role '{role}' necessária",
        )
    return ctx


class RoleRequired:
    """Dependency class for requiring specific roles.

    Usage:
        @router.get("/admin")
        async def admin_endpoint(
            ctx: SecurityContext = Depends(RoleRequired("admin"))
        ):
            pass

        @router.get("/write")
        async def write_endpoint(
            ctx: SecurityContext = Depends(RoleRequired(["write", "admin"]))
        ):
            pass
    """

    def __init__(self, roles: str | list[str]) -> None:
        """Initialize with required role(s).

        Args:
            roles: Single role or list of roles (any will grant access)
        """
        if isinstance(roles, str):
            self.roles = [roles]
        else:
            self.roles = roles

    def __call__(
        self,
        ctx: SecurityContext = Depends(require_api_key),
    ) -> SecurityContext:
        """Check if user has required role.

        Args:
            ctx: Security context

        Returns:
            SecurityContext if authorized

        Raises:
            HTTPException: 403 if unauthorized
        """
        rbac = get_rbac_validator()
        if not rbac.has_any_role(ctx, self.roles):
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=f"Uma das roles {self.roles} é necessária",
            )
        return ctx


def verify_resource_ownership(
    resource_owner_id: str | None,
    ctx: SecurityContext,
    resource_id: str | None = None,
) -> None:
    """Verify user owns resource before allowing access.

    Standalone function for ownership verification.

    Args:
        resource_owner_id: Hash of resource owner's API key
        ctx: Current user's security context
        resource_id: Optional resource identifier for error messages

    Raises:
        HTTPException: 403 if ownership verification fails
    """
    protector = get_bola_protector()
    try:
        protector.verify_ownership(ctx, resource_owner_id, resource_id)
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Acesso negado: você não tem permissão para este recurso",
        ) from e
