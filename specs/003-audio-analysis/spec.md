# Feature Specification: Análise de Áudio

**Feature Branch**: `[003-audio-analysis]`
**Created**: 2026-04-11
**Status**: Draft
**Input**: User description: "Implementar endpoint de análise de áudio usando Azure Speech Services"

---

## Clarifications

### Session 2026-04-12

- **Q**: Fallback quando Azure Speech falha → **A**: Retornar erro HTTP 503 quando Azure indisponível (requer Azure)
- **Q**: Timeout de processamento → **A**: 30 segundos por requisição
- **Q**: Limite de tamanho de arquivo → **A**: Hard limit - rejeitar arquivos >50MB com HTTP 400
- **Q**: Storage temporário → **A**: Local filesystem (/tmp) com cleanup automático
- **Q**: Desenvolvimento sem Azure → **A**: Modo mock com transcrição simulada + aviso no log

---

## User Scenarios & Testing

### User Story 1 - Speech-to-Text (Priority: P1)

Como profissional de saúde, quero submeter gravações de consultas para transcrição automática.

**Why this priority**: Análise de áudio é uma das 3 modalidades obrigatórias do projeto.

**Independent Test**: POST `/analyze/audio` retorna transcrição mesmo sem outras modalidades.

**Acceptance Scenarios**:

1. **Given** arquivo de áudio em português, **When** submeto ao endpoint, **Then** recebo transcrição em texto
2. **Given** áudio com voz tremida/hesitante, **When** processado, **Then** detecta características na voz
3. **Given** arquivo maior que 50MB, **When** submetido, **Then** retorna erro 400
4. **Given** formato não suportado, **When** submetido, **Then** retorna erro 400 com formatos aceitos

### User Story 2 - Análise de Padrões de Fala (Priority: P1)

Como profissional de saúde, quero identificar pausas suspeitas e voz tremida como indicadores de risco.

**Why this priority**: Padrões de fala são indicadores importantes de violência doméstica e saúde mental.

**Independent Test**: Response inclui métricas de análise prosódica.

**Acceptance Scenarios**:

1. **Given** áudio com silêncios longos, **When** processado, **Then** conta pausas_suspeitas
2. **Given** áudio com variação de tom, **When** processado, **Then** identifica entonação hesitante
3. **Given** áudio com tremor na voz, **When** processado, **Then** flag voz_tremida = true

### User Story 3 - Gestão de Arquivos Temporários (Priority: P2)

Como sistema LGPD-compliant, quero que arquivos de áudio sejam deletados após processamento.

**Why this priority**: Conformidade com LGPD é requisito obrigatório (RNF05).

**Independent Test**: Verificar se arquivos são removidos do storage temporário.

**Acceptance Scenarios**:

1. **Given** arquivo de áudio enviado, **When** processamento completa, **Then** arquivo é deletado em até 24h
2. **Given** falha no processamento, **When** erro ocorre, **Then** arquivo ainda é deletado

---

## Requirements

### Functional Requirements

- **FR-001**: Endpoint POST `/analyze/audio` disponível
- **FR-002**: Aceita arquivos WAV, MP3, OGG (max: 50MB)
- **FR-003**: Integra com Azure Speech Services para transcrição
- **FR-004**: Retorna obrigatoriamente: risco_violencia, risco_saude_mental
- **FR-005**: Retorna: transcrição, idioma_detectado, sentimento, entonação, voz_tremida, pausas_suspeitas
- **FR-006**: Armazena arquivo temporariamente em filesystem local (/tmp) durante processamento
- **FR-007**: Deleta arquivo após processamento (LGPD)
- **FR-008**: Valida formato e tamanho do arquivo

### Key Entities

- **AudioAnalysisRequest**: multipart/form-data com audio, tipo_consulta, patient_id
- **AudioAnalysisResponse**: { transcricao, idioma_detectado, sentimento, entonação, voz_tremida, pausas_suspeitas, duracao_segundos, risco_violencia, risco_saude_mental, metadata }
- **AudioAnalysisService**: Upload, processamento, análise

---

## Success Criteria

- **SC-001**: Latência < 10s para arquivo de 1 minuto
- **SC-002**: Precisão de transcrição > 85% (pt-BR)
- **SC-003**: Arquivos temporários deletados após processamento
- **SC-004**: Campos obrigatórios sempre presentes

---

## Assumptions

- Azure Speech Services credenciais disponíveis
- Free Tier: 5 horas/mês (suficiente para desenvolvimento)
- Áudio em português do Brasil
- FFmpeg disponível no container para pré-processamento
- Não armazenamos áudio original após processamento

---

## Technical Notes

### Azure Speech SDK
- Pacote: `azure-cognitiveservices-speech>=1.48.0`
- Requer: Speech SDK nativo (instalado via apt no Dockerfile)

### Processamento de Áudio
- Extrair features prosódicas: pitch, energia, pausas
- Detectar voz tremida via variação de pitch
- Detectar pausas via análise de silêncio

### Storage Temporário
- ~~Azure Blob Storage~~ Local filesystem (`/tmp`)
- TTL: Imediato (cleanup após processamento)
- Anonimização: patient_id hash (SHA256) no prefixo do nome do arquivo
- Cleanup garantido via `try/finally` + `atexit` handler

---

## Melhores Práticas de Implementação

### Padrão Singleton para Cliente Azure Speech

```python
from azure.cognitiveservices.speech import SpeechConfig, SpeechRecognizer
from functools import lru_cache

@lru_cache()
def get_speech_config():
    """Config singleton para Azure Speech"""
    return SpeechConfig(
        subscription=settings.azure_speech_key,
        region=settings.azure_speech_region
    )

# Uso com lifespan (FastAPI moderno)
from contextlib import asynccontextmanager

@asynccontextmanager
async def lifespan(app: FastAPI):
    app.state.speech_config = get_speech_config()
    yield
    # Cleanup não necessário para SpeechConfig

app = FastAPI(lifespan=lifespan)
```

### Validação de Uploads com Magic Numbers

```python
import magic
from fastapi import UploadFile, HTTPException

ALLOWED_AUDIO_TYPES = {
    'audio/wav': '.wav',
    'audio/mpeg': '.mp3',
    'audio/ogg': '.ogg',
    'audio/x-wav': '.wav'
}

async def validate_audio_file(file: UploadFile):
    # 1. Validar extensão
    ext = Path(file.filename).suffix.lower()
    if ext not in ['.wav', '.mp3', '.ogg']:
        raise HTTPException(400, "Extensão não permitida")

    # 2. Verificar magic numbers (conteúdo real)
    content = await file.read(2048)  # Primeiros 2KB
    await file.seek(0)

    mime = magic.from_buffer(content, mime=True)
    if mime not in ALLOWED_AUDIO_TYPES:
        raise HTTPException(400, f"Tipo de arquivo não suportado: {mime}")

    # 3. Verificar tamanho
    file_size = len(content)
    if file_size > 50 * 1024 * 1024:  # 50MB
        raise HTTPException(400, "Arquivo muito grande")
```

### Processamento com Timeout e Retry

```python
import asyncio
from azure.core.exceptions import HttpResponseError

async def transcribe_with_timeout(
    audio_path: str,
    timeout_secs: int = 30
) -> str:
    """Transcreve áudio com timeout e retry"""
    speech_config = get_speech_config()
    audio_config = AudioConfig(filename=audio_path)
    recognizer = SpeechRecognizer(speech_config, audio_config)

    try:
        # Executa com timeout
        result = await asyncio.wait_for(
            asyncio.to_thread(recognizer.recognize_once_async),
            timeout=timeout_secs
        )

        if result.reason == ResultReason.RecognizedSpeech:
            return result.text
        elif result.reason == ResultReason.NoMatch:
            raise ValueError("Nenhuma fala detectada no áudio")
        else:
            raise AzureServiceError(f"Erro na transcrição: {result.reason}")

    except asyncio.TimeoutError:
        raise HTTPException(504, "Tempo limite excedido para transcrição")
    except HttpResponseError as e:
        if e.status_code == 429:
            raise QuotaExceededError("Azure Speech quota exceeded")
        raise
```

### Limpeza de Arquivos Temporários (LGPD)

```python
import tempfile
from pathlib import Path
import atexit

class TempFileManager:
    """Gerencia arquivos temporários com auto-cleanup"""

    def __init__(self):
        self.temp_files = []
        atexit.register(self.cleanup_all)

    async def save_temp(self, upload: UploadFile) -> Path:
        """Salva arquivo temporariamente"""
        with tempfile.NamedTemporaryFile(
            delete=False,
            suffix=Path(upload.filename).suffix
        ) as tmp:
            content = await upload.read()
            tmp.write(content)
            self.temp_files.append(tmp.name)
            return Path(tmp.name)

    def cleanup(self, file_path: Path):
        """Remove arquivo específico"""
        try:
            file_path.unlink()
            self.temp_files.remove(str(file_path))
        except FileNotFoundError:
            pass

    def cleanup_all(self):
        """Remove todos os arquivos temporários"""
        for file_path in self.temp_files:
            try:
                Path(file_path).unlink()
            except FileNotFoundError:
                pass

# Uso
@app.post("/analyze/audio")
async def analyze_audio(audio: UploadFile):
    temp_manager = TempFileManager()
    try:
        temp_path = await temp_manager.save_temp(audio)
        result = await audio_service.analyze(temp_path)
        return result
    finally:
        temp_manager.cleanup(temp_path)
```

### Logging de Métricas

```python
from time import perf_counter
import structlog

logger = structlog.get_logger()

async def analyze_with_metrics(audio_path: Path):
    start = perf_counter()
    logger.info("audio_analysis_started", file=str(audio_path))

    try:
        result = await process_audio(audio_path)
        duration = perf_counter() - start

        logger.info(
            "audio_analysis_completed",
            duration_seconds=duration,
            transcription_length=len(result.transcription),
            risk_level=result.risco_violencia
        )
        return result
    except Exception as e:
        logger.error("audio_analysis_failed", error=str(e))
        raise
```

### Extração de Features Prosódicas

```python
import librosa
import numpy as np

class ProsodicFeatureExtractor:
    """Extrai features prosódicas para análise de risco"""

    def __init__(self):
        self.sample_rate = 16000

    async def extract(self, audio_path: Path) -> dict:
        # Carrega áudio
        y, sr = librosa.load(str(audio_path), sr=self.sample_rate)

        # Extrai pitch (F0)
        pitches, magnitudes = librosa.piptrack(y=y, sr=sr)
        pitch_values = pitches[magnitudes > np.median(magnitudes)]

        # Variação de pitch (tremor na voz)
        pitch_variation = np.std(pitch_values) if len(pitch_values) > 0 else 0

        # Energia (volume)
        rms = librosa.feature.rms(y=y)[0]
        energy_variation = np.std(rms)

        # Pausas (silêncios)
        intervals = librosa.effects.split(y, top_db=20)
        pauses = len(intervals) - 1  # Número de pausas

        return {
            "voz_tremida": pitch_variation > 50,  # Threshold
            "pausas_suspeitas": pauses,
            "entonação": "hesitante" if energy_variation > 0.1 else "normal"
        }
```

---

## Referências

- Documentação completa: `docs/technical/context7-best-practices.md` (integrado)
- [Azure AI Speech](https://learn.microsoft.com/azure/ai-services/speech-service/)
- [librosa Documentation](https://librosa.org/doc/latest/)
- [python-magic](https://github.com/ahupp/python-magic)
