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

### Core Layer (`src/core/`)

| Module | Purpose |
|--------|---------|
| `config.py` | Pydantic Settings, env var validation |
| `logging_config.py` | Structured logging with structlog |
| `rate_limit.py` | Azure Free Tier quota protection |
| `cache.py` | In-memory TTL cache for results |
| `temp_file_manager.py` | LGPD-compliant temp file handling |
| `exceptions.py` | Custom exception hierarchy |

## Data Flow

### Text Analysis Flow
```
1. Client POST /analyze/text
2. Validate request (Pydantic)
3. Check rate limit (160/day)
4. Call Azure Text Analytics API
5. Detect risk keywords locally
6. Calculate risk levels
7. Return JSON response
8. Cache result
```

### Audio Analysis Flow
```
1. Client POST /analyze/audio (multipart/form-data)
2. Validate file (WAV/MP3/OGG, <50MB)
3. Check rate limit (10 min/day)
4. Save temp file
5. Call Azure Speech-to-Text
6. Analyze prosody with librosa (pitch, energy, pauses)
7. Run text analysis on transcription
8. Calculate risk levels
9. Return response + cleanup temp files
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
