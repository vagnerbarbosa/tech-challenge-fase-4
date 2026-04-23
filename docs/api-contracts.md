# API Contracts

## Base URL

```
Development: http://localhost:8000
Production:  (your-azure-deployment).azurewebsites.net
```

## Authentication

API uses optional API key authentication via header:
```
X-API-Key: your-api-key-here
```

In development mode, authentication is optional.

---

## Endpoints

### 1. Health Check

Check system health and Azure quota status.

**Endpoint:** `GET /health`

**Response:**
```json
{
  "status": "healthy",
  "version": "0.6.0",
  "timestamp": "2026-04-21T12:00:00Z",
  "services": {
    "text_analytics": "connected",
    "speech": "connected",
    "vision": "connected"
  },
  "quotas": {
    "text_remaining": 145,
    "speech_minutes_remaining": 8
  }
}
```

**Status Codes:**
- `200` - Healthy
- `503` - Service unavailable

---

### 2. Text Analysis

Analyze text for sentiment and risk indicators.

**Endpoint:** `POST /analyze/text`

**Content-Type:** `application/json`

**Request Body:**
```json
{
  "texto": "Estou me sentindo muito ansiosa e com medo quando ele chega em casa",
  "tipo": "diario",
  "patient_id": "uuid-anonimo-123"
}
```

**Parameters:**

| Field | Type | Required | Description |
|-------|------|----------|-------------|
| texto | string | Yes | 10-5000 characters |
| tipo | string | No | `diario`, `prontuario`, `relato`, `geral` (default: geral) |
| patient_id | string | No | Anonymous patient UUID |

**Response:**
```json
{
  "sentimento": "negativo",
  "score": -0.85,
  "risco_violencia": "alto",
  "risco_saude_mental": "alto",
  "palavras_chave": ["ansiosa", "medo", "casa"],
  "indicadores": ["ansiedade", "medo"],
  "metadata": {
    "correlation_id": "txt-123456",
    "timestamp": "2026-04-21T12:00:00Z",
    "tempo_processamento_ms": 450,
    "cache_hit": false,
    "azure_calls": 1
  }
}
```

**Status Codes:**
- `200` - Analysis complete
- `400` - Invalid input (validation error)
- `429` - Quota exceeded
- `502` - Azure service error
- `503` - Configuration missing

**Response Fields:**

| Field | Type | Description |
|-------|------|-------------|
| sentimento | string | `positivo`, `negativo`, `neutro`, `misto` |
| score | float | -1.0 to 1.0 |
| risco_violencia | string | `baixo`, `medio`, `alto` **(REQUIRED)** |
| risco_saude_mental | string | `baixo`, `medio`, `alto` **(REQUIRED)** |
| palavras_chave | array | Extracted keywords |
| indicadores | array | Risk-indicating words found |
| metadata | object | Processing metadata |

---

### 3. Audio Analysis

Transcribe and analyze audio for prosodic features and risks.

**Endpoint:** `POST /analyze/audio`

**Content-Type:** `multipart/form-data`

**Request:**
```bash
curl -X POST http://localhost:8000/analyze/audio \
  -H "Content-Type: multipart/form-data" \
  -F "file=@consulta.wav" \
  -F "patient_id=uuid-anonimo-123"
```

**Parameters:**

| Field | Type | Required | Description |
|-------|------|----------|-------------|
| file | File | Yes | Audio file (WAV, MP3, OGG) |
| patient_id | string | No | Anonymous patient UUID |

**Constraints:**
- Max file size: 50MB
- Max duration: 5 minutes (Free Tier)
- Supported formats: WAV, MP3, OGG

**Response:**
```json
{
  "transcricao": "Doutor, eu não sei se posso contar isso...",
  "idioma_detectado": "pt-BR",
  "sentimento": "negativo",
  "entonação": "hesitante",
  "voz_tremida": true,
  "pausas_suspeitas": 3,
  "duracao_segundos": 45.2,
  "risco_violencia": "medio",
  "risco_saude_mental": "alto",
  "metadata": {
    "correlation_id": "aud-123456",
    "timestamp": "2026-04-21T12:00:00Z",
    "tempo_processamento_ms": 8500,
    "cache_hit": false,
    "azure_calls": 1
  }
}
```

**Status Codes:**
- `200` - Analysis complete
- `400` - Invalid file format
- `413` - File too large (>50MB)
- `429` - Quota exceeded

---

### 4. Video Analysis

Analyze video for objects, bleeding, and body language.

**Endpoint:** `POST /analyze/video`

**Content-Type:** `multipart/form-data`

**Request:**
```bash
curl -X POST http://localhost:8000/analyze/video \
  -H "Content-Type: multipart/form-data" \
  -F "video=@procedimento.mp4" \
  -F "tipo=procedimento" \
  -F "patient_id=uuid-anonimo-123"
```

**Parameters:**

| Field | Type | Required | Description |
|-------|------|----------|-------------|
| video | File | Yes | Video file (MP4, AVI, MOV) |
| tipo | string | No | `consulta`, `procedimento`, `exame` (default: consulta) |
| patient_id | string | No | Anonymous patient UUID |

**Constraints:**
- Max file size: 50MB
- Max duration: 2 minutes
- Supported formats: MP4, AVI, MOV
- Processing: Local (no Azure cost)

**Response:**
```json
{
  "risco_violencia": "baixo",
  "risco_saude_mental": "medio",
  "detecoes": [
    {
      "classe": "person",
      "confianca": 0.89,
      "bbox": {"x": 0.1, "y": 0.2, "w": 0.3, "h": 0.5},
      "frame": 5,
      "timestamp": 5.0
    }
  ],
  "alertas": [
    {
      "tipo": "sangramento_detectado",
      "severidade": "media",
      "descricao": "Possível sangramento detectado no vídeo",
      "frame_referencia": 12
    }
  ],
  "metadata": {
    "correlation_id": "vid-123456",
    "timestamp": "2026-04-21T12:00:00Z",
    "tempo_processamento_ms": 4500,
    "cache_hit": false,
    "frames_analisados": 24,
    "duracao_video_segundos": 45.5,
    "modelo": "yolov8n",
    "local_processing": true
  }
}
```

**Detection Classes:**
- `person` - Person detected
- `scissors` - Surgical scissors
- `knife` - Surgical knife
- `sangramento` - Bleeding detected (custom HSV analysis)

**Status Codes:**
- `200` - Analysis complete
- `400` - Invalid file or duration exceeded
- `413` - File too large (>50MB)
- `429` - Rate limit exceeded
- `504` - Processing timeout

---

### 5. Get Video Formats

Get supported video formats and limits.

**Endpoint:** `GET /analyze/video/formats`

**Response:**
```json
{
  "formatos_suportados": ["MP4", "AVI", "MOV"],
  "extensoes": [".mp4", ".avi", ".mov"],
  "tamanho_maximo_mb": 50,
  "duracao_maxima_segundos": 120,
  "duracao_maxima_minutos": 2,
  "fps_adaptativo": {
    "ate_30s": "1 FPS (1 frame/segundo)",
    "acima_30s": "0.2 FPS (1 frame/5 segundos)"
  }
}
```

---

### 6. Get Video Cache Stats

Get video analysis cache statistics.

**Endpoint:** `GET /analyze/video/cache/stats`

**Response:**
```json
{
  "entries": 50,
  "ttl_minutes": 60.0
}
```

---

### 7. Clear Video Cache

Clear all video analysis cache entries.

**Endpoint:** `POST /analyze/video/cache/clear`

**Response:**
```json
{
  "message": "Cache de vídeo limpo com sucesso"
}
```

---

### 8. Get Audio Formats

Get supported audio formats and limits.

**Endpoint:** `GET /analyze/audio/formats`

**Response:**
```json
{
  "formatos_suportados": ["WAV", "MP3", "OGG"],
  "extensoes": [".wav", ".mp3", ".ogg"],
  "tamanho_maximo_mb": 50,
  "duracao_maxima_segundos": 300,
  "duracao_maxima_minutos": 5,
  "azure_quota": {
    "max_minutos_por_dia": 10,
    "max_minutos_por_mes": 300
  }
}
```

---

## Error Response Format

All errors follow this structure:

```json
{
  "error": "ERROR_CODE",
  "message": "Human-readable error description",
  "details": [
    {
      "field": "field_name",
      "message": "Field-specific error"
    }
  ]
}
```

### Error Codes

| Code | HTTP Status | Description |
|------|-------------|-------------|
| VALIDATION_ERROR | 400 | Input validation failed |
| FILE_TOO_LARGE | 413 | File exceeds size limit |
| DURATION_EXCEEDED | 400 | Video/audio duration too long |
| QUOTA_EXCEEDED | 429 | Azure quota exceeded |
| AZURE_SERVICE_ERROR | 502 | Azure API error |
| SERVICE_UNAVAILABLE | 503 | Configuration missing |
| PROCESSING_TIMEOUT | 504 | Processing took too long |
| RATE_LIMIT_EXCEEDED | 429 | Rate limit hit |

---

## Required Fields Contract

**IMPORTANT:** All analysis endpoints MUST return these fields:

```json
{
  "risco_violencia": "baixo|medio|alto",
  "risco_saude_mental": "baixo|medio|alto"
}
```

These fields are mandatory for all response types (text, audio, video, multimodal).

---

## Rate Limits

| Endpoint | Limit | Window |
|----------|-------|--------|
| POST /analyze/text | 160/day | Azure Free Tier |
| POST /analyze/audio | 10 min/day | Azure Free Tier |
| POST /analyze/video | No Azure limit | Local processing |

When limits exceeded:
- HTTP 429 returned
- `Retry-After` header included
- No Azure quota consumed

---

## OpenAPI Specification

Interactive docs available at:
- Swagger UI: `http://localhost:8000/docs`
- ReDoc: `http://localhost:8000/redoc`
- OpenAPI JSON: `http://localhost:8000/openapi.json`
