"""Middleware de rate limiting para FastAPI.

Adiciona headers X-RateLimit-* a todas as respostas e trata exceções de rate limit.
"""

from collections.abc import Awaitable, Callable
from typing import Any

from fastapi import Request, Response
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.responses import JSONResponse
from structlog import get_logger

from src.core.security.rate_limiter import (
    RateLimiters,
    check_rate_limit,
    get_rate_limiters,
)

logger = get_logger(__name__)


class RateLimitMiddleware(BaseHTTPMiddleware):
    """Middleware para adicionar headers de rate limiting às respostas.

    Adiciona os seguintes headers a todas as respostas:
    - X-RateLimit-Limit: Máximo de requisições permitidas
    - X-RateLimit-Remaining: Requisições restantes na janela
    - X-RateLimit-Reset: Segundos até o reset do rate limit
    """

    def __init__(
        self,
        app: Any,
        limiter_type: str = "general",
        skip_paths: list[str] | None = None,
    ) -> None:
        """Inicializa o middleware de rate limiting.

        Args:
            app: Aplicação FastAPI
            limiter_type: Tipo de rate limiter (general, auth, analyze, health)
            skip_paths: Lista de caminhos para ignorar rate limiting
        """
        super().__init__(app)
        self.limiter_type = limiter_type
        self.skip_paths = skip_paths or ["/health", "/docs", "/openapi.json", "/redoc"]
        self._limiters: RateLimiters | None = None

    async def dispatch(
        self,
        request: Request,
        call_next: Callable[[Request], Awaitable[Response]],
    ) -> Response:
        """Processa a requisição e adiciona headers de rate limit.

        CRÍTICO: A verificação de rate limit acontece ANTES do call_next
        para garantir que 429 seja retornado antes de 401 (falha de auth).
        Isso evita que ataques de autenticação sejam mascarados por violações
        de rate limit.

        Args:
            request: Requisição FastAPI
            call_next: Próximo middleware/handler

        Returns:
            Resposta com headers de rate limit
        """
        # Ignora rate limiting para certos caminhos
        path = request.url.path
        if any(path.startswith(skip) for skip in self.skip_paths):
            return await call_next(request)

        # Obtém identificador do cliente
        identifier = self._get_client_identifier(request)

        # Verifica rate limit ANTES de processar a requisição (garante 429 antes de 401)
        is_allowed, info = await check_rate_limit(identifier, self.limiter_type)

        if not is_allowed:
            # Rate limit excedido - retorna 429 imediatamente (antes da verificação de auth)
            retry_after = info.get("reset_after", 60)

            logger.warning(
                "rate_limit_exceeded",
                path=path,
                identifier=identifier[:8] + "...",  # Identificador parcial para privacidade
                retry_after=retry_after,
            )

            return JSONResponse(
                status_code=429,
                content={
                    "error": "RateLimitExceeded",
                    "message": f"Rate limit excedido. Tente novamente após {retry_after} segundos.",
                    "retry_after": retry_after,
                },
                headers={
                    "Retry-After": str(retry_after),
                    "X-RateLimit-Limit": str(info["limit"]),
                    "X-RateLimit-Remaining": "0",
                    "X-RateLimit-Reset": str(retry_after),
                },
            )

        # Rate limit OK - processa requisição (pode retornar 401, 403, etc.)
        response = await call_next(request)

        # Adiciona headers de rate limit à resposta (sobrescreve existentes)
        response.headers["X-RateLimit-Limit"] = str(info["limit"])
        response.headers["X-RateLimit-Remaining"] = str(info["remaining"])
        response.headers["X-RateLimit-Reset"] = str(info["reset_after"])

        return response

    async def _get_rate_limit_info(self, identifier: str) -> dict[str, Any]:
        """Obtém informações de rate limit sem verificar o limite.

        Args:
            identifier: Identificador do cliente

        Returns:
            Dicionário com informações de rate limit
        """
        from src.core.security.rate_limiter import get_rate_limiters

        limiters = get_rate_limiters()
        limiter = limiters.general
        return await limiter.get_rate_limit_info(identifier)

    def _get_client_identifier(self, request: Request) -> str:
        """Extrai identificador do cliente da requisição.

        Prioridade:
        1. Header X-API-Key (hasheada)
        2. Header X-Forwarded-For (primeiro IP)
        3. Header X-Real-IP
        4. Endereço remoto

        Args:
            request: Requisição FastAPI

        Returns:
            String com identificador do cliente
        """
        # Verifica API key primeiro
        api_key = request.headers.get("X-API-Key")
        if api_key:
            return f"api:{api_key}"

        # Obtém endereço IP
        forwarded_for = request.headers.get("X-Forwarded-For")
        if forwarded_for:
            # Primeiro IP no X-Forwarded-For é o cliente
            return forwarded_for.split(",")[0].strip()

        real_ip = request.headers.get("X-Real-IP")
        if real_ip:
            return real_ip

        # Fallback para endereço remoto
        if request.client:
            return str(request.client.host)

        return "unknown"


class AuthRateLimitMiddleware(BaseHTTPMiddleware):
    """Rate limiting mais restritivo para endpoints de autenticação.

    Aplica limites mais rigorosos (5/min) a endpoints relacionados a auth
    para proteger contra ataques de força bruta.
    """

    def __init__(
        self,
        app: Any,
        protected_paths: list[str] | None = None,
    ) -> None:
        """Inicializa o middleware de rate limiting para auth.

        Args:
            app: Aplicação FastAPI
            protected_paths: Caminhos que requerem rate limiting mais restritivo
        """
        super().__init__(app)
        self.protected_paths = protected_paths or [
            "/auth",
            "/login",
            "/token",
            "/api-key",
        ]

    async def dispatch(
        self,
        request: Request,
        call_next: Callable[[Request], Awaitable[Response]],
    ) -> Response:
        """Processa requisição com rate limiting específico para auth.

        CRÍTICO: A verificação de rate limit acontece ANTES do call_next
        para garantir que 429 seja retornado antes de 401 (falha de auth).

        Args:
            request: Requisição FastAPI
            call_next: Próximo middleware/handler

        Returns:
            Resposta com headers de rate limit
        """
        path = request.url.path

        # Aplica apenas a caminhos de auth
        if not any(path.startswith(p) for p in self.protected_paths):
            return await call_next(request)

        identifier = self._get_client_identifier(request)

        # Verifica rate limit ANTES de processar a requisição (garante 429 antes de 401)
        is_allowed, info = await check_rate_limit(identifier, "auth")

        if not is_allowed:
            # Rate limit excedido - retorna 429 imediatamente (antes da verificação de auth)
            retry_after = info.get("reset_after", 60)

            logger.warning(
                "auth_rate_limit_exceeded",
                path=path,
                identifier=identifier[:8] + "...",
                retry_after=retry_after,
            )

            return JSONResponse(
                status_code=429,
                content={
                    "error": "RateLimitExceeded",
                    "message": "Muitas tentativas de autenticação. Tente novamente mais tarde.",
                    "retry_after": retry_after,
                },
                headers={
                    "Retry-After": str(retry_after),
                    "X-RateLimit-Limit": str(info["limit"]),
                    "X-RateLimit-Remaining": "0",
                    "X-RateLimit-Reset": str(retry_after),
                },
            )

        # Rate limit OK - processa requisição (pode retornar 401, 403, etc.)
        response = await call_next(request)

        # Adiciona headers de rate limit
        response.headers["X-RateLimit-Limit"] = str(info["limit"])
        response.headers["X-RateLimit-Remaining"] = str(info["remaining"])
        response.headers["X-RateLimit-Reset"] = str(info["reset_after"])

        return response

    def _get_client_identifier(self, request: Request) -> str:
        """Extrai identificador do cliente da requisição.

        Para endpoints de auth, usa combinação de IP + caminho para prevenir
        ataques distribuídos no mesmo endpoint.
        """
        # Obtém endereço IP
        forwarded_for = request.headers.get("X-Forwarded-For")
        if forwarded_for:
            ip = forwarded_for.split(",")[0].strip()
        else:
            real_ip = request.headers.get("X-Real-IP")
            ip = real_ip or (request.client.host if request.client else "unknown")

        # Inclui caminho no identificador para rate limit por endpoint
        return f"{ip}:{request.url.path}"


# Funções auxiliares para verificações manuais de rate limit

async def add_rate_limit_headers(
    response: Response,
    identifier: str,
    limiter_type: str = "general",
) -> Response:
    """Adiciona headers de rate limit a uma resposta.

    Args:
        response: Resposta FastAPI
        identifier: Identificador do cliente
        limiter_type: Tipo de rate limiter

    Returns:
        Resposta com headers adicionados
    """
    limiters = get_rate_limiters()

    limiter_map = {
        "general": limiters.general,
        "auth": limiters.auth,
        "analyze": limiters.analyze,
        "health": limiters.health,
    }

    limiter = limiter_map.get(limiter_type, limiters.general)
    info = await limiter.get_rate_limit_info(identifier)

    response.headers["X-RateLimit-Limit"] = str(info["limit"])
    response.headers["X-RateLimit-Remaining"] = str(info["remaining"])
    response.headers["X-RateLimit-Reset"] = str(info["reset_after"])

    return response
