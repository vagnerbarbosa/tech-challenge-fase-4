# Contract: POST /analyze/video

## Endpoint

```
POST /analyze/video
Content-Type: multipart/form-data
```

## Request

### Headers

| Header | Required | Description |
|--------|----------|-------------|
| Content-Type | Yes | Must be `multipart/form-data` |
| X-API-Key | No | API key se autenticação habilitada |

### Form Fields

| Field | Type | Required | Description |
|-------|------|----------|-------------|
| video | File | Yes | Arquivo de vídeo (MP4, AVI, MOV) |
| tipo | String | No | Tipo de análise: `consulta`, `procedimento`, `exame` (default: `consulta`) |
| patient_id | String | No | ID anônimo do paciente (UUID recomendado) |
| extract_fps | Float | No | Taxa de extração de frames: 0.2-5.0 (default: adaptativo) |

### Constraints

- **Formatos**: MP4, AVI, MOV
- **Tamanho máximo**: 50MB
- **Duração máxima**: 2 minutos (120 segundos)
- **Codecs suportados**: H.264, MPEG-4, Motion JPEG

## Response

### Success (200 OK)

```json
{
  "risco_violencia": "baixo",
  "risco_saude_mental": "medio",
  "detecoes": [
    {
      "classe": "person",
      "confianca": 0.89,
      "bbox": {
        "x": 120.5,
        "y": 80.0,
        "w": 200.0,
        "h": 350.0
      },
      "frame": 5,
      "timestamp": 5.0
    },
    {
      "classe": "sangramento",
      "confianca": 0.72,
      "bbox": {
        "x": 300.0,
        "y": 200.0,
        "w": 50.0,
        "h": 40.0
      },
      "frame": 12,
      "timestamp": 12.0
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
    "correlation_id": "vid-abc123",
    "timestamp": "2026-04-19T15:30:00Z",
    "tempo_processamento_ms": 4500,
    "cache_hit": false,
    "frames_analisados": 24,
    "duracao_video_segundos": 45.5,
    "modelo": "yolov8n",
    "local_processing": true
  }
}
```

### Error Responses

#### 400 Bad Request - Formato inválido

```json
{
  "error": "VALIDATION_ERROR",
  "message": "Formato de vídeo não suportado. Use MP4, AVI ou MOV."
}
```

#### 413 Payload Too Large

```json
{
  "error": "FILE_TOO_LARGE",
  "message": "Arquivo excede o limite de 50MB."
}
```

#### 400 Duração excedida

```json
{
  "error": "DURATION_EXCEEDED",
  "message": "Vídeo excede o limite de 2 minutos."
}
```

#### 500 Internal Server Error

```json
{
  "error": "PROCESSING_ERROR",
  "message": "Erro ao processar vídeo. Tente novamente mais tarde."
}
```

## Example Usage

### cURL

```bash
curl -X POST http://localhost:8000/analyze/video \
  -F "video=@consulta.mp4" \
  -F "tipo=consulta" \
  -F "patient_id=550e8400-e29b-41d4-a716-446655440000"
```

### Python (requests)

```python
import requests

with open("consulta.mp4", "rb") as f:
    files = {"video": ("consulta.mp4", f, "video/mp4")}
    data = {"tipo": "consulta", "patient_id": "uuid-aqui"}
    response = requests.post(
        "http://localhost:8000/analyze/video",
        files=files,
        data=data
    )
    result = response.json()
    print(f"Risco violência: {result['risco_violencia']}")
    print(f"Risco saúde mental: {result['risco_saude_mental']}")
```

## Notes

- O processamento é **síncrono** (bloqueante) mas pode levar alguns segundos
- O vídeo é processado **localmente** pelo YOLOv8 (sem custo Azure no MVP)
- Arquivos temporários são removidos automaticamente após processamento (LGPD)
- O campo `detecoes` pode estar vazio se nenhum objeto for detectado
- Os campos `risco_violencia` e `risco_saude_mental` são sempre obrigatórios
