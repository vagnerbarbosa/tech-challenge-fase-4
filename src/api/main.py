"""Ponto de entrada da aplicação FastAPI.

Configura a aplicação FastAPI com todos os middlewares, rotas
e handlers de exceção.
"""

import uuid
from contextlib import asynccontextmanager
from typing import Any

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware

from src.api.middleware.rate_limit import (
    AuthRateLimitMiddleware,
    RateLimitMiddleware,
)
from src.api.routes import admin, audio, auth, health, multimodal, text, video
from src.core.config import settings
from src.core.exceptions import (
    AppException,
    AuthenticationException,
    RateLimitExceeded,
    SecurityException,
)
from src.core.logging_config import configure_logging, get_logger
from src.core.security.log_sanitizer import SecretMasker
from src.core.security.middleware import (
    CORSValidation,
    SecurityHeadersConfig,
    SecurityHeadersMiddleware,
    create_cors_middleware,
)

# Configura logging
configure_logging()
logger = get_logger(__name__)


def get_cors_origins() -> list[str]:
    """Obtém lista de origens CORS permitidas baseado no ambiente.

    Em desenvolvimento, permite todas as origens se não configurado.
    Em produção, requer configuração explícita de origens.

    Returns:
        Lista de origens permitidas
    """
    security_config = settings.security_config
    cors_origins = security_config.cors_origins_list

    # Warning se CORS * em não-local
    if "*" in cors_origins and settings.environment != "development":
        logger.warning(
            "CORS configurado com '*' em ambiente nao-local",
            environment=settings.environment,
            cors_origins=cors_origins,
        )

    # Em produção, valida que não está usando * com credentials
    if security_config.is_production and "*" in cors_origins:
        logger.error(
            "Configuracao CORS insegura em producao: '*' nao permitido com credentials",
            cors_origins=cors_origins,
        )
        # Remove * em produção por segurança
        cors_origins = ["https://localhost:3000"]  # Fallback seguro

    return cors_origins


def configure_cors(app: FastAPI) -> None:
    """Configura CORS na aplicação FastAPI.

    Adiciona middleware CORSMiddleware com validações de segurança
    e CORSValidation para logging e validações extras.

    Args:
        app: Instância FastAPI
    """
    cors_origins = get_cors_origins()

    # Configura CORSMiddleware do FastAPI
    cors_config = create_cors_middleware(
        allowed_origins=cors_origins,
        allow_credentials=True,
        allow_methods=["GET", "POST", "PUT", "DELETE", "OPTIONS", "PATCH"],
        allow_headers=[
            "*",
            "Content-Type",
            "Authorization",
            "X-API-Key",
            "X-Request-ID",
        ],
        environment=settings.environment,
    )

    app.add_middleware(
        CORSMiddleware,
        allow_origins=cors_config["allow_origins"],
        allow_credentials=cors_config["allow_credentials"],
        allow_methods=cors_config["allow_methods"],
        allow_headers=cors_config["allow_headers"],
    )

    # Adiciona middleware customizado para validação e logging
    app.add_middleware(
        CORSValidation,
        allowed_origins=cors_origins,
        environment=settings.environment,
    )

    logger.info(
        "CORS configurado",
        allowed_origins=cors_origins,
        environment=settings.environment,
        origin_count=len(cors_origins),
    )


@asynccontextmanager
async def lifespan(app: FastAPI) -> Any:
    """Gerenciador de contexto do lifespan da aplicação.

    Gerencia eventos de startup e shutdown.
    """
    # Startup
    logger.info(
        "Iniciando aplicação",
        app_name=settings.app_name,
        version=settings.app_version,
        environment=settings.environment,
    )
    yield
    # Shutdown
    logger.info("Encerrando aplicação")


# Cria aplicação FastAPI
app = FastAPI(
    title=settings.app_name,
    version=settings.app_version,
    description="API multimodal para análise de saúde da mulher usando Azure AI Services",
    docs_url="/docs" if settings.debug else None,
    redoc_url="/redoc" if settings.debug else None,
    openapi_url="/openapi.json" if settings.debug else None,
    lifespan=lifespan,
)

# Configura CORS
configure_cors(app)


# Configura Security Headers (T056)
# SecurityHeadersMiddleware deve ser adicionado antes de outros middlewares
# que modificam a resposta para garantir que os headers sejam incluídos
security_headers_config = SecurityHeadersConfig.from_settings()
app.add_middleware(
    SecurityHeadersMiddleware,
    hsts_max_age=security_headers_config["hsts_max_age"],
    hsts_include_subdomains=security_headers_config["hsts_include_subdomains"],
    hsts_preload=security_headers_config["hsts_preload"],
    csp_report_only=security_headers_config["csp_report_only"],
)
logger.info(
    "SecurityHeadersMiddleware configurado",
    hsts_max_age=security_headers_config["hsts_max_age"],
    hsts_include_subdomains=security_headers_config["hsts_include_subdomains"],
)


# Configura Rate Limiting
if settings.security_config.rate_limit_per_minute > 0:
    # General rate limiting middleware (60 req/min default)
    app.add_middleware(
        RateLimitMiddleware,
        limiter_type="general",
        skip_paths=["/health", "/docs", "/openapi.json", "/redoc", "/"],
    )

    # Auth-specific rate limiting middleware (5 req/min)
    app.add_middleware(
        AuthRateLimitMiddleware,
        protected_paths=["/auth", "/login", "/token", "/api-key"],
    )

    logger.info(
        "rate_limiting_configured",
        rate_limit_per_minute=settings.security_config.rate_limit_per_minute,
        auth_rate_limit=5,
    )
else:
    logger.warning("rate_limiting_disabled")


# Handlers de exceção
@app.exception_handler(AppException)
async def app_exception_handler(request: Request, exc: AppException) -> Any:
    """Trata exceções customizadas da aplicação."""
    from fastapi.responses import JSONResponse

    logger.error(
        "Erro na aplicação",
        error=exc.message,
        status_code=exc.status_code,
        path=request.url.path,
    )
    return JSONResponse(
        status_code=exc.status_code,
        content={
            "error": exc.__class__.__name__,
            "message": exc.message,
            "details": exc.details,
        },
    )


@app.exception_handler(RateLimitExceeded)
async def rate_limit_exception_handler(request: Request, exc: RateLimitExceeded) -> Any:
    """Trata exceções de rate limit com headers apropriados."""
    from fastapi.responses import JSONResponse

    retry_after = exc.retry_after or 60

    logger.warning(
        "rate_limit_exceeded",
        path=request.url.path,
        client_ip=request.client.host if request.client else None,
        retry_after=retry_after,
    )

    return JSONResponse(
        status_code=429,
        content={
            "error": "RateLimitExceeded",
            "message": exc.message,
            "retry_after": retry_after,
        },
        headers={
            "Retry-After": str(retry_after),
            "X-RateLimit-Limit": str(exc.details.get("limit", 60)),
            "X-RateLimit-Remaining": "0",
        },
    )


# Exception handlers for security (T034)
@app.exception_handler(AuthenticationException)
async def authentication_exception_handler(
    request: Request, exc: AuthenticationException
) -> Any:
    """Handle authentication exceptions with generic messages in production."""
    from fastapi.responses import JSONResponse

    # Mask any sensitive information in error message
    safe_message = (
        "Authentication failed"
        if settings.environment == "production"
        else exc.message
    )

    logger.warning(
        "authentication_failed",
        path=request.url.path,
        client_ip=request.client.host if request.client else None,
        error=SecretMasker.mask(exc.message),
    )

    return JSONResponse(
        status_code=exc.status_code,
        content={
            "error": "AuthenticationFailed",
            "message": safe_message,
        },
    )


@app.exception_handler(SecurityException)
async def security_exception_handler(request: Request, exc: SecurityException) -> Any:
    """Handle security exceptions with sanitized error messages."""
    from fastapi.responses import JSONResponse

    # In production, return generic message
    safe_message = (
        "Security violation detected"
        if settings.environment == "production"
        else exc.message
    )

    logger.warning(
        "security_exception",
        path=request.url.path,
        client_ip=request.client.host if request.client else None,
        error_type=exc.__class__.__name__,
        error=SecretMasker.mask(exc.message),
    )

    return JSONResponse(
        status_code=exc.status_code,
        content={
            "error": exc.__class__.__name__,
            "message": safe_message,
        },
    )


@app.exception_handler(Exception)
async def generic_exception_handler(request: Request, exc: Exception) -> Any:
    """Handle generic exceptions without exposing sensitive data.

    FR-034: Sistema deve ocultar detalhes de erro em produção.
    """
    from fastapi.responses import JSONResponse

    error_id = str(uuid.uuid4())[:8]

    # Log the full error internally (masked)
    logger.error(
        "unhandled_exception",
        error_id=error_id,
        path=request.url.path,
        error_type=exc.__class__.__name__,
        error_message=SecretMasker.mask(str(exc)),
    )

    # Return generic message in production, details in development
    if settings.environment == "production":
        content = {
            "error": "InternalServerError",
            "message": "An internal error occurred. Please contact support.",
            "error_id": error_id,
        }
    else:
        content = {
            "error": exc.__class__.__name__,
            "message": str(exc),
            "error_id": error_id,
        }

    return JSONResponse(
        status_code=500,
        content=content,
    )


# Inclui routers
app.include_router(health.router, tags=["Health"])
app.include_router(auth.router, tags=["Authentication"])
app.include_router(admin.router)
app.include_router(text.router)
app.include_router(audio.router)
app.include_router(video.router)
app.include_router(multimodal.router)


@app.get("/", tags=["Root"])
async def root() -> dict[str, Any]:
    """Endpoint raiz."""
    return {
        "name": settings.app_name,
        "version": settings.app_version,
        "docs": "/docs" if settings.debug else None,
        "health": "/health",
    }
