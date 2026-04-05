"""Ponto de entrada da aplicação FastAPI.

Configura a aplicação FastAPI com todos os middlewares, rotas
e handlers de exceção.
"""

from contextlib import asynccontextmanager
from typing import Any

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware

from src.api.routes import health
from src.core.config import settings
from src.core.exceptions import AppException
from src.core.logging_config import configure_logging, get_logger

# Configura logging
configure_logging()
logger = get_logger(__name__)


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
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"] if settings.debug else [],  # TODO: Configurar para produção
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


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


# Inclui routers
app.include_router(health.router, tags=["Health"])


@app.get("/", tags=["Root"])
async def root() -> dict[str, Any]:
    """Endpoint raiz."""
    return {
        "name": settings.app_name,
        "version": settings.app_version,
        "docs": "/docs" if settings.debug else None,
        "health": "/health",
    }
