# Quickstart: Análise de Vídeo

Guia rápido para começar a usar o endpoint de análise de vídeo.

---

## Pré-requisitos

1. **Instalar dependências**

```bash
poetry install
# OU
docker-compose build
```

2. **Baixar modelo YOLOv8n** (automático no Docker, ou manualmente):

```bash
python -c "from ultralytics import YOLO; YOLO('yolov8n.pt')"
```

---

## Executar a API

### Local (desenvolvimento)

```bash
poetry run uvicorn src.api.main:app --reload
```

### Docker

```bash
docker-compose up -d
```

A API estará disponível em `http://localhost:8000`

---

## Testar o Endpoint

### 1. Verificar health check

```bash
curl http://localhost:8000/health
```

### 2. Enviar vídeo para análise

```bash
# Usando cURL
curl -X POST http://localhost:8000/analyze/video \
  -F "video=@caminho/para/seu/video.mp4" \
  -F "tipo=consulta"
```

### 3. Ver resposta

A resposta será um JSON com:
- `risco_violencia`: baixo | medio | alto
- `risco_saude_mental`: baixo | medio | alto
- `detecoes`: Lista de objetos detectados
- `alertas`: Alertas gerados
- `metadata`: Informações do processamento

---

## Limites

| Recurso | Limite |
|---------|--------|
| Tamanho do arquivo | 50MB |
| Duração do vídeo | 2 minutos |
| Formatos | MP4, AVI, MOV |
| Frames máximos | ~24 (amostragem adaptativa) |

---

## Exemplos de Uso

### Exemplo 1: Consulta médica simples

```python
import requests

with open("consulta.mp4", "rb") as f:
    response = requests.post(
        "http://localhost:8000/analyze/video",
        files={"video": f},
        data={"tipo": "consulta"}
    )
    
result = response.json()
print(f"Risco violência: {result['risco_violencia']}")
print(f"Objetos detectados: {len(result['detecoes'])}")
```

### Exemplo 2: Com patient_id (LGPD-compliant)

```python
import uuid

patient_id = str(uuid.uuid4())  # Gera ID anônimo

with open("procedimento.mp4", "rb") as f:
    response = requests.post(
        "http://localhost:8000/analyze/video",
        files={"video": f},
        data={
            "tipo": "procedimento",
            "patient_id": patient_id
        }
    )
```

---

## Troubleshooting

### Erro: "Formato de vídeo não suportado"

- Verifique se o arquivo é MP4, AVI ou MOV
- Use `ffprobe` para verificar o codec: `ffprobe -v error video.mp4`

### Erro: "Arquivo excede o limite"

- Comprima o vídeo: `ffmpeg -i input.mp4 -vcodec h264 -acodec mp2 output.mp4`
- Ou corte o vídeo: `ffmpeg -ss 00:00:00 -t 00:02:00 -i input.mp4 output.mp4`

### Timeout no processamento

- Vídeos longos (>30s) podem levar mais tempo
- O padrão é timeout de 30 segundos na requisição

---

## Ver Swagger/OpenAPI

Acesse `http://localhost:8000/docs` para documentação interativa completa.

---

## Próximos Passos

1. Verifique os [exemplos de resposta](contracts/video-endpoint.md)
2. Consulte a [especificação completa](../spec.md)
3. Veja os [testes de exemplo](../../tests/integration/test_video_endpoint.py)
