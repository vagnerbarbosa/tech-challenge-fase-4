# Architecture Documentation

## System Overview

**Tech Challenge Fase 4** - API multimodal para análise de saúde da mulher usando Azure AI Services e ML local (YOLOv8).

## Architecture Diagram

```
┌─────────────────────────────────────────────────────────────┐
│                        Client Layer                          │
│              (HTTP requests - curl, frontend)               │
└──────────────────────┬──────────────────────────────────────┘
                       │
┌──────────────────────▼──────────────────────────────────────┐
│                     API Layer                                │
│  FastAPI + Uvicorn + Pydantic v2 + CORS Middleware          │
│  Routes: /health, /analyze/text, /analyze/audio,            │
│          /analyze/video, /analyze/multimodal (pending)     │
└──────────────────────┬──────────────────────────────────────┘
                       │
        ┌──────────────┼──────────────┐
        │              │              │
┌───────▼──────┐ ┌────▼─────┐ ┌──────▼──────┐
│   Service    │ │ Service  │ │   Service   │
│    Layer     │ │  Layer   │ │    Layer    │
│              │ │          │ │             │
│ TextAnalysis │ │  Audio   │ │   Video     │
│   Service    │ │ Analysis │ │  Analysis   │
│              │ │  Service │ │   Service   │
└───────┬──────┘ └────┬─────┘ └──────┬──────┘
        │             │            │
┌───────▼─────────────▼────────────▼────────┐
│          Infrastructure Layer              │
│  Azure Clients (Text, Speech, Vision)     │
│  Azure AI Content Safety (Text moderate)│
│  YOLOv8 (Ultralytics) - Local ML          │
│  OpenCV - Frame extraction                │
│  librosa - Audio prosody analysis         │
└───────────────────┬───────────────────────┘
                    │
┌───────────────────▼───────────────────────┐
│              Core Layer                 │
│  - Config (Pydantic Settings)           │
│  - Logging (structlog)                  │
│  - Rate Limiting (Azure quota mgmt)     │
│  - Cache (in-memory TTL)                │
│  - Temp File Manager (LGPD compliant)   │
│  - Exceptions (custom error hierarchy)  │
│  - MultilingualRiskDetector (CS + Keywords)│
└─────────────────────────────────────────┘
```

## Component Details

### API Layer (`src/api/`)

| Component | Responsibility |
|-----------|---------------|
| `main.py` | FastAPI app factory, lifespan management, exception handlers |
| `routes/health.py` | Health check with Azure quota status |
| `routes/text.py` | Text sentiment analysis endpoint |
| `routes/audio.py` | Audio transcription + prosody analysis |
| `routes/video.py` | Video analysis with YOLOv8 |
| `routes/dependencies.py` | FastAPI dependency injection |

### Service Layer (`src/services/`)

| Service | Technology | Purpose |
|---------|-----------|---------|
| `text_analysis.py` | Azure AI Language | Sentiment analysis, NLP |
| `audio_analysis.py` | Azure Speech + librosa | Transcription, prosody features |
| `video_analysis.py` | YOLOv8 + OpenCV | Object detection, bleeding detection |
| `yolo_service.py` | Ultralytics YOLOv8n | Person/object detection |
| `bleeding_detector.py` | OpenCV HSV | Blood detection via color analysis |
| `posture_analyzer.py` | Custom heuristics | Body language analysis |
| `risk_detector.py` | Keyword matching | Violence/mental health risk detection |
| `risk_calculator_video.py` | Scoring algorithm | Video risk level calculation |

### Infrastructure Layer (`src/infrastructure/`)

| Component | SDK | Purpose |
|-----------|-----|---------|
| Azure Text Client | `azure-ai-textanalytics` | Text analysis API calls |
| Azure Speech Client | `azure-cognitiveservices-speech` | Speech-to-text |
| Azure Vision Client | `azure-ai-vision-imageanalysis` | Image analysis (fallback) |
| Azure Content Safety | `azure-ai-contentsafety` | Text moderation, risk detection |

### Core Layer (`src/core/`)

| Module | Purpose |
|--------|---------|
| `config.py` | Pydantic Settings, env var validation |
| `logging_config.py` | Structured logging with structlog |
| `rate_limit.py` | Azure Free Tier quota protection |
| `cache.py` | In-memory TTL cache for results |
| `temp_file_manager.py` | LGPD-compliant temp file handling |
| `exceptions.py` | Custom exception hierarchy |
| `risk_detector.py` | MultilingualRiskDetector (CS + Keywords) |

## Data Flow

### Text Analysis Flow
```
1. Client POST /analyze/text
2. Validate request (Pydantic)
3. Check rate limit (160/day)
4. Call Azure Text Analytics API
5. Call Azure Content Safety API (severidade 0-6)
6. Detect risk keywords local (PT + EN fallback)
7. Combinar scores (MultilingualRiskDetector)
8. Calculate risk levels
9. Return JSON response com risco_violencia, risco_saude_mental
10. Cache result
```

### Audio Analysis Flow
```
1. Client POST /analyze/audio (multipart/form-data)
2. Validate file (WAV/MP3/OGG, <50MB)
3. Check rate limit (10 min/day)
4. Save temp file
5. Call Azure Speech-to-Text (transcrição)
6. Analyze prosody with librosa (pitch, energy, pauses)
7. Call Azure Content Safety API na transcrição (severidade 0-6)
8. Detect risk keywords na transcrição (PT + EN fallback)
9. Combinar scores (MultilingualRiskDetector)
10. Calculate risk levels
11. Return response + cleanup temp files
```

### Video Analysis Flow
```
1. Client POST /analyze/video (multipart/form-data)
2. Validate file (MP4/AVI/MOV, <50MB, <2min)
3. Save temp file
4. Extract frames (1 FPS ≤30s, 0.2 FPS >30s)
5. YOLOv8 detection (person, scissors, knife)
6. Bleeding detection (HSV color analysis)
7. Posture analysis (bounding box heuristics)
8. Calculate risk levels
9. Return response + cleanup temp files
```

## Risk Detection

### Violence Risk Keywords
Located in `src/core/config.py` - `RISK_KEYWORDS["violencia"]`
- Physical: bater, soco, chute, empurrar, tapa
- Psychological: ameaça, xingar, humilhar, controlar, proibir
- Indicators: ciúmes, medo, fugir, desespero

### Mental Health Risk Keywords
Located in `src/core/config.py` - `RISK_KEYWORDS["saude_mental"]`
- Depression markers: depressão, tristeza, vazio, desanimo
- Anxiety markers: ansiedade, pânico, crise, insônia
- Critical markers: suicídio, morrer, não aguento mais

## Content Safety Integration

### Overview
O sistema utiliza **Azure AI Content Safety** combinado com detecção por keywords locais para identificação robusta de riscos em texto e transcrições de áudio. Essa abordagem híbrida maximiza a cobertura linguística enquanto mantém controle sobre termos específicos do contexto de saúde da mulher.

### Architecture Components

```
┌─────────────────────────────────────────────────────────────┐
│               MultilingualRiskDetector                      │
│                                                             │
│  ┌─────────────────┐        ┌──────────────────────┐       │
│  │  Azure AI       │        │  Local Keywords      │       │
│  │  Content Safety │        │  (PT + EN)           │       │
│  │                 │        │                      │       │
│  │  - 100+ idiomas │        │  - Violência         │       │
│  │  - Severidade   │        │  - Saúde mental      │       │
│  │    0-6          │        │  - Contexto BR       │       │
│  └────────┬────────┘        └──────────┬───────────┘       │
│           │                            │                 │
│           └────────────┬───────────────┘                 │
│                        ▼                                 │
│           ┌─────────────────────────┐                   │
│           │   Combinação de scores  │                   │
│           │   (fallback híbrido)    │                   │
│           └────────────┬────────────┘                   │
│                        ▼                                 │
│           ┌─────────────────────────┐                   │
│           │  risco_violencia: bool  │                   │
│           │  risco_saude_mental: bool│                  │
│           └─────────────────────────┘                   │
└─────────────────────────────────────────────────────────────┘
```

### Design Decision: Por que CS + Keywords?

| Aspect | Azure Content Safety | Keywords Locais |
|--------|---------------------|-----------------|
| **Idiomas** | 100+ idiomas suportados | PT/EN otimizados |
| **Contexto cultural** | Genérico, global | Específico para Brasil |
| **Termos médicos** | Cobertura limitada | "aborto espontâneo", "hemorragia" |
| **Dependência** | API externa (quota) | 100% local, zero custo |
| **Latência** | ~50-200ms | <1ms |

**Estratégia combinada:**
1. **Content Safety como detector primário** - Cobertura multilíngue nativa
2. **Keywords como fallback e reforço** - Termos específicos do domínio
3. **Score combinado** - OR lógico: CS severidade > 3 OU keyword match

### Language Agnostic Detection

O Azure AI Content Safety é **agnóstico a idioma** por design:
- Mesmo modelo para todos os idiomas suportados
- Sem necessidade de especificar `language` no request
- Treinado em conteúdo multilíngue real
- Severidade 0-6 consistente across idiomas

```python
# Exemplo: mesmo comportamento para PT, EN, ES
from azure.ai.contentsafety import ContentSafetyClient

# Não requer language parameter
response = client.analyze_text(text="conteúdo em qualquer idioma")
# Retorna severidade 0-6 independente do idioma detectado
```

### Detection Flow

#### Text Analysis com Content Safety
```
1. Client POST /analyze/text
2. Validate request (Pydantic)
3. Check rate limit (160/day)
4. Call Azure Text Analytics API (sentimento)
5. Call Azure Content Safety API (moderação)
   └─ Retorna severidades: hate, self-harm, violence
6. Executar keyword matching local (PT/EN)
7. Combinar resultados (MultilingualRiskDetector)
8. Calcular risk levels
9. Return JSON response com risco_violencia, risco_saude_mental
```

#### Audio Analysis com Content Safety
```
1. Client POST /analyze/audio (multipart/form-data)
2. Validate file (WAV/MP3/OGG, <50MB)
3. Check rate limit (10 min/day)
4. Save temp file
5. Call Azure Speech-to-Text (transcrição)
6. Call Azure Content Safety API na transcrição
   └─ Severidade 0-6 para cada categoria
7. Executar keyword matching na transcrição
8. Combinar resultados com prosody analysis
9. Calculate risk levels
10. Return response + cleanup temp files
```

### Severity Mapping

| Severity CS | Significado | Keywords Match | Resultado |
|-------------|-------------|----------------|-----------|
| 0 | Conteúdo seguro | Nenhuma | `risco_violencia: false` |
| 1-2 | Baixo risco | - | `risco_violencia: false` |
| 3-4 | Médio risco | Sim | `risco_violencia: true` |
| 5-6 | Alto risco | Sim/Não | `risco_violencia: true` |

### MultilingualRiskDetector

Localizado em `src/core/risk_detector.py`:

```python
class MultilingualRiskDetector:
    """
    Combina Azure Content Safety com keyword matching local.
    Retorna risk flags independente do idioma de entrada.
    """

    def analyze(self, text: str) -> RiskAssessment:
        # 1. Chama Azure Content Safety
        cs_result = self.content_safety.analyze(text)

        # 2. Executa keyword matching (PT + EN)
        keyword_result = self.keywords.analyze(text)

        # 3. Combina resultados (OR lógico)
        return RiskAssessment(
            risco_violencia=cs_result.severity > 3 or keyword_result.violence,
            risco_saude_mental=cs_result.self_harm > 3 or keyword_result.mental_health
        )
```

### Quota Considerations

Content Safety compartilha quota com outros serviços Azure:
- **Free Tier**: 5,000 transações/mês (compartilhado com Text Analytics)
- Fallback para keywords locais quando quota excedida
- Cache de resultados para textos repetidos

## Azure Free Tier Protection

### Rate Limits (configurable in `.env`)

| Service | Daily | Monthly |
|---------|-------|---------|
| Text Analytics | 160 requests | 5,000 requests |
| Speech | 10 minutes | 300 minutes |
| Computer Vision | 160 requests | 5,000 requests |

### Hard Stop Behavior
When quotas exceeded:
- Return HTTP 429 (Too Many Requests)
- Include `Retry-After` header
- Log warning with correlation_id
- No Azure API calls made (saves quota)

## LGPD Compliance

### Data Handling
- **Anonymization**: PII stripped before processing
- **Consent**: Explicit consent required flag
- **Temp Files**: Auto-cleanup in `finally` blocks
- **Retention**: 30-day default (configurable)

### Security
- Secrets in `.env` (never committed)
- API key authentication (optional in dev)
- No media content in logs
- Structured logging with correlation IDs

## Project Structure

```
tech-challenge-fase-4/
├── src/
│   ├── api/              # FastAPI routes
│   ├── core/             # Config, logging, rate limiting
│   ├── infrastructure/   # Azure clients
│   ├── models/           # Pydantic schemas
│   ├── services/         # Business logic
│   └── utils/            # Video validation, helpers
├── tests/
│   ├── unit/            # Service tests
│   ├── integration/     # API endpoint tests
│   └── load/            # Locust tests
├── docs/                # Documentation
├── scripts/             # Dev scripts
└── docker-compose.yml   # Docker setup
```

## Technology Stack

| Category | Technology | Version |
|----------|-----------|---------|
| Runtime | Python | 3.11+ |
| Framework | FastAPI | 0.115+ |
| Validation | Pydantic | v2 |
| Azure SDK | azure-ai-textanalytics | 5.4.0 |
| Azure SDK | azure-cognitiveservices-speech | 1.48.x |
| ML | Ultralytics (YOLOv8) | 8.x |
| CV | OpenCV | 4.8+ |
| Audio | librosa | 0.10+ |
| Testing | pytest | 8.x |
| Linting | ruff | - |
| Types | mypy | strict |

## Deployment

### Docker
```bash
docker-compose up --build -d
```

### Local Dev
```bash
poetry install
poetry run uvicorn src.api.main:app --reload
```

## References

- Azure AI Services: https://azure.microsoft.com/services/cognitive-services/
- YOLOv8: https://docs.ultralytics.com/
- FastAPI: https://fastapi.tiangolo.com/
