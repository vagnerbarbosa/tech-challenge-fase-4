"""Configuração de logging estruturado usando structlog.

Fornece logs formatados em JSON para produção e logs legíveis
para desenvolvimento. Inclui context binding para rastreamento de requests.
"""

import logging
import sys
from typing import Any

import structlog

from src.core.config import settings


def configure_logging() -> None:
    """Configura logging estruturado para a aplicação.

    Usa structlog para logging estruturado com fallback para
    logging padrão das bibliotecas de terceiros.
    """
    shared_processors: list[Any] = [
        # Adiciona nível de log na saída
        structlog.stdlib.filter_by_level,
        # Adiciona timestamp
        structlog.processors.TimeStamper(fmt="iso"),
        # Adiciona nível de log
        structlog.stdlib.add_log_level,
        # Adiciona nome do logger
        structlog.stdlib.add_logger_name,
        # Substitui informação de exceção por traceback formatado
        structlog.processors.format_exc_info,
    ]

    if settings.environment == "production":
        # Produção: formato JSON
        processors = shared_processors + [
            structlog.processors.dict_tracebacks,
            structlog.processors.JSONRenderer(),
        ]
    else:
        # Desenvolvimento: renderer de console com cores
        processors = shared_processors + [
            structlog.dev.ConsoleRenderer(
                colors=True,
                sort_keys=True,
            ),
        ]

    # Configura structlog
    structlog.configure(
        processors=processors,
        context_class=dict,
        logger_factory=structlog.stdlib.LoggerFactory(),
        wrapper_class=structlog.stdlib.BoundLogger,
        cache_logger_on_first_use=True,
    )

    # Configura logging da biblioteca padrão
    logging.basicConfig(
        format="%(message)s",
        stream=sys.stdout,
        level=getattr(logging, settings.log_level),
    )

    # Silencia loggers de terceiros barulhentos
    logging.getLogger("azure").setLevel(logging.WARNING)
    logging.getLogger("urllib3").setLevel(logging.WARNING)


def get_logger(name: str | None = None) -> structlog.stdlib.BoundLogger:
    """Obtém uma instância de logger estruturado.

    Args:
        name: Nome do logger (geralmente __name__)

    Returns:
        BoundLogger com capacidades de logging estruturado
    """
    return structlog.get_logger(name)


class RequestContextMiddleware:
    """Middleware ASGI para adicionar contexto de request nos logs.

    Adiciona request_id, method e path em todas as entradas de log
    dentro de um request.
    """

    def __init__(self, app: Any) -> None:
        self.app = app

    async def __call__(self, scope: Any, receive: Any, send: Any) -> None:
        """Adiciona contexto de request nos logs."""
        import uuid

        if scope["type"] == "http":
            request_id = str(uuid.uuid4())
            structlog.contextvars.clear_contextvars()
            structlog.contextvars.bind_contextvars(
                request_id=request_id,
                method=scope.get("method"),
                path=scope.get("path"),
            )

        await self.app(scope, receive, send)
