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


class AudioAnalysisResponse(BaseModel):
    """Modelo de resposta para o endpoint de análise de áudio."""

    model_config = {
        "json_schema_extra": {
            "example": {
                "transcricao": "Doutor, eu não sei se posso contar isso...",
                "idioma_detectado": "pt-BR",
                "sentimento": "negativo",
                "entonação": "hesitante",
                "voz_tremida": True,
                "pausas_suspeitas": 3,
                "duracao_segundos": 45.2,
                "risco_violencia": "medio",
                "risco_saude_mental": "alto",
                "metadata": {
                    "correlation_id": "abc-123",
                    "timestamp": "2026-04-11T14:30:00Z",
                    "tempo_processamento_ms": 8500,
                    "cache_hit": False,
                    "azure_calls": 1,
                },
            }
        }
    }

    transcricao: str = Field(
        ...,
        description="Texto transcrito do áudio",
    )
    idioma_detectado: str = Field(
        default="pt-BR",
        description="Idioma detectado no áudio",
    )
    sentimento: str = Field(
        default="neutro",
        pattern="^(positivo|negativo|neutro|misto)$",
        description="Classificação de sentimento da transcrição",
    )
    entonação: str = Field(
        default="normal",
        pattern="^(normal|hesitante|agitado|calmo)$",
        description="Entonação detectada na fala",
    )
    voz_tremida: bool = Field(
        default=False,
        description="Indica se foi detectado tremor na voz (possível ansiedade/stress)",
    )
    pausas_suspeitas: int = Field(
        default=0,
        ge=0,
        description="Número de pausas suspeitas detectadas (silêncios longos)",
    )
    duracao_segundos: float = Field(
        ...,
        ge=0,
        description="Duração do áudio em segundos",
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
    metadata: AnalysisMetadata = Field(
        ...,
        description="Metadados da análise",
    )


# ===========================================
# Video Analysis Schemas
# ===========================================


class BoundingBox(BaseModel):
    """Bounding box em coordenadas normalizadas (0-1)."""

    x: float = Field(..., ge=0.0, le=1.0, description="Posição X do canto superior esquerdo")
    y: float = Field(..., ge=0.0, le=1.0, description="Posição Y do canto superior esquerdo")
    w: float = Field(..., ge=0.0, le=1.0, description="Largura da caixa")
    h: float = Field(..., ge=0.0, le=1.0, description="Altura da caixa")


class Detection(BaseModel):
    """Objeto detectado no vídeo."""

    classe: str = Field(..., description="Classe do objeto detectada (ex: person, scissors)")
    confianca: float = Field(..., ge=0.0, le=1.0, description="Score de confiança (0-1)")
    bbox: BoundingBox = Field(..., description="Bounding box normalizado")
    frame: int = Field(..., ge=0, description="Número do frame onde foi detectado")
    timestamp: float = Field(..., ge=0.0, description="Timestamp em segundos no vídeo")


class Alert(BaseModel):
    """Alerta de risco detectado no vídeo."""

    tipo: str = Field(..., description="Tipo de alerta (ex: sangramento_detectado)")
    severidade: str = Field(..., pattern="^(baixa|media|alta)$", description="Nível de severidade")
    descricao: str = Field(..., description="Descrição do alerta")
    frame_referencia: int = Field(..., ge=0, description="Frame de referência do alerta")


class VideoAnalysisMetadata(BaseModel):
    """Metadados específicos da análise de vídeo."""

    correlation_id: str = Field(..., description="ID único de correlação")
    timestamp: datetime = Field(default_factory=datetime.utcnow, description="Timestamp da análise")
    tempo_processamento_ms: int = Field(..., description="Tempo de processamento em ms")
    cache_hit: bool = Field(default=False, description="Se o resultado veio do cache")
    frames_analisados: int = Field(..., ge=0, description="Número de frames analisados")
    duracao_video_segundos: float = Field(..., ge=0.0, description="Duração do vídeo em segundos")
    modelo: str = Field(default="yolov8n", description="Modelo YOLO utilizado")
    local_processing: bool = Field(default=True, description="Processamento local (sem Azure)")


class VideoAnalysisResponse(BaseModel):
    """Modelo de resposta para o endpoint de análise de vídeo."""

    model_config = {
        "json_schema_extra": {
            "example": {
                "risco_violencia": "baixo",
                "risco_saude_mental": "medio",
                "detecoes": [
                    {
                        "classe": "person",
                        "confianca": 0.89,
                        "bbox": {"x": 0.1, "y": 0.2, "w": 0.3, "h": 0.5},
                        "frame": 5,
                        "timestamp": 5.0,
                    }
                ],
                "alertas": [
                    {
                        "tipo": "sangramento_detectado",
                        "severidade": "media",
                        "descricao": "Possível sangramento detectado no vídeo",
                        "frame_referencia": 12,
                    }
                ],
                "metadata": {
                    "correlation_id": "vid-abc123",
                    "timestamp": "2026-04-19T15:30:00Z",
                    "tempo_processamento_ms": 4500,
                    "cache_hit": False,
                    "frames_analisados": 24,
                    "duracao_video_segundos": 45.5,
                    "modelo": "yolov8n",
                    "local_processing": True,
                },
            }
        }
    }

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
    detecoes: list[Detection] = Field(
        default_factory=list,
        description="Lista de objetos detectados no vídeo",
    )
    alertas: list[Alert] = Field(
        default_factory=list,
        description="Alertas de risco gerados",
    )
    metadata: VideoAnalysisMetadata = Field(
        ...,
        description="Metadados da análise de vídeo",
    )
