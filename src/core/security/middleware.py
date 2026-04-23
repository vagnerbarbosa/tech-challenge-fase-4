"""Middleware de segurança para CORS, headers de segurança e validação de requisições.

Este módulo implementa:
- SecurityHeadersMiddleware: Headers de segurança HTTP (HSTS, CSP, etc.)
- CORSValidation: Validação customizada de origens CORS
- Logging de tentativas de acesso de origens não permitidas
- Validação de preflight requests

Implementation T050-T055: Security headers hardening para Spec 007.
"""

from collections.abc import Callable
from typing import Any

from fastapi import Request
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.responses import Response

from src.core.config import settings
from src.core.logging_config import get_logger

logger = get_logger(__name__)


class CORSValidation(BaseHTTPMiddleware):
    """Middleware para validação customizada de CORS.

    Adiciona logging e validações extras para requisições CORS:
    - Log de origens permitidas em debug
    - Log de warning para origens não permitidas
    - Validação de preflight requests
    """

    def __init__(
        self,
        app: Any,
        allowed_origins: list[str],
        environment: str = "development",
    ) -> None:
        """Inicializa o middleware de validação CORS.

        Args:
            app: Aplicação ASGI
            allowed_origins: Lista de origens permitidas
            environment: Ambiente de execução (development, staging, production)
        """
        super().__init__(app)
        self.allowed_origins = allowed_origins
        self.environment = environment
        self.is_production = environment == "production"
        self._log_cors_configuration()

    def _log_cors_configuration(self) -> None:
        """Loga a configuração atual de CORS."""
        if "*" in self.allowed_origins:
            if self.is_production:
                logger.warning(
                    "CORS configurado com '*' em ambiente de producao",
                    environment=self.environment,
                    allowed_origins=self.allowed_origins,
                )
            else:
                logger.warning(
                    "CORS configurado com '*' em ambiente nao-producao",
                    environment=self.environment,
                    allowed_origins=self.allowed_origins,
                    message="Recomendado configurar origens especificas",
                )
        else:
            logger.info(
                "CORS configurado com origens especificas",
                environment=self.environment,
                allowed_origins=self.allowed_origins,
                count=len(self.allowed_origins),
            )

    async def dispatch(self, request: Request, call_next: Callable[[Request], Response]) -> Response:  # type: ignore[override,misc]
        """Processa a requisição e valida CORS.

        Args:
            request: Requisição HTTP
            call_next: Próximo middleware/handler

        Returns:
            Response HTTP
        """
        origin = request.headers.get("origin")
        method = request.method

        # Validação de preflight request
        if method == "OPTIONS" and origin:
            logger.debug(
                "Preflight request recebida",
                origin=origin,
                path=request.url.path,
                headers=dict(request.headers),
            )

        # Validação de origem
        if origin and origin not in self.allowed_origins and "*" not in self.allowed_origins:
            logger.warning(
                "Tentativa de acesso de origem nao permitida",
                origin=origin,
                allowed_origins=self.allowed_origins,
                path=request.url.path,
                method=method,
            )

        # Log de origens permitidas em debug
        if origin and origin in self.allowed_origins:
            logger.debug(
                "Requisicao de origem permitida",
                origin=origin,
                path=request.url.path,
                method=method,
            )

        response = await call_next(request)  # type: ignore[misc]

        # Adiciona headers CORS na resposta se necessário
        if origin:
            if "*" in self.allowed_origins:
                response.headers["Access-Control-Allow-Origin"] = "*"
            elif origin in self.allowed_origins:
                response.headers["Access-Control-Allow-Origin"] = origin

        return response


def create_cors_middleware(
    allowed_origins: list[str],
    allow_credentials: bool = True,
    allow_methods: list[str] | None = None,
    allow_headers: list[str] | None = None,
    environment: str = "development",
) -> dict[str, Any]:
    """Cria configuração para CORSMiddleware.

    Args:
        allowed_origins: Lista de origens permitidas
        allow_credentials: Permite credenciais em requisições CORS
        allow_methods: Lista de métodos permitidos (default: todos)
        allow_headers: Lista de headers permitidos (default: todos)
        environment: Ambiente de execução

    Returns:
        Dict com configuração do middleware
    """
    if allow_methods is None:
        allow_methods = ["GET", "POST", "PUT", "DELETE", "OPTIONS", "PATCH"]

    if allow_headers is None:
        allow_headers = [
            "*",
            "Content-Type",
            "Authorization",
            "X-API-Key",
            "X-Request-ID",
        ]

    # Validações de segurança
    if "*" in allowed_origins and allow_credentials and environment == "production":
        logger.warning(
            "Configuracao insegura: CORS '*' com credentials em producao",
            allowed_origins=allowed_origins,
            allow_credentials=allow_credentials,
        )

    return {
        "allow_origins": allowed_origins,
        "allow_credentials": allow_credentials,
        "allow_methods": allow_methods,
        "allow_headers": allow_headers,
    }


class PreflightRequestValidator:
    """Validador de preflight requests CORS.

    Valida se preflight requests contêm todos os headers necessários
    e se o método solicitado é permitido.
    """

    REQUIRED_PREFLIGHT_HEADERS = {
        "Access-Control-Request-Method",
        "Origin",
    }

    def __init__(self, allowed_methods: list[str], allowed_headers: list[str]) -> None:
        """Inicializa o validador.

        Args:
            allowed_methods: Métodos HTTP permitidos
            allowed_headers: Headers permitidos
        """
        self.allowed_methods = [m.upper() for m in allowed_methods]
        self.allowed_headers = [h.lower() for h in allowed_headers]

    def validate(self, request: Request) -> tuple[bool, str | None]:
        """Valida uma preflight request.

        Args:
            request: Requisição HTTP

        Returns:
            Tupla (is_valid, error_message)
        """
        # Verifica headers obrigatórios
        missing_headers = self.REQUIRED_PREFLIGHT_HEADERS - set(request.headers.keys())
        if missing_headers:
            return False, f"Headers obrigatorios ausentes: {missing_headers}"

        # Verifica método solicitado
        requested_method = request.headers.get("Access-Control-Request-Method", "").upper()
        if requested_method and requested_method not in self.allowed_methods:
            return False, f"Metodo nao permitido: {requested_method}"

        # Verifica headers solicitados
        requested_headers = request.headers.get("Access-Control-Request-Headers", "")
        if requested_headers:
            headers_list = [h.strip().lower() for h in requested_headers.split(",")]
            # '*' permite todos os headers
            if "*" not in self.allowed_headers:
                invalid_headers = [h for h in headers_list if h not in self.allowed_headers]
                if invalid_headers:
                    return False, f"Headers nao permitidos: {invalid_headers}"

        return True, None


class SecurityHeadersMiddleware(BaseHTTPMiddleware):
    """Middleware para adicionar headers de segurança em todas as respostas HTTP.

    Implementa as melhores práticas de headers de segurança baseadas em OWASP:
    - Strict-Transport-Security (HSTS) - T051
    - Content-Security-Policy (CSP) - T052
    - X-Content-Type-Options - T053
    - X-Frame-Options - T054
    - Referrer-Policy - T055
    - X-XSS-Protection
    - Permissions-Policy

    Attributes:
        hsts_max_age: HSTS max-age em segundos (padrão: 31536000 = 1 ano)
        hsts_include_subdomains: Incluir subdomínios no HSTS (padrão: True)
        hsts_preload: Incluir diretiva preload (padrão: False)
    """

    def __init__(
        self,
        app: Any,
        hsts_max_age: int = 31536000,  # 1 ano
        hsts_include_subdomains: bool = True,
        hsts_preload: bool = False,
        csp_report_only: bool = False,
    ) -> None:
        """Inicializa o middleware de headers de segurança.

        Args:
            app: Aplicação ASGI
            hsts_max_age: HSTS max-age em segundos
            hsts_include_subdomains: Incluir subdomínios no HSTS
            hsts_preload: Incluir diretiva preload para HSTS
            csp_report_only: Se True, usa Content-Security-Policy-Report-Only
        """
        super().__init__(app)
        self.hsts_max_age = hsts_max_age
        self.hsts_include_subdomains = hsts_include_subdomains
        self.hsts_preload = hsts_preload
        self.csp_report_only = csp_report_only

    async def dispatch(self, request: Request, call_next: Callable[[Request], Response]) -> Response:  # type: ignore[override,misc]
        """Processa a requisição e adiciona headers de segurança na resposta.

        Args:
            request: Requisição HTTP de entrada
            call_next: Próximo middleware/handler na cadeia

        Returns:
            Response com headers de segurança adicionados
        """
        response = await call_next(request)  # type: ignore[misc]

        # Adiciona header HSTS (T051)
        self._add_hsts_header(response)

        # Adiciona header CSP (T052)
        self._add_csp_header(response)

        # Adiciona header X-Content-Type-Options (T053)
        self._add_content_type_options_header(response)

        # Adiciona header X-Frame-Options (T054)
        self._add_frame_options_header(response)

        # Adiciona header Referrer-Policy (T055)
        self._add_referrer_policy_header(response)

        # Adiciona headers adicionais de segurança
        self._add_xss_protection_header(response)
        self._add_permissions_policy_header(response)

        return response

    def _add_hsts_header(self, response: Response) -> None:
        """Adiciona header Strict-Transport-Security (HSTS). (T051)

        Força conexões HTTPS e previne ataques de downgrade.
        Formato: max-age=31536000; includeSubDomains; preload

        Args:
            response: Resposta HTTP para modificar
        """
        hsts_value = f"max-age={self.hsts_max_age}"

        if self.hsts_include_subdomains:
            hsts_value += "; includeSubDomains"

        if self.hsts_preload:
            hsts_value += "; preload"

        response.headers["Strict-Transport-Security"] = hsts_value

    def _add_csp_header(self, response: Response) -> None:
        """Adiciona header Content-Security-Policy. (T052)

        Previne XSS e ataques de injeção de dados controlando
        quais recursos podem ser carregados.

        Args:
            response: Resposta HTTP para modificar
        """
        csp_directives = [
            # Política padrão: apenas recursos da mesma origem
            "default-src 'self'",
            # Scripts: self + inline com suporte a nonce/hash
            "script-src 'self'",
            # Styles: self + inline (necessário para alguns frameworks UI)
            "style-src 'self' 'unsafe-inline'",
            # Imagens: self + data URIs + blob
            "img-src 'self' data: blob:",
            # Fontes: self + data URIs
            "font-src 'self' data:",
            # Connect: apenas self (para chamadas API)
            "connect-src 'self'",
            # Mídia: self + blob (para uploads de vídeo/áudio)
            "media-src 'self' blob:",
            # Objetos: nenhum (sem Flash/Java)
            "object-src 'none'",
            # Frames: nenhum (prevenir clickjacking)
            "frame-src 'none'",
            # Ancestrais de frame: nenhum (prevenir embedding)
            "frame-ancestors 'none'",
            # Base URI: apenas self
            "base-uri 'self'",
            # Ações de formulário: apenas self
            "form-action 'self'",
        ]

        # Adiciona upgrade-insecure-requests em produção
        if settings.environment == "production":
            csp_directives.append("upgrade-insecure-requests")

        csp_value = "; ".join(csp_directives)

        if self.csp_report_only:
            response.headers["Content-Security-Policy-Report-Only"] = csp_value
        else:
            response.headers["Content-Security-Policy"] = csp_value

    def _add_content_type_options_header(self, response: Response) -> None:
        """Adiciona header X-Content-Type-Options. (T053)

        Previne ataques de sniffing de MIME type forçando browsers
        a respeitar o Content-Type declarado.

        Args:
            response: Resposta HTTP para modificar
        """
        response.headers["X-Content-Type-Options"] = "nosniff"

    def _add_frame_options_header(self, response: Response) -> None:
        """Adiciona header X-Frame-Options. (T054)

        Previne ataques de clickjacking controlando se/quando
        a página pode ser embarcada em frames/iframes.

        Args:
            response: Resposta HTTP para modificar
        """
        response.headers["X-Frame-Options"] = "DENY"

    def _add_referrer_policy_header(self, response: Response) -> None:
        """Adiciona header Referrer-Policy. (T055)

        Controla quanta informação de referrer é incluída nas requisições.
        "strict-origin-when-cross-origin" envia URL completa para mesma origem,
        apenas origem para cross-origin, e nenhum referrer para HTTPS->HTTP.

        Args:
            response: Resposta HTTP para modificar
        """
        response.headers["Referrer-Policy"] = "strict-origin-when-cross-origin"

    def _add_xss_protection_header(self, response: Response) -> None:
        """Adiciona header X-XSS-Protection.

        Proteção legada contra XSS (browsers modernos
        dependem do CSP, mas isso ajuda browsers antigos).

        Args:
            response: Resposta HTTP para modificar
        """
        response.headers["X-XSS-Protection"] = "1; mode=block"

    def _add_permissions_policy_header(self, response: Response) -> None:
        """Adiciona header Permissions-Policy (anteriormente Feature-Policy).

        Controla quais features do browser podem ser usadas pela página.

        Args:
            response: Resposta HTTP para modificar
        """
        # Desabilita features potencialmente perigosas por padrão
        permissions = [
            "accelerometer=()",
            "ambient-light-sensor=()",
            "autoplay=()",
            "battery=()",
            "camera=()",
            "display-capture=()",
            "document-domain=()",
            "encrypted-media=()",
            "execution-while-not-rendered=()",
            "execution-while-out-of-viewport=()",
            "fullscreen=()",
            "gamepad=()",
            "geolocation=()",
            "gyroscope=()",
            "hid=()",
            "identity-credentials-get=()",
            "idle-detection=()",
            "keyboard-map=()",
            "local-fonts=()",
            "magnetometer=()",
            "microphone=()",
            "midi=()",
            "navigation-override=()",
            "payment=()",
            "picture-in-picture=()",
            "publickey-credentials-create=()",
            "publickey-credentials-get=()",
            "screen-wake-lock=()",
            "serial=()",
            "speaker-selection=()",
            "storage-access=()",
            "sync-xhr=()",
            "usb=()",
            "web-share=()",
            "xr-spatial-tracking=()",
        ]

        response.headers["Permissions-Policy"] = ", ".join(permissions)


class SecurityHeadersConfig:
    """Configuração para middleware de headers de segurança.

    Fornece defaults baseados no ambiente para configurações de headers de segurança.
    """

    @classmethod
    def from_settings(cls) -> dict[str, Any]:
        """Cria configuração de middleware a partir das configurações da aplicação.

        Returns:
            Dicionário de opções de configuração para SecurityHeadersMiddleware
        """
        is_production = settings.environment == "production"

        return {
            "hsts_max_age": 31536000 if is_production else 0,  # 1 ano em prod
            "hsts_include_subdomains": True,  # Always include for test compatibility
            "hsts_preload": is_production,  # Habilitar apenas após testar em prod
            "csp_report_only": False,  # Sempre aplicar CSP
        }

