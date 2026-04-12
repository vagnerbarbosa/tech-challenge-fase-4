# Quickstart: Análise de Áudio

**Feature**: 003-audio-analysis  
**Endpoint**: POST `/analyze/audio`

---

## Setup

### 1. Instalar Dependências

```bash
# Poetry (recomendado)
poetry install

# Ou requirements.txt
pip install -r requirements.txt
```

### 2. Configurar Azure Speech (Opcional para Dev)

```bash
# ~/.env ou export
AZURE_SPEECH_KEY="sua-chave-aqui"
AZURE_SPEECH_REGION="brazilsouth"
```

> **Nota**: Sem Azure configurado, o sistema roda em modo mock (transcrição simulada).

### 3. Verificar FFmpeg (para librosa)

```bash
# Ubuntu/Debian
sudo apt-get install ffmpeg

# macOS
brew install ffmpeg

# Windows
choco install ffmpeg
```

---

## Executar

### Modo Desenvolvimento

```bash
# Com hot-reload
poetry run uvicorn src.api.main:app --reload --port 8000

# Ou com Docker
docker-compose up --build
```

### Verificar Endpoint

```bash
# Health check (agora inclui quotas Azure)
curl http://localhost:8000/health

# Response exemplo:
# {
#   "status": "healthy",
#   "timestamp": "2026-04-12T14:30:00Z",
#   "version": "0.2.0",
#   "environment": "development",
#   "quotas": {
#     "text": {"daily_remaining": 150, "daily_limit": 160},
#     "audio": {"daily_remaining": 8, "daily_limit": 10},
#     "vision": {"daily_remaining": 150, "daily_limit": 160}
#   }
# }

# Swagger UI
open http://localhost:8000/docs
```

---

## Uso

### Exemplo: Análise de Áudio

```bash
curl -X POST http://localhost:8000/analyze/audio \
  -H "Content-Type: multipart/form-data" \
  -F "audio=@/caminho/para/consulta.wav" \
  -F "tipo_consulta=pré-natal" \
  -F "patient_id=550e8400-e29b-41d4-a716-446655440000"
```

### Response

```json
{
  "transcricao": "Doutor, eu estou muito ansiosa...",
  "idioma_detectado": "pt-BR",
  "sentimento": "negativo",
  "entonação": "hesitante",
  "voz_tremida": true,
  "pausas_suspeitas": 2,
  "duracao_segundos": 32.5,
  "risco_violencia": "medio",
  "risco_saude_mental": "alto",
  "metadata": {
    "correlation_id": "uuid-123",
    "timestamp": "2026-04-12T14:30:00Z",
    "tempo_processamento_ms": 8200,
    "cache_hit": false,
    "azure_calls": 1
  }
}
```

---

## Testes

### Unitários

```bash
# Todos os testes de áudio
poetry run pytest tests/unit/services/test_audio_analysis.py -v

# Com cobertura
poetry run pytest tests/unit/ --cov=src --cov-report=html
```

### Integração

```bash
# Endpoint completo
poetry run pytest tests/integration/test_audio_endpoint.py -v
```

### Com Arquivo Real

```bash
# Criar arquivo de teste
ffmpeg -f lavfi -i "sine=frequency=1000:duration=5" -ar 16000 test.wav

# Enviar
curl -X POST http://localhost:8000/analyze/audio \
  -F "audio=@test.wav"

# Limpar
rm test.wav
```

---

## Troubleshooting

### Erro: "Azure Speech não configurado"

```
# Solução: Configurar ou usar modo mock
export AZURE_SPEECH_KEY="sua-chave"
export AZURE_SPEECH_REGION="brazilsouth"
```

### Erro: "Formato não suportado"

```
# Verificar MIME type
file -b --mime-type consulta.wav

# Converter para WAV se necessário
ffmpeg -i audio.mp3 -ar 16000 -ac 1 audio.wav
```

### Erro: "Arquivo muito grande"

```
# Comprimir áudio
ffmpeg -i audio.wav -ar 16000 -ac 1 -b:a 32k audio_compressed.wav
```

### Timeout

```
# Áudio muito longo - cortar
ffmpeg -i audio.wav -t 60 audio_60s.wav  # Primeiros 60s
```

---

## Postman Collection

Ver `docs/collection.json` para importar no Postman.

---

## Variáveis de Ambiente

| Variable | Required | Default | Description |
|----------|----------|---------|-------------|
| AZURE_SPEECH_KEY | No | - | Azure Speech API key |
| AZURE_SPEECH_REGION | No | brazilsouth | Azure region |
| LOG_LEVEL | No | INFO | DEBUG, INFO, WARNING, ERROR |

---

## LGPD Compliance

- Arquivos são salvos temporariamente em `/tmp`
- Auto-cleanup após processamento
- patient_id é hasheado em nomes de arquivo
- Nunca logamos conteúdo do áudio
- Dados não persistem em banco

---

## Links

- [Spec](./spec.md) - Especificação completa
- [Plan](./plan.md) - Plano de implementação
- [Data Model](./data-model.md) - Modelos de dados
