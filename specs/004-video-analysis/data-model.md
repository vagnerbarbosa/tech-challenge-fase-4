# Data Model: Análise de Vídeo

**Feature**: Video Analysis com YOLOv8  
**Date**: 2026-04-19

---

## Pydantic Schemas

### VideoAnalysisRequest

```python
class VideoAnalysisRequest(BaseModel):
    """Requisição de análise de vídeo."""
    
    video: UploadFile = Field(..., description="Arquivo de vídeo (MP4, AVI, MOV)")
    tipo: str = Field(default="consulta", pattern="^(consulta|procedimento|exame)$")
    patient_id: str | None = Field(default=None, description="ID anônimo do paciente (UUID)")
    extract_fps: float = Field(default=1.0, ge=0.2, le=5.0, description="Taxa de extração de frames")
```

### VideoAnalysisResponse

```python
class VideoAnalysisResponse(BaseModel):
    """Resposta da análise de vídeo."""
    
    # Campos obrigatórios (mesmo padrão de texto e áudio)
    risco_violencia: str = Field(..., pattern="^(baixo|medio|alto)$")
    risco_saude_mental: str = Field(..., pattern="^(baixo|medio|alto)$")
    
    # Detecções do vídeo
    detecoes: list[Detection] = Field(default_factory=list)
    alertas: list[Alert] = Field(default_factory=list)
    
    # Metadados
    metadata: VideoAnalysisMetadata

class Detection(BaseModel):
    """Objeto detectado no vídeo."""
    
    classe: str = Field(..., description="Classe do objeto (COCO)")
    confianca: float = Field(..., ge=0.0, le=1.0)
    bbox: BoundingBox
    frame: int = Field(..., ge=0)
    timestamp: float = Field(..., ge=0.0)  # segundos no vídeo

class BoundingBox(BaseModel):
    """Bounding box em coordenadas absolutas."""
    
    x: float  # canto superior esquerdo
    y: float
    w: float  # width
    h: float  # height

class Alert(BaseModel):
    """Alerta de risco detectado."""
    
    tipo: str = Field(..., description="Tipo de alerta")
    severidade: str = Field(..., pattern="^(baixa|media|alta)$")
    descricao: str
    frame_referencia: int

class VideoAnalysisMetadata(BaseModel):
    """Metadados do processamento."""
    
    correlation_id: str
    timestamp: datetime
    tempo_processamento_ms: int
    cache_hit: bool
    frames_analisados: int = Field(..., ge=0)
    duracao_video_segundos: float = Field(..., ge=0.0)
    modelo: str = Field(default="yolov8n")
    local_processing: bool = Field(default=True)  # Indica YOLOv8 local
```

---

## Internal Data Structures

### FrameInfo (para processamento interno)

```python
@dataclass
class FrameInfo:
    """Informações de um frame extraído."""
    
    frame_number: int
    timestamp: float  # segundos no vídeo original
    path: Path  # caminho do arquivo temporário
```

### VideoProcessingResult

```python
@dataclass
class VideoProcessingResult:
    """Resultado do processamento de vídeo."""
    
    detections: list[dict]  # Lista de detecções YOLOv8
    frames_processed: int
    video_duration: float
    processing_time_ms: int
```

---

## Relationships

```
VideoAnalysisRequest
    ├── video: UploadFile
    ├── tipo: str
    ├── patient_id: str | None
    └── extract_fps: float

VideoAnalysisResponse
    ├── risco_violencia: str (obrigatório)
    ├── risco_saude_mental: str (obrigatório)
    ├── detecoes: Detection[]
    │   └── Detection
    │       ├── classe: str
    │       ├── confianca: float
    │       ├── bbox: BoundingBox
    │       ├── frame: int
    │       └── timestamp: float
    ├── alertas: Alert[]
    │   └── Alert
    │       ├── tipo: str
    │       ├── severidade: str
    │       ├── descricao: str
    │       └── frame_referencia: int
    └── metadata: VideoAnalysisMetadata
        ├── correlation_id: str
        ├── timestamp: datetime
        ├── tempo_processamento_ms: int
        ├── cache_hit: bool
        ├── frames_analisados: int
        ├── duracao_video_segundos: float
        ├── modelo: str
        └── local_processing: bool
```

---

## Validation Rules

1. **Arquivo**: Deve ser MP4, AVI, ou MOV (magic number + extensão)
2. **Tamanho**: Máximo 50MB (config.MAX_UPLOAD_SIZE_MB)
3. **Duração**: Máximo 120 segundos (2 minutos)
4. **FPS de extração**: Entre 0.2 e 5.0 (padrão: 1.0, adaptativo)

---

## State Transitions

```
[Upload Request]
      ↓
[Validar arquivo]
      ↓ (erro: 400/413)
[Extrair frames]
      ↓ (erro: 500)
[Processar com YOLOv8]
      ↓ (erro: 500)
[Detectar sangramento]
      ↓
[Calcular riscos]
      ↓
[Montar resposta]
      ↓
[Retornar 200]
```

---

## Integration Points

### Com schemas existentes

O `VideoAnalysisResponse` deve ser compatível com fusão multimodal:

```python
# Em fusão multimodal, teremos:
class MultimodalResponse(BaseModel):
    texto: TextAnalysisResponse | None
    audio: AudioAnalysisResponse | None
    video: VideoAnalysisResponse | None
    fusao: FusionResult
```

### Cache Key

```python
def generate_cache_key(video_path: Path, patient_id: str | None) -> str:
    stats = video_path.stat()
    content = f"{video_path.name}:{stats.st_size}:{stats.st_mtime}:{patient_id or ''}"
    return hashlib.sha256(content.encode()).hexdigest()[:16]
```
