# Implementation Plan: Análise de Áudio

**Branch**: `003-audio-analysis` | **Date**: 2026-04-12 | **Spec**: [spec.md](./spec.md)
**Input**: Feature specification from `/specs/003-audio-analysis/spec.md`

---

## Summary

Implementar endpoint POST `/analyze/audio` para transcrição e análise de áudio usando Azure Speech Services. O endpoint aceita arquivos WAV/MP3/OGG (max 50MB), extrai features prosódicas (pitch, energia, pausas) via librosa, e retorna análise de risco conforme LGPD.

---

## Technical Context

**Language/Version**: Python 3.11+  
**Primary Dependencies**: FastAPI, Azure Speech SDK (azure-cognitiveservices-speech>=1.48.0), librosa>=0.10.0, python-magic>=0.4.27  
**Storage**: Local filesystem (/tmp) - LGPD compliant  
**Testing**: pytest with pytest-asyncio, httpx for integration tests  
**Target Platform**: Linux server (Docker + Azure App Service Free Tier)  
**Project Type**: web-service  
**Performance Goals**: Latência < 10s para arquivo de 1 minuto  
**Constraints**: Timeout 30s, <50MB arquivo, Azure Free Tier 5h/mês  
**Scale/Scope**: 100-500 análises/dia (estimativa)

---

## Constitution Check

*GATE: Must pass before Phase 0 research. Re-check after Phase 1 design.*

| Principle | Compliance | Notes |
|-----------|------------|-------|
| LGPD First | ✅ Pass | Arquivos temporários em /tmp com auto-cleanup |
| Azure Free Tier Protection | ✅ Pass | Rate limiting por minutos processados |
| Campos Obrigatórios | ✅ Pass | risco_violencia, risco_saude_mental presentes |
| Qualidade de Código | ⚠️ TBD | Implementar durante tasks |
| Documentação | ✅ Pass | Spec em português, código em inglês |

---

## Research (Phase 0)

### Unknowns Resolved

1. **Azure Speech SDK Async Pattern**
   - Decision: SDK é síncrono, usar `asyncio.to_thread()`
   - Rationale: SDK não suporta async nativo
   - Pattern: Wrapper async com timeout

2. **Librosa Audio Loading**
   - Decision: Usar `librosa.load(sr=16000, mono=True)`
   - Rationale: 16kHz é padrão para speech, reduz processamento
   - Note: Requer soundfile ou ffmpeg no container

3. **Magic Numbers Validation**
   - Decision: python-magic para validação MIME real
   - Rationale: Evita spoofing de extensão
   - Implementation: Verificar magic bytes antes de salvar

4. **Temp File Cleanup**
   - Decision: Singleton TempFileManager com atexit
   - Rationale: Garante cleanup mesmo em crashes
   - LGPD: Alinhado com requisito de não armazenar dados

---

## Project Structure

### Documentation (this feature)

```text
specs/003-audio-analysis/
├── spec.md              # Feature specification
├── plan.md              # This file
├── research.md          # Phase 0 output
├── data-model.md        # Phase 1 output (schemas)
├── quickstart.md        # Phase 1 output (como usar)
├── contracts/           # API contracts (OpenAPI)
└── tasks.md             # Phase 2 output
```

### Source Code (repository root)

```text
src/
├── api/
│   └── routes/
│       └── audio.py              # Endpoint POST /analyze/audio
├── services/
│   ├── audio_analysis.py         # AudioAnalysisService
│   └── prosodic_extractor.py     # ProsodicFeatureExtractor
├── infrastructure/
│   └── azure_speech_client.py    # AzureSpeechClient
├── core/
│   └── temp_file_manager.py      # TempFileManager (LGPD)
├── models/
│   └── schemas.py                # AudioAnalysisResponse
└── utils/
    └── file_validation.py        # validate_audio_file()

tests/
├── unit/
│   ├── infrastructure/
│   │   └── test_azure_speech_client.py
│   ├── services/
│   │   ├── test_audio_analysis.py
│   │   └── test_prosodic_extractor.py
│   └── core/
│       └── test_temp_file_manager.py
└── integration/
    └── test_audio_endpoint.py
```

**Structure Decision**: Single project (FastAPI web service) conforme existente. Reutilizar estrutura atual em `src/`.

---

## Data Model

### AudioAnalysisResponse

```python
{
    "transcricao": str,              # Texto transcrito
    "idioma_detectado": str,         # "pt-BR"
    "sentimento": str,               # "positivo"|"negativo"|"neutro"|"misto"
    "entonação": str,                # "normal"|"hesitante"|"agitado"|"calmo"
    "voz_tremida": bool,             # True se pitch variation > threshold
    "pausas_suspeitas": int,         # Número de pausas longas
    "duracao_segundos": float,       # Duração do áudio
    "risco_violencia": str,          # "baixo"|"medio"|"alto"
    "risco_saude_mental": str,       # "baixo"|"medio"|"alto"
    "metadata": {
        "correlation_id": str,
        "timestamp": datetime,
        "tempo_processamento_ms": int,
        "cache_hit": bool,
        "azure_calls": int
    }
}
```

---

## Contracts

### POST /analyze/audio

**Request**: multipart/form-data
- `audio`: File (WAV, MP3, OGG, max 50MB)
- `tipo_consulta`: str (opcional) - "pré-natal", "pós-parto", "geral"
- `patient_id`: str (opcional) - UUID anônimo

**Response**: 200 OK (AudioAnalysisResponse)

**Errors**:
- 400: Formato inválido ou arquivo muito grande
- 503: Azure Speech indisponível
- 504: Timeout (>30s)

---

## Implementation Phases

### Phase 1: Infrastructure
- Azure Speech Client (singleton, retry, timeout)
- Temp File Manager (LGPD, atexit cleanup)
- File Validation (magic numbers)

### Phase 2: Services
- Prosodic Feature Extractor (librosa)
- Audio Analysis Service (orquestração)
- Response Schema (Pydantic)

### Phase 3: API
- Audio Route (endpoint)
- Register route in main.py
- Swagger documentation

### Phase 4: Testing
- Unit tests (mock Azure)
- Integration tests (endpoint)
- Cobertura > 70%

---

## Dependencies

### Código Existente Reutilizado
- `src/core/config.py` - Configurações Azure Speech
- `src/services/risk_detector.py` - Cálculo de risco
- `src/models/schemas.py` - AnalysisMetadata

### Novos Arquivos
- `azure_speech_client.py` - Cliente Azure
- `temp_file_manager.py` - Gerenciamento temporário
- `audio_analysis.py` - Serviço principal
- `prosodic_extractor.py` - Features prosódicas
- `audio.py` - Endpoint FastAPI
- `file_validation.py` - Validação MIME

---

## Constraints & Tradeoffs

| Constraint | Decision | Rationale |
|------------|----------|-----------|
| Azure SDK sync | Usar asyncio.to_thread() | SDK não suporta async nativo |
| File storage | Local filesystem | Simplicidade, LGPD, custo zero |
| Librosa dependency | Adicionar ao pyproject.toml | Necessário para prosódica |
| Mock mode | Azure client retorna mock se key não configurado | Permite desenvolvimento |

---

## Success Criteria Validation

| Criterion | How to Validate |
|-------------|-----------------|
| SC-001: Latência < 10s | Teste com áudio 1 min, medir tempo |
| SC-002: Precisão > 85% | Comparar transcrição com ground truth |
| SC-003: Arquivos deletados | Verificar /tmp vazio após requisições |
| SC-004: Campos obrigatórios | Schema validation no Pydantic |

---

## Quick Start (Developer)

```bash
# 1. Instalar dependências
poetry install

# 2. Configurar Azure Speech (opcional para dev)
export AZURE_SPEECH_KEY="..."
export AZURE_SPEECH_REGION="brazilsouth"

# 3. Rodar em dev (com mocks se sem Azure)
poetry run uvicorn src.api.main:app --reload

# 4. Testar endpoint
curl -X POST http://localhost:8000/analyze/audio \
  -F "audio=@consulta.wav" \
  -F "tipo_consulta=geral"
```

---

## Version

**Plan Version**: 1.0 | **Last Updated**: 2026-04-12 | **Next**: `/speckit.tasks`
