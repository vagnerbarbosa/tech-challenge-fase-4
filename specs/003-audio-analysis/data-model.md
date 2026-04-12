# Data Model: Análise de Áudio

**Feature**: 003-audio-analysis  
**Date**: 2026-04-12

---

## Entities

### AudioAnalysisRequest

Input do endpoint POST /analyze/audio.

| Field | Type | Required | Validation |
|-------|------|----------|------------|
| audio | UploadFile | Yes | MIME: audio/wav, audio/mpeg, audio/ogg, audio/x-wav; Max: 50MB |
| tipo_consulta | string | No | Enum: "pré-natal", "pós-parto", "geral" |
| patient_id | string | No | UUID v4 format (anônimo) |

**Validation Rules**:
1. Arquivo obrigatório
2. Extensão deve ser .wav, .mp3, ou .ogg
3. Magic numbers devem corresponder ao tipo MIME permitido
4. Tamanho máximo 50MB

---

### AudioAnalysisResponse

Output do endpoint POST /analyze/audio.

| Field | Type | Description | Constraints |
|-------|------|-------------|-------------|
| transcricao | string | Texto transcrito do áudio | Não vazio em sucesso |
| idioma_detectado | string | Idioma identificado | Default: "pt-BR" |
| sentimento | string | Sentimento da transcrição | Enum: positivo, negativo, neutro, misto |
| entonação | string | Classificação prosódica | Enum: normal, hesitante, agitado, calmo |
| voz_tremida | boolean | Indica tremor na voz | Threshold: pitch_std > 50Hz |
| pausas_suspeitas | integer | Número de pausas longas | Min: 0 |
| duracao_segundos | float | Duração do áudio em segundos | Min: 0.1 |
| risco_violencia | string | Nível de risco | Enum: baixo, medio, alto (OBRIGATÓRIO) |
| risco_saude_mental | string | Nível de risco | Enum: baixo, medio, alto (OBRIGATÓRIO) |
| metadata | AnalysisMetadata | Metadados da análise | Ver schema abaixo |

**Derived Fields**:
- `sentimento`: Calculado via risk_detector.analyze_text(transcricao)
- `risco_violencia`: Baseado em keywords + features prosódicas
- `risco_saude_mental`: Baseado em keywords + features prosódicas

---

### AnalysisMetadata (Reused)

| Field | Type | Description |
|-------|------|-------------|
| correlation_id | string | UUID único da requisição |
| timestamp | datetime | ISO 8601 UTC |
| tempo_processamento_ms | integer | Tempo total em ms |
| cache_hit | boolean | Se veio do cache |
| azure_calls | integer | Número de chamadas Azure |

---

### ProsodicFeatures (Internal)

Dados extraídos via librosa (não expostos na API).

| Field | Type | Description |
|-------|------|-------------|
| pitch_mean | float | Pitch médio (Hz) |
| pitch_std | float | Desvio padrão do pitch |
| pitch_range | float | Range do pitch (max - min) |
| energy_mean | float | Energia média (RMS) |
| energy_std | float | Desvio padrão da energia |
| silence_count | integer | Número de segmentos de silêncio |
| duration_seconds | float | Duração total |

---

## State Transitions

```
UploadFile → [Validation] → Validated

Validated → [Save Temp] → TempSaved

TempSaved → [Transcribe Azure] + [Extract Prosodic]
    ↓ Parallel
Transcription + ProsodicFeatures
    ↓
[Risk Analysis]
    ↓
AudioAnalysisResponse
    ↓
[Cleanup Temp File]
```

**Error States**:
- Validation Error → HTTP 400
- Azure Unavailable → HTTP 503  
- Timeout → HTTP 504
- Quota Exceeded → HTTP 429

---

## Relationships

```
AudioAnalysisRequest
    │ 1:1
    ▼
TempFile (em /tmp, lifecycle: request)
    │ 1:1
    ▼
AudioAnalysis (processamento)
    │
    ├──► Azure Speech API (transcrição)
    │
    └──► Librosa (prosódica)
    │
    ▼
AudioAnalysisResponse
    │
    └──► RiskDetector (reused from text analysis)
```

---

## File Storage

### Temp File Naming

```
/tmp/audio_{patient_id_hash}_{timestamp}_{random}.ext

Example:
/tmp/audio_a1b2c3d4_20260412_143052_7f8e9d0a.wav
```

**Components**:
- `patient_id_hash`: SHA256 dos primeiros 8 chars do patient_id (anonimização parcial)
- `timestamp`: YYYYMMDD_HHMMSS
- `random`: 8 chars hex (evitar colisão)
- `ext`: Extensão original

**Lifecycle**:
1. Criado no início do request
2. Processado (transcrição + prosódica)
3. Deletado no `finally` block
4. Fallback: atexit cleanup se `finally` falhar

---

## Validation Rules

### Audio File Validation

```python
# 1. Extension Check
allowed_extensions = {'.wav', '.mp3', '.ogg'}
if ext not in allowed_extensions:
    raise HTTPException(400, detail="Extensão não permitida")

# 2. Magic Numbers Check
allowed_mimes = {
    'audio/wav': '.wav',
    'audio/mpeg': '.mp3', 
    'audio/ogg': '.ogg',
    'audio/x-wav': '.wav'
}
mime = magic.from_buffer(content, mime=True)
if mime not in allowed_mimes:
    raise HTTPException(400, detail=f"Tipo MIME não suportado: {mime}")

# 3. Size Check
if file_size > 50 * 1024 * 1024:  # 50MB
    raise HTTPException(400, detail="Arquivo muito grande (max 50MB)")
```

---

## Indexes/Keys

### In-Memory (Runtime)

- `temp_files: Set[Path]` - Tracking de arquivos para cleanup
- `azure_speech_config: SpeechConfig` - Singleton (lru_cache)

### Not Stored

Não há persistência em banco de dados (LGPD compliance).

---

## Schema Example

### Request (multipart/form-data)

```
POST /analyze/audio
Content-Type: multipart/form-data; boundary=----WebKitFormBoundary

------WebKitFormBoundary
Content-Disposition: form-data; name="audio"; filename="consulta.wav"
Content-Type: audio/wav

[binary data]
------WebKitFormBoundary
Content-Disposition: form-data; name="tipo_consulta"

pré-natal
------WebKitFormBoundary
Content-Disposition: form-data; name="patient_id"

550e8400-e29b-41d4-a716-446655440000
------WebKitFormBoundary--
```

### Response (application/json)

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
    "correlation_id": "uuid-1234",
    "timestamp": "2026-04-12T14:30:52Z",
    "tempo_processamento_ms": 8500,
    "cache_hit": false,
    "azure_calls": 1
  }
}
```

---

## Version

**Schema Version**: 1.0 | **Last Updated**: 2026-04-12
