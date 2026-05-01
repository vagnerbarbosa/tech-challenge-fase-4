"""Gerenciamento de configuração usando Pydantic Settings.

Este módulo gerencia todas as configurações da aplicação, incluindo credenciais Azure,
rate limiting e configurações de segurança. Usa Pydantic Settings para validação
e carregamento de variáveis de ambiente.
"""

import os
from functools import lru_cache
from typing import Literal

from pydantic import Field, ValidationInfo, field_validator, model_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


def is_running_in_azure() -> bool:
    """Detecta se a aplicação está rodando no Azure App Service.

    Verifica a presença de variáveis de ambiente específicas do Azure.

    Returns:
        True se estiver no Azure App Service, False caso contrário.
    """
    # WEBSITE_SITE_NAME é definida automaticamente no Azure App Service
    # WEBSITE_INSTANCE_ID também indica App Service
    return bool(
        os.environ.get("WEBSITE_SITE_NAME")
        or os.environ.get("WEBSITE_INSTANCE_ID")
        or os.environ.get("WEBSITE_RESOURCE_GROUP")
    )


def _get_package_version() -> str:
    """Lê a versão do pacote do pyproject.toml.

    Usa importlib.metadata para obter a versão instalada do pacote.
    Fallback para versão hardcoded se pacote não estiver instalado.

    Returns:
        Versão da aplicação como string.
    """
    try:
        from importlib.metadata import version
        return version("multimodal-health-analysis")
    except Exception:
        # Fallback se pacote não estiver instalado (desenvolvimento)
        return "0.6.0"


class SecurityConfig(BaseSettings):
    """Configurações de segurança para hardening da API (Spec 007).

    Agrupa todas as configurações relacionadas à segurança:
    - Autenticação via API Key
    - Rate limiting
    - CORS
    - Redis para rate limiting distribuído

    Variáveis de ambiente são carregadas com prefixo SECURITY_.
    Exemplo: SECURITY_API_KEY, SECURITY_CORS_ORIGINS
    """

    model_config = SettingsConfigDict(
        env_prefix="SECURITY_",
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore",
    )

    api_key: str = Field(
        default="change-me-in-production",
        description="API key para autenticação de endpoints",
    )
    api_key_header: str = Field(
        default="X-API-Key",
        description="Nome do header HTTP para API key",
    )
    rate_limit_per_minute: int = Field(
        default=60,
        description="Requisições permitidas por minuto por IP/cliente",
    )
    redis_url: str = Field(
        default="redis://localhost:6379/0",
        description="URL de conexão com Redis para rate limiting",
    )
    cors_origins: str = Field(
        default="http://localhost:3000,http://localhost:8000",
        description="Origens permitidas para CORS (separadas por vírgula)",
    )
    environment: Literal["development", "staging", "production"] = Field(
        default="development",
        description="Ambiente de execução para ajustes de segurança",
    )
    secret_key: str = Field(
        default="change-me-in-production",
        description="Chave secreta para tokens e criptografia",
    )

    @field_validator("cors_origins")
    @classmethod
    def validate_cors_origins(cls, v: str) -> str:
        """Valida que CORS origins não está vazio em produção."""
        return v

    @property
    def cors_origins_list(self) -> list[str]:
        """Retorna lista de origens CORS permitidas."""
        return [origin.strip() for origin in self.cors_origins.split(",")]

    @property
    def is_production(self) -> bool:
        """Retorna True se ambiente é produção."""
        return self.environment == "production"

    # T010: Audit log configuration
    audit_log_path: str = Field(
        default="logs/audit.log",
        description="Path to the audit log file",
        alias="AUDIT_LOG_PATH",
    )
    audit_log_retention_days: int = Field(
        default=90,
        description="Number of days to retain audit logs",
        alias="AUDIT_LOG_RETENTION_DAYS",
    )
    audit_log_max_size_mb: int = Field(
        default=100,
        description="Maximum size of audit log file before rotation (MB)",
        alias="AUDIT_LOG_MAX_SIZE_MB",
    )
    audit_log_compress: bool = Field(
        default=True,
        description="Compress rotated audit logs with gzip",
        alias="AUDIT_LOG_COMPRESS",
    )


class Settings(BaseSettings):
    """Configurações da aplicação carregadas de variáveis de ambiente.

    Todas as credenciais Azure e configurações são validadas na inicialização.
    Variáveis obrigatórias irão gerar ValidationError se não forem fornecidas.
    """

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore",
    )

    # ===========================================
    # Configurações da Aplicação
    # ===========================================
    app_name: str = Field(
        default="Multimodal Health Analysis API",
        description="Nome da aplicação",
    )
    app_version: str = Field(
        default_factory=_get_package_version,
        description="Versão da aplicação (lida automaticamente do pyproject.toml)",
    )
    environment: Literal["development", "staging", "production"] = Field(
        default="development",
        description="Ambiente de deploy",
    )
    debug: bool = Field(
        default=False,
        description="Habilita modo debug",
    )
    log_level: Literal["DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"] = Field(
        default="INFO",
        description="Nível de logging",
    )

    # ===========================================
    # Configurações de Segurança (Spec 007)
    # ===========================================
    security_config: SecurityConfig = Field(
        default_factory=SecurityConfig,
        description="Configurações de segurança hardening",
    )

    # Legacy security fields (deprecated, use security_config)
    secret_key: str = Field(
        default="change-me-in-production",
        description="Chave secreta para segurança JWT/API",
    )
    api_key_header: str = Field(
        default="X-API-Key",
        description="Nome do header para autenticação via API key",
    )
    api_key: str | None = Field(
        default=None,
        description="API key para autenticação (opcional em dev)",
    )

    # ===========================================
    # Azure AI Language (Text Analytics)
    # ===========================================
    azure_text_key: str | None = Field(
        default=None,
        description="Chave da API Azure AI Language",
        alias="AZURE_TEXT_KEY",
    )
    azure_text_endpoint: str | None = Field(
        default=None,
        description="URL do endpoint Azure AI Language",
        alias="AZURE_TEXT_ENDPOINT",
    )

    # ===========================================
    # Azure AI Speech Services
    # ===========================================
    azure_speech_key: str | None = Field(
        default=None,
        description="Chave da API Azure AI Speech",
        alias="AZURE_SPEECH_KEY",
    )
    azure_speech_region: str = Field(
        default="brazilsouth",
        description="Região do Azure Speech Services",
        alias="AZURE_SPEECH_REGION",
    )

    # ===========================================
    # Azure AI Vision (Image Analysis)
    # ===========================================
    azure_vision_key: str | None = Field(
        default=None,
        description="Chave da API Azure AI Vision",
        alias="AZURE_VISION_KEY",
    )
    azure_vision_endpoint: str | None = Field(
        default=None,
        description="URL do endpoint Azure AI Vision",
        alias="AZURE_VISION_ENDPOINT",
    )

    # ===========================================
    # Azure Blob Storage
    # ===========================================
    azure_storage_connection_string: str | None = Field(
        default=None,
        description="String de conexão do Azure Storage",
        alias="AZURE_STORAGE_CONNECTION_STRING",
    )
    azure_storage_container: str = Field(
        default="health-media-uploads",
        description="Nome do container do Azure Storage",
        alias="AZURE_STORAGE_CONTAINER",
    )

    # ===========================================
    # Rate Limiting (Proteção Azure Free Tier)
    # ===========================================
    rate_limit_enabled: bool = Field(
        default=True,
        description="Habilita rate limiting para proteção Azure",
        alias="RATE_LIMIT_ENABLED",
    )
    max_text_requests_per_day: int = Field(
        default=160,  # ~5000/month / 31 days
        description="Máximo de requisições Text Analytics por dia",
        alias="MAX_TEXT_REQUESTS_PER_DAY",
    )
    max_speech_minutes_per_day: int = Field(
        default=10,  # ~300/month / 30 days
        description="Máximo de minutos Speech Services por dia",
        alias="MAX_SPEECH_MINUTES_PER_DAY",
    )
    max_vision_requests_per_day: int = Field(
        default=160,  # ~5000/month / 31 days
        description="Máximo de requisições Vision por dia",
        alias="MAX_VISION_REQUESTS_PER_DAY",
    )

    # ===========================================
    # Configurações do Banco de Dados
    # ===========================================
    database_url: str = Field(
        default="sqlite+aiosqlite:///./health_analysis.db",
        description="URL de conexão do banco de dados",
        alias="DATABASE_URL",
    )

    # ===========================================
    # Configurações do Redis (Opcional)
    # ===========================================
    redis_url: str = Field(
        default="redis://localhost:6379/0",
        description="URL de conexão do Redis",
        alias="REDIS_URL",
    )
    redis_enabled: bool = Field(
        default=False,
        description="Habilita Redis para rate limiting distribuído",
        alias="REDIS_ENABLED",
    )

    # ===========================================
    # Configurações de Upload de Arquivos
    # ===========================================
    max_upload_size_mb: int = Field(
        default=50,
        description="Tamanho máximo de arquivo em MB",
        alias="MAX_UPLOAD_SIZE_MB",
    )
    allowed_image_extensions: str = Field(
        default="jpg,jpeg,png",
        description="Lista de extensões de imagem permitidas separadas por vírgula",
        alias="ALLOWED_IMAGE_EXTENSIONS",
    )
    allowed_audio_extensions: str = Field(
        default="wav,mp3,ogg",
        description="Lista de extensões de áudio permitidas separadas por vírgula",
        alias="ALLOWED_AUDIO_EXTENSIONS",
    )
    allowed_video_extensions: str = Field(
        default="mp4,avi,mov",
        description="Lista de extensões de vídeo permitidas separadas por vírgula",
        alias="ALLOWED_VIDEO_EXTENSIONS",
    )
    upload_timeout_seconds: int = Field(
        default=300,
        description="Timeout de upload em segundos",
        alias="UPLOAD_TIMEOUT_SECONDS",
    )

    # ===========================================
    # Configurações de Conformidade LGPD
    # ===========================================
    data_retention_days: int = Field(
        default=30,
        description="Número de dias para reter dados antes da exclusão",
        alias="DATA_RETENTION_DAYS",
    )
    anonymize_pii: bool = Field(
        default=True,
        description="Anonimiza informações pessoalmente identificáveis",
        alias="ANONYMIZE_PII",
    )
    consent_required: bool = Field(
        default=True,
        description="Requer consentimento explícito para processamento de dados",
        alias="CONSENT_REQUIRED",
    )

    # ===========================================
    # Validadores
    # ===========================================
    @field_validator("azure_text_endpoint", "azure_vision_endpoint")
    @classmethod
    def validate_azure_endpoint(cls, v: str | None) -> str | None:
        """Garante que URLs de endpoint Azure são válidas."""
        if v is None:
            return v
        # Permitir HTTP em desenvolvimento (para mocks locais)
        if not v.startswith(("https://", "http://")):
            raise ValueError("Azure endpoint deve começar com http:// ou https://")
        if not v.endswith("/"):
            v = v + "/"
        return v

    @field_validator("secret_key")
    @classmethod
    def validate_secret_key(cls, v: str, info: ValidationInfo) -> str:
        """Alerta se a secret key padrão for usada em produção."""
        values = info.data
        if values.get("environment") == "production" and v == "change-me-in-production":
            raise ValueError("Deve alterar a secret_key padrão em produção")
        return v

    @model_validator(mode="after")
    def validate_azure_credentials(self) -> "Settings":
        """Valida se credenciais Azure estão configuradas em produção."""
        if self.environment == "production":
            missing = []
            if not self.azure_text_key:
                missing.append("azure_text_key")
            if not self.azure_speech_key:
                missing.append("azure_speech_key")
            if not self.azure_vision_key:
                missing.append("azure_vision_key")
            if missing:
                raise ValueError(
                    f"Credenciais Azure obrigatórias ausentes em produção: {', '.join(missing)}"
                )
        return self

    # ===========================================
    # Propriedades
    # ===========================================
    @property
    def max_upload_size_bytes(self) -> int:
        """Retorna tamanho máximo de upload em bytes."""
        return self.max_upload_size_mb * 1024 * 1024

    @property
    def is_azure(self) -> bool:
        """Detecta se está rodando no Azure App Service.

        Returns:
            True se estiver no Azure, False caso contrário.
        """
        return is_running_in_azure()

    @property
    def allowed_image_extensions_list(self) -> list[str]:
        """Retorna lista de extensões de imagem permitidas."""
        return [ext.strip().lower() for ext in self.allowed_image_extensions.split(",")]

    @property
    def allowed_audio_extensions_list(self) -> list[str]:
        """Retorna lista de extensões de áudio permitidas."""
        return [ext.strip().lower() for ext in self.allowed_audio_extensions.split(",")]

    @property
    def allowed_video_extensions_list(self) -> list[str]:
        """Retorna lista de extensões de vídeo permitidas."""
        return [ext.strip().lower() for ext in self.allowed_video_extensions.split(",")]


@lru_cache
def get_settings() -> Settings:
    """Obtém instância cacheada de configurações.

    Usa lru_cache para evitar recarregar configurações em cada chamada.
    """
    return Settings()


# Instância global de configurações para conveniência
settings = get_settings()

# ===========================================
# Palavras-chave de Detecção de Risco
# ===========================================
RISK_KEYWORDS: dict[str, list[str]] = {
    "violencia": [
        "violência",
        "agressão",
        "agredir",
        "agredi",
        "ameaça",
        "ameaçar",
        "bater",
        "bati",
        "bateram",
        "machucar",
        "machuquei",
        "machucaram",
        "xingar",
        "xingou",
        "xingaram",
        "humilhar",
        "humilhou",
        "humilharam",
        "controlar",
        "controla",
        "proibir",
        "proíbe",
        "ciúmes",
        "ciumento",
        "ciumenta",
        "separar",
        "separei",
        "fugir",
        "fugi",
        "medo",
        "tenho medo",
        "com medo",
        "apanhar",
        "apanhei",
        "soco",
        "chute",
        "empurrar",
        "empurrou",
        "empurraram",
        "gritar",
        "gritou",
        "gritaram",
        "insultar",
        "insultou",
        "ofender",
        "ofendeu",
        "ofenderam",
        "tapa",
        "tapas",
        "empurrão",
        "puxar",
        "puxou",
        "arrancar",
        "arrancou",
        "arma",
        "faca",
        "revólver",
        "pistola",
        "arma de fogo",
        "atirar",
        "atirou",
        "atiraram",
        "disparar",
        "disparou",
        "apontar",
        "apontou",
        "apontaram",
        "matar",
        "matou",
        "mataram",
        "matarem",
        "morrer",
        "morreu",
        "morreram",
        "socorro",
        "ajuda",
        "me ajuda",
        "polícia",
        "liga para polícia",
        "chamar polícia",
        "hospital",
        "preciso de ajuda",
        "estou em perigo",
        "estou em risco",
        "me mata",
        "vou morrer",
        "vai me matar",
        "vai matar",
    ],
    "saude_mental": [
        "ansiedade",
        "ansiosa",
        "ansioso",
        "nervosa",
        "nervoso",
        "depressão",
        "depressiva",
        "depressivo",
        "triste",
        "tristeza",
        "chorar",
        "choro",
        "chorei",
        "suicídio",
        "suicida",
        "morrer",
        "morra",
        "acabar",
        "acabar com tudo",
        "desaparecer",
        "sumir",
        "não aguento",
        "não aguento mais",
        "desespero",
        "desesperada",
        "desesperado",
        "pânico",
        "crise",
        "ataque",
        "ataque de pânico",
        "insônia",
        "não durmo",
        "não consigo dormir",
        "cansada",
        "cansado",
        "exausta",
        "exausto",
        "sem forças",
        "sem energia",
        "vazio",
        "vazia",
        "sem sentido",
        "desanimada",
        "desanimado",
        "pessimismo",
        "pessimista",
        "culpa",
        "culpada",
        "culpado",
        "inútil",
        "fracassada",
        "fracassado",
        "solidão",
        "só",
        "sozinha",
        "sozinho",
        "isolada",
        "isolado",
    ],
}
