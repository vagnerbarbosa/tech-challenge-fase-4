"""Schemas Pydantic para a API de Análise Multimodal de Saúde."""

from datetime import datetime

from pydantic import BaseModel, Field, field_validator


class AnalysisMetadata(BaseModel):
    """Metadados para requisições de análise."""

    correlation_id: str = Field(..., description="ID único de correlação para rastreamento")
    timestamp: datetime = Field(default_factory=datetime.utcnow, description="Timestamp da requisição")
    tempo_processamento_ms: int = Field(..., description="Tempo de processamento em milissegundos")
    cache_hit: bool = Field(default=False, description="Se o resultado veio do cache")
    azure_calls: int = Field(default=0, description="Número de chamadas à API Azure realizadas")


class TextAnalysisRequest(BaseModel):
    """Modelo de requisição para o endpoint de análise de texto."""

    model_config = {
        "json_schema_extra": {
            "example": {
                "texto": "Estou me sentindo muito ansiosa e com medo quando ele chega em casa",
                "tipo": "diario",
                "patient_id": "uuid-anonimo-123",
            }
        }
    }

    texto: str = Field(
        ...,
        min_length=10,
        max_length=5000,
        description="Texto para análise (10-5000 caracteres)",
    )
    tipo: str | None = Field(
        default="geral",
        pattern="^(diario|prontuario|relato|geral)$",
        description="Tipo de texto: diario, prontuario, relato, ou geral",
    )
    patient_id: str | None = Field(
        default=None,
        description="ID anônimo do paciente (formato UUID recomendado)",
    )

    @field_validator("texto", mode="after")
    @classmethod
    def validate_texto_not_empty(cls, v: str) -> str:
        """Valida que o texto não está vazio ou apenas com espaços."""
        if not v.strip():
            raise ValueError("Texto não pode estar vazio ou conter apenas espaços")
        return v.strip()


class TextAnalysisResponse(BaseModel):
    """Modelo de resposta para o endpoint de análise de texto."""

    model_config = {
        "json_schema_extra": {
            "example": {
                "sentimento": "negativo",
                "score": -0.85,
                "risco_violencia": "alto",
                "risco_saude_mental": "alto",
                "palavras_chave": ["ansiosa", "medo", "casa"],
                "indicadores": ["ansiedade", "medo"],
                "metadata": {
                    "correlation_id": "abc-123",
                    "timestamp": "2026-04-11T14:30:00Z",
                    "tempo_processamento_ms": 450,
                    "cache_hit": False,
                    "azure_calls": 1,
                },
            }
        }
    }

    sentimento: str = Field(
        ...,
        pattern="^(positivo|negativo|neutro|misto)$",
        description="Classificação de sentimento",
    )
    score: float = Field(
        ...,
        ge=-1.0,
        le=1.0,
        description="Score de sentimento de -1.0 (negativo) a 1.0 (positivo)",
    )
    risco_violencia: str = Field(
        ...,
        pattern="^(baixo|medio|alto)$",
        description="Nível de risco de violência - CAMPO OBRIGATÓRIO",
    )
    risco_saude_mental: str = Field(
        ...,
        pattern="^(baixo|medio|alto)$",
        description="Nível de risco de saúde mental - CAMPO OBRIGATÓRIO",
    )
    palavras_chave: list[str] = Field(
        default_factory=list,
        description="Palavras-chave extraídas do texto",
    )
    indicadores: list[str] = Field(
        default_factory=list,
        description="Palavras indicadoras de risco encontradas no texto",
    )
    metadata: AnalysisMetadata = Field(
        ...,
        description="Metadados da análise",
    )
