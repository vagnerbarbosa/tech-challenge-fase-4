"""Gerenciamento de configuração usando Pydantic Settings.

Este módulo gerencia todas as configurações da aplicação, incluindo credenciais Azure,
rate limiting e configurações de segurança. Usa Pydantic Settings para validação
e carregamento de variáveis de ambiente.
"""

from functools import lru_cache
from typing import Literal, Optional

from pydantic import Field, field_validator, model_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


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
        default="1.0.0",
        description="Versão da aplicação",
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
    # Configurações de Segurança
    # ===========================================
    secret_key: str = Field(
        default="change-me-in-production",
        description="Chave secreta para segurança JWT/API",
    )
    api_key_header: str = Field(
        default="X-API-Key",
        description="Nome do header para autenticação via API key",
    )
    api_key: Optional[str] = Field(
        default=None,
        description="API key para autenticação (opcional em dev)",
    )

    # ===========================================
    # Azure AI Language (Text Analytics)
    # ===========================================
    azure_text_key: Optional[str] = Field(
        default=None,
        description="Chave da API Azure AI Language",
        alias="AZURE_TEXT_KEY",
    )
    azure_text_endpoint: Optional[str] = Field(
        default=None,
        description="URL do endpoint Azure AI Language",
        alias="AZURE_TEXT_ENDPOINT",
    )

    # ===========================================
    # Azure AI Speech Services
    # ===========================================
    azure_speech_key: Optional[str] = Field(
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
    azure_vision_key: Optional[str] = Field(
        default=None,
        description="Chave da API Azure AI Vision",
        alias="AZURE_VISION_KEY",
    )
    azure_vision_endpoint: Optional[str] = Field(
        default=None,
        description="URL do endpoint Azure AI Vision",
        alias="AZURE_VISION_ENDPOINT",
    )

    # ===========================================
    # Azure Blob Storage
    # ===========================================
    azure_storage_connection_string: Optional[str] = Field(
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
        default="wav,mp3,ogg,m4a",
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
    def validate_azure_endpoint(cls, v: Optional[str]) -> Optional[str]:
        """Garante que URLs de endpoint Azure são válidas."""
        if v is None:
            return v
        if not v.startswith("https://"):
            raise ValueError("Azure endpoint deve usar HTTPS")
        if not v.endswith("/"):
            v = v + "/"
        return v

    @field_validator("secret_key")
    @classmethod
    def validate_secret_key(cls, v: str, info) -> str:
        """Alerta se a secret key padrão for usada em produção."""
        values = info.data
        if values.get("environment") == "production" and v == "change-me-in-production":
            raise ValueError("Deve alterar a secret_key padrão em produção")
        return v

    @model_validator(mode="after")
    def validate_azure_credentials(self):
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


@lru_cache()
def get_settings() -> Settings:
    """Obtém instância cacheada de configurações.

    Usa lru_cache para evitar recarregar configurações em cada chamada.
    """
    return Settings()


# Instância global de configurações para conveniência
settings = get_settings()
