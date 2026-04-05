"""Configuration management using Pydantic Settings.

This module handles all application configuration, including Azure credentials,
rate limiting, and security settings. Uses Pydantic Settings for validation
and environment variable loading.
"""

from functools import lru_cache
from typing import Literal, Optional

from pydantic import Field, field_validator, model_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Application settings loaded from environment variables.

    All Azure credentials and configuration are validated at startup.
    Required variables will raise ValidationError if not provided.
    """

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore",
    )

    # ===========================================
    # Application Settings
    # ===========================================
    app_name: str = Field(
        default="Multimodal Health Analysis API",
        description="Application name",
    )
    app_version: str = Field(
        default="1.0.0",
        description="Application version",
    )
    environment: Literal["development", "staging", "production"] = Field(
        default="development",
        description="Deployment environment",
    )
    debug: bool = Field(
        default=False,
        description="Enable debug mode",
    )
    log_level: Literal["DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"] = Field(
        default="INFO",
        description="Logging level",
    )

    # ===========================================
    # Security Settings
    # ===========================================
    secret_key: str = Field(
        default="change-me-in-production",
        description="Secret key for JWT/API security",
    )
    api_key_header: str = Field(
        default="X-API-Key",
        description="Header name for API key authentication",
    )
    api_key: Optional[str] = Field(
        default=None,
        description="API key for authentication (optional in dev)",
    )

    # ===========================================
    # Azure AI Language (Text Analytics)
    # ===========================================
    azure_text_key: Optional[str] = Field(
        default=None,
        description="Azure AI Language API key",
        alias="AZURE_TEXT_KEY",
    )
    azure_text_endpoint: Optional[str] = Field(
        default=None,
        description="Azure AI Language endpoint URL",
        alias="AZURE_TEXT_ENDPOINT",
    )

    # ===========================================
    # Azure AI Speech Services
    # ===========================================
    azure_speech_key: Optional[str] = Field(
        default=None,
        description="Azure AI Speech API key",
        alias="AZURE_SPEECH_KEY",
    )
    azure_speech_region: str = Field(
        default="brazilsouth",
        description="Azure Speech Services region",
        alias="AZURE_SPEECH_REGION",
    )

    # ===========================================
    # Azure AI Vision (Image Analysis)
    # ===========================================
    azure_vision_key: Optional[str] = Field(
        default=None,
        description="Azure AI Vision API key",
        alias="AZURE_VISION_KEY",
    )
    azure_vision_endpoint: Optional[str] = Field(
        default=None,
        description="Azure AI Vision endpoint URL",
        alias="AZURE_VISION_ENDPOINT",
    )

    # ===========================================
    # Azure Blob Storage
    # ===========================================
    azure_storage_connection_string: Optional[str] = Field(
        default=None,
        description="Azure Storage connection string",
        alias="AZURE_STORAGE_CONNECTION_STRING",
    )
    azure_storage_container: str = Field(
        default="health-media-uploads",
        description="Azure Storage container name",
        alias="AZURE_STORAGE_CONTAINER",
    )

    # ===========================================
    # Rate Limiting (Azure Free Tier Protection)
    # ===========================================
    rate_limit_enabled: bool = Field(
        default=True,
        description="Enable rate limiting for Azure protection",
        alias="RATE_LIMIT_ENABLED",
    )
    max_text_requests_per_day: int = Field(
        default=160,  # ~5000/month / 31 days
        description="Maximum Text Analytics requests per day",
        alias="MAX_TEXT_REQUESTS_PER_DAY",
    )
    max_speech_minutes_per_day: int = Field(
        default=10,  # ~300/month / 30 days
        description="Maximum Speech Services minutes per day",
        alias="MAX_SPEECH_MINUTES_PER_DAY",
    )
    max_vision_requests_per_day: int = Field(
        default=160,  # ~5000/month / 31 days
        description="Maximum Vision requests per day",
        alias="MAX_VISION_REQUESTS_PER_DAY",
    )

    # ===========================================
    # Database Settings
    # ===========================================
    database_url: str = Field(
        default="sqlite+aiosqlite:///./health_analysis.db",
        description="Database connection URL",
        alias="DATABASE_URL",
    )

    # ===========================================
    # Redis Settings (Optional)
    # ===========================================
    redis_url: str = Field(
        default="redis://localhost:6379/0",
        description="Redis connection URL",
        alias="REDIS_URL",
    )
    redis_enabled: bool = Field(
        default=False,
        description="Enable Redis for distributed rate limiting",
        alias="REDIS_ENABLED",
    )

    # ===========================================
    # File Upload Settings
    # ===========================================
    max_upload_size_mb: int = Field(
        default=50,
        description="Maximum upload file size in MB",
        alias="MAX_UPLOAD_SIZE_MB",
    )
    allowed_image_extensions: str = Field(
        default="jpg,jpeg,png",
        description="Comma-separated list of allowed image extensions",
        alias="ALLOWED_IMAGE_EXTENSIONS",
    )
    allowed_audio_extensions: str = Field(
        default="wav,mp3,ogg,m4a",
        description="Comma-separated list of allowed audio extensions",
        alias="ALLOWED_AUDIO_EXTENSIONS",
    )
    allowed_video_extensions: str = Field(
        default="mp4,avi,mov",
        description="Comma-separated list of allowed video extensions",
        alias="ALLOWED_VIDEO_EXTENSIONS",
    )
    upload_timeout_seconds: int = Field(
        default=300,
        description="Upload timeout in seconds",
        alias="UPLOAD_TIMEOUT_SECONDS",
    )

    # ===========================================
    # LGPD Compliance Settings
    # ===========================================
    data_retention_days: int = Field(
        default=30,
        description="Number of days to retain data before deletion",
        alias="DATA_RETENTION_DAYS",
    )
    anonymize_pii: bool = Field(
        default=True,
        description="Anonymize personally identifiable information",
        alias="ANONYMIZE_PII",
    )
    consent_required: bool = Field(
        default=True,
        description="Require explicit consent for data processing",
        alias="CONSENT_REQUIRED",
    )

    # ===========================================
    # Validators
    # ===========================================
    @field_validator("azure_text_endpoint", "azure_vision_endpoint")
    @classmethod
    def validate_azure_endpoint(cls, v: Optional[str]) -> Optional[str]:
        """Ensure Azure endpoint URLs are valid."""
        if v is None:
            return v
        if not v.startswith("https://"):
            raise ValueError("Azure endpoint must use HTTPS")
        if not v.endswith("/"):
            v = v + "/"
        return v

    @field_validator("secret_key")
    @classmethod
    def validate_secret_key(cls, v: str, info) -> str:
        """Warn if default secret key is used in production."""
        values = info.data
        if values.get("environment") == "production" and v == "change-me-in-production":
            raise ValueError("Must change default secret_key in production")
        return v

    @model_validator(mode="after")
    def validate_azure_credentials(self):
        """Validate Azure credentials are provided in production."""
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
                    f"Missing required Azure credentials in production: {', '.join(missing)}"
                )
        return self

    # ===========================================
    # Properties
    # ===========================================
    @property
    def max_upload_size_bytes(self) -> int:
        """Return max upload size in bytes."""
        return self.max_upload_size_mb * 1024 * 1024

    @property
    def allowed_image_extensions_list(self) -> list[str]:
        """Return list of allowed image extensions."""
        return [ext.strip().lower() for ext in self.allowed_image_extensions.split(",")]

    @property
    def allowed_audio_extensions_list(self) -> list[str]:
        """Return list of allowed audio extensions."""
        return [ext.strip().lower() for ext in self.allowed_audio_extensions.split(",")]

    @property
    def allowed_video_extensions_list(self) -> list[str]:
        """Return list of allowed video extensions."""
        return [ext.strip().lower() for ext in self.allowed_video_extensions.split(",")]


@lru_cache()
def get_settings() -> Settings:
    """Get cached settings instance.

    Uses lru_cache to avoid reloading settings on every call.
    """
    return Settings()


# Global settings instance for convenience
settings = get_settings()
