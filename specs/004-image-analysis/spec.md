# Feature Specification: Análise de Imagem/Vídeo

**Feature Branch**: `[004-image-analysis]`
**Created**: 2026-04-11
**Status**: Draft
**Input**: User description: "Implementar endpoint de análise de imagem usando Azure AI Vision"

---

## User Scenarios & Testing

### User Story 1 - Análise de Imagem (Priority: P1)

Como profissional de saúde, quero submeter fotos de consultas para análise de expressões faciais.

**Why this priority**: Análise de imagem é uma das 3 modalidades obrigatórias do projeto.

**Independent Test**: POST `/analyze/image` retorna análise de emoções mesmo sem outras modalidades.

**Acceptance Scenarios**:

1. **Given** imagem de rosto humano, **When** submeto ao endpoint, **Then** recebo emoção_principal identificada
2. **Given** expressão de tristeza/medo, **When** processada, **Then** identifica risco_saude_mental adequado
3. **Given** imagem sem rosto, **When** submetida, **Then** retorna erro 400 com mensagem clara
4. **Given** formato não suportado, **When** submetido, **Then** retorna erro 400

### User Story 2 - Processamento de Vídeo (Priority: P1)

Como profissional de saúde, quero submeter vídeos curtos de consultas para análise de expressões ao longo do tempo.

**Why this priority**: Vídeos fornecem contexto temporal importante para análise comportamental.

**Independent Test**: POST `/analyze/image` com MP4 extrai frames e analisa.

**Acceptance Scenarios**:

1. **Given** vídeo MP4 (max 30s), **When** submeto ao endpoint, **Then** extrai frames automaticamente
2. **Given** frames extraídos, **When** processados, **Then** combina resultados de múltiplos frames
3. **Given** vídeo maior que 30s, **When** submetido, **Then** retorna erro 400

### User Story 3 - Detecção de Sinais de Alerta (Priority: P2)

Como profissional de saúde, quero que o sistema detecte possíveis sinais físicos de violência.

**Why this priority**: Marcas ou hematomas podem ser indicadores importantes (com cautela para falsos positivos).

**Independent Test**: Response inclui sinais_alertas quando detectados.

**Acceptance Scenarios**:

1. **Given** imagem com possíveis marcas, **When** processada, **Then** inclui em sinais_alertas (com baixa confiança)
2. **Given** imagem sem anomalias, **When** processada, **Then** sinais_alertas é array vazio

---

## Requirements

### Functional Requirements

- **FR-001**: Endpoint POST `/analyze/image` disponível
- **FR-002**: Aceita imagens JPEG, PNG (max: 20MB)
- **FR-003**: Aceita vídeos MP4 (max: 30s, max: 50MB)
- **FR-004**: Extrai frames de vídeo automaticamente (a cada 5s)
- **FR-005**: Integra com Azure AI Vision para análise facial
- **FR-006**: Retorna obrigatoriamente: risco_violencia, risco_saude_mental
- **FR-007**: Retorna: emoção_principal, confiança, expressoes, sinais_alertas
- **FR-008**: Combina resultados de múltiplos frames para vídeos
- **FR-009**: Valida formato, tamanho e conteúdo (deve ter rosto)

### Key Entities

- **ImageAnalysisRequest**: multipart/form-data com imagem, tipo, patient_id
- **ImageAnalysisResponse**: { emoção_principal, confiança, expressoes, sinais_alertas, risco_violencia, risco_saude_mental, metadata }
- **VideoAnalysisResponse**: Extensão com analise_video (frames_analisados, emocoes_por_frame)
- **ImageAnalysisService**: Processamento de imagem/vídeo
- **VideoFrameExtractor**: Extração de frames usando OpenCV

---

## Success Criteria

- **SC-001**: Latência imagem < 5s
- **SC-002**: Latência vídeo < 15s (30s de vídeo)
- **SC-003**: Precisão detecção emoção > 75%
- **SC-004**: Extração de frames funciona corretamente
- **SC-005**: Campos obrigatórios sempre presentes

---

## Assumptions

- Azure AI Vision credenciais disponíveis
- Free Tier: 5.000 transactions/mês
- OpenCV (cv2) disponível no container
- FFmpeg para processamento de vídeo
- Imagens devem conter rosto humano
- Não armazenamos imagens originais após processamento

---

## Technical Notes

### Azure AI Vision SDK
- Pacote: `azure-ai-vision-imageanalysis>=1.0.0`
- **IMPORTANTE**: SDK antigo `azure-cognitiveservices-vision-computervision` foi deprecated em nov/2024

### Processamento de Vídeo
- Extrair frames a cada 5 segundos
- Analisar cada frame com Azure AI Vision
- Combinar resultados (votação ou média)
- Deletar frames temporários após análise

### OpenCV
- Pacote: `opencv-python-headless` (versão headless para containers)
- Funções: VideoCapture, imwrite, frame extraction

### Limitações Azure Free Tier
- Apenas análise de imagem (não vídeo direto)
- Máximo 5.000 chamadas/mês
- Rate limiting necessário

---

## Melhores Práticas de Implementação

### Padrão Singleton para Cliente Azure AI Vision

```python
from azure.ai.vision.imageanalysis import ImageAnalysisClient
from azure.core.credentials import AzureKeyCredential
from functools import lru_cache

@lru_cache()
def get_vision_client():
    """Cliente singleton para Azure AI Vision"""
    return ImageAnalysisClient(
        endpoint=settings.azure_vision_endpoint,
        credential=AzureKeyCredential(settings.azure_vision_key)
    )

# Uso com lifespan (FastAPI moderno)
from contextlib import asynccontextmanager

@asynccontextmanager
async def lifespan(app: FastAPI):
    app.state.vision_client = get_vision_client()
    yield
    # Cleanup não necessário para ImageAnalysisClient

app = FastAPI(lifespan=lifespan)
```

### Extração de Frames com OpenCV

```python
import cv2
from pathlib import Path
from typing import List
import tempfile

class VideoFrameExtractor:
    """Extrai frames de vídeos para análise com Azure AI Vision"""

    def __init__(self, interval_seconds: int = 5):
        self.interval = interval_seconds

    async def extract_frames(self, video_path: Path) -> List[Path]:
        """
        Extrai frames do vídeo a cada N segundos
        Retorna: Lista de caminhos dos frames extraídos
        """
        frames = []
        cap = cv2.VideoCapture(str(video_path))

        if not cap.isOpened():
            raise ValueError("Não foi possível abrir o vídeo")

        fps = cap.get(cv2.CAP_PROP_FPS)
        total_frames = cap.get(cv2.CAP_PROP_FRAME_COUNT)
        duration = total_frames / fps if fps > 0 else 0

        # Valida duração máxima (30s)
        if duration > 30:
            cap.release()
            raise ValueError("Vídeo deve ter no máximo 30 segundos")

        frame_interval = int(fps * self.interval)
        frame_count = 0

        while True:
            ret, frame = cap.read()
            if not ret:
                break

            if frame_count % frame_interval == 0:
                with tempfile.NamedTemporaryFile(
                    suffix='.jpg',
                    delete=False
                ) as tmp:
                    cv2.imwrite(tmp.name, frame)
                    frames.append(Path(tmp.name))

            frame_count += 1

        cap.release()
        return frames
```

### Validação de Imagem com Magic Numbers

```python
import magic
from fastapi import UploadFile, HTTPException

ALLOWED_IMAGE_TYPES = {
    'image/jpeg': '.jpg',
    'image/png': '.png',
    'image/jpg': '.jpg'
}

ALLOWED_VIDEO_TYPES = {
    'video/mp4': '.mp4'
}

async def validate_media_file(file: UploadFile, is_video: bool = False):
    # 1. Validar extensão
    ext = Path(file.filename).suffix.lower()
    if is_video and ext != '.mp4':
        raise HTTPException(400, "Vídeo deve ser MP4")
    elif not is_video and ext not in ['.jpg', '.jpeg', '.png']:
        raise HTTPException(400, "Imagem deve ser JPEG ou PNG")

    # 2. Verificar magic numbers
    content = await file.read(2048)
    await file.seek(0)

    mime = magic.from_buffer(content, mime=True)

    if is_video:
        if mime not in ALLOWED_VIDEO_TYPES:
            raise HTTPException(400, f"Tipo de vídeo não suportado: {mime}")
    else:
        if mime not in ALLOWED_IMAGE_TYPES:
            raise HTTPException(400, f"Tipo de imagem não suportado: {mime}")

    # 3. Verificar tamanho
    file_size = len(content)
    max_size = 50 * 1024 * 1024 if is_video else 20 * 1024 * 1024
    if file_size > max_size:
        raise HTTPException(400, "Arquivo excede tamanho máximo")
```

### Análise de Imagem com Timeout

```python
import asyncio
from azure.core.exceptions import HttpResponseError

async def analyze_image_with_timeout(
    image_path: Path,
    timeout_secs: int = 30
) -> dict:
    """Analisa imagem com timeout"""
    client = get_vision_client()

    try:
        with open(image_path, 'rb') as image_file:
            result = await asyncio.wait_for(
                asyncio.to_thread(
                    client.analyze,
                    image_data=image_file.read(),
                    visual_features=["FACE", "EMOTION"]
                ),
                timeout=timeout_secs
            )

        return {
            "emoção_principal": result.emotions[0].type if result.emotions else "neutro",
            "confiança": result.emotions[0].confidence if result.emotions else 0.0,
            "expressoes": result.faces if result.faces else []
        }

    except asyncio.TimeoutError:
        raise HTTPException(504, "Tempo limite excedido para análise")
    except HttpResponseError as e:
        if e.status_code == 429:
            raise QuotaExceededError("Azure Vision quota exceeded")
        raise
```

### Combinação de Resultados de Vídeo

```python
from typing import List, Dict
from collections import Counter

class VideoResultCombiner:
    """Combina resultados de múltiplos frames de vídeo"""

    def combine_emotions(self, frame_results: List[Dict]) -> Dict:
        """
        Combina emoções de múltiplos frames usando votação ponderada
        """
        if not frame_results:
            return {"emoção_principal": "neutro", "confiança": 0.0}

        # Extrai emoções e confianças
        emotions = [r["emoção_principal"] for r in frame_results]
        confidences = [r["confiança"] for r in frame_results]

        # Votação ponderada por confiança
        weighted_votes = Counter()
        for emotion, conf in zip(emotions, confidences):
            weighted_votes[emotion] += conf

        # Emoção mais frequente
        dominant_emotion = weighted_votes.most_common(1)[0][0]
        avg_confidence = sum(confidences) / len(confidences)

        # União de expressões únicas
        all_expressions = set()
        for r in frame_results:
            all_expressions.update(r.get("expressoes", []))

        return {
            "emoção_principal": dominant_emotion,
            "confiança": avg_confidence,
            "expressoes": list(all_expressions),
            "frames_analisados": len(frame_results)
        }
```

### Limpeza de Recursos Temporários

```python
import atexit
from pathlib import Path
from typing import List

class TempResourceManager:
    """Gerencia recursos temporários (frames, uploads)"""

    def __init__(self):
        self.temp_files: List[Path] = []
        atexit.register(self.cleanup_all)

    def add(self, file_path: Path):
        self.temp_files.append(file_path)

    def cleanup(self, file_path: Path):
        try:
            if file_path.exists():
                file_path.unlink()
            self.temp_files.remove(file_path)
        except (FileNotFoundError, ValueError):
            pass

    def cleanup_all(self):
        for file_path in self.temp_files[:]:
            self.cleanup(file_path)

# Uso no serviço
async def analyze_video(video_path: Path) -> dict:
    temp_manager = TempResourceManager()
    try:
        # Extrai frames
        frames = await extractor.extract_frames(video_path)
        for frame in frames:
            temp_manager.add(frame)

        # Analisa cada frame
        results = []
        for frame_path in frames:
            result = await analyze_image(frame_path)
            results.append(result)

        # Combina resultados
        combined = combiner.combine_emotions(results)
        return combined

    finally:
        # Limpa frames temporários
        for frame in frames:
            temp_manager.cleanup(frame)
```

### Logging de Métricas

```python
from time import perf_counter
import structlog

logger = structlog.get_logger()

async def analyze_image_with_metrics(image_path: Path):
    start = perf_counter()
    logger.info("image_analysis_started", file=str(image_path))

    try:
        result = await vision_service.analyze(image_path)
        duration = perf_counter() - start

        logger.info(
            "image_analysis_completed",
            duration_seconds=duration,
            emotion=result.emoção_principal,
            confidence=result.confiança,
            risk_level=result.risco_violencia
        )
        return result
    except Exception as e:
        logger.error("image_analysis_failed", error=str(e))
        raise
```

---

## Referências

- Documentação completa: `docs/technical/best-practices.md` (integrado)
- [Azure AI Vision](https://learn.microsoft.com/azure/ai-services/computer-vision/)
- [OpenCV Python](https://docs.opencv.org/4.x/d6/d00/tutorial_py_root.html)
- [python-magic](https://github.com/ahupp/python-magic)
