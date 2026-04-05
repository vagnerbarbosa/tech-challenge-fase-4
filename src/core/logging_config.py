"""Structured logging configuration using structlog.

Provides JSON-formatted logging for production and human-readable logs
for development. Includes context binding for request tracing.
"""

import logging
import sys
from typing import Any

import structlog

from src.core.config import settings


def configure_logging() -> None:
    """Configure structured logging for the application.

    Uses structlog for structured logging with fallback to standard
    logging for third-party libraries.
    """
    shared_processors: list[Any] = [
        # Add log level to output
        structlog.stdlib.filter_by_level,
        # Add timestamp
        structlog.processors.TimeStamper(fmt="iso"),
        # Add log level
        structlog.stdlib.add_log_level,
        # Add logger name
        structlog.stdlib.add_logger_name,
        # Replace exception info with formatted traceback
        structlog.processors.format_exc_info,
    ]

    if settings.environment == "production":
        # Production: JSON format
        processors = shared_processors + [
            structlog.processors.dict_tracebacks,
            structlog.processors.JSONRenderer(),
        ]
    else:
        # Development: Console renderer with colors
        processors = shared_processors + [
            structlog.dev.ConsoleRenderer(
                colors=True,
                sort_keys=True,
            ),
        ]

    # Configure structlog
    structlog.configure(
        processors=processors,
        context_class=dict,
        logger_factory=structlog.stdlib.LoggerFactory(),
        wrapper_class=structlog.stdlib.BoundLogger,
        cache_logger_on_first_use=True,
    )

    # Configure standard library logging
    logging.basicConfig(
        format="%(message)s",
        stream=sys.stdout,
        level=getattr(logging, settings.log_level),
    )

    # Silence noisy third-party loggers
    logging.getLogger("azure").setLevel(logging.WARNING)
    logging.getLogger("urllib3").setLevel(logging.WARNING)


def get_logger(name: str | None = None) -> structlog.stdlib.BoundLogger:
    """Get a structured logger instance.

    Args:
        name: Logger name (usually __name__)

    Returns:
        BoundLogger with structured logging capabilities
    """
    return structlog.get_logger(name)


class RequestContextMiddleware:
    """ASGI middleware to add request context to logs.

    Adds request_id, method, and path to all log entries within a request.
    """

    def __init__(self, app: Any) -> None:
        self.app = app

    async def __call__(self, scope: Any, receive: Any, send: Any) -> None:
        """Add request context to logs."""
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
