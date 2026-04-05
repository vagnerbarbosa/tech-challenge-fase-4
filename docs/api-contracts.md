# Contratos de API

## Base URL

```
Desenvolvimento: http://localhost:8000
Produção: https://diabetes-analysis-api.azurewebsites.net (exemplo)
```

---

## Schema Base de Resposta (Todos os Endpoints de Análise)

Todos os endpoints de análise (`/analyze/*`) retornam obrigatoriamente:

| Campo | Tipo | Valores | Descrição |
|-------|------|---------|-----------|
| `risco_violencia` | string | baixo, medio, alto | Nível de risco de violência doméstica |
| `risco_saude_mental` | string | baixo, medio, alto | Nível de risco de saúde mental |
| `metadata` | object | - | Informações da requisição |

**Nota:** Campos adicionais específicos de cada modalidade são incluídos conforme documentado em cada endpoint.

## Autenticação

**MVP**: Sem autenticação (para facilitar demonstração)

**Pós-MVP**: API Key no header `X-API-Key`

## Headers Comuns

### Requisição

| Header | Obrigatório | Descrição |
|--------|-------------|-----------|
| `Content-Type` | Sim | `application/json` ou `multipart/form-data` |
| `X-Correlation-ID` | Não | ID para rastreamento |

### Resposta

| Header | Descrição |
|--------|-----------|
| `X-Correlation-ID` | ID de rastreamento da requisição |
| `X-RateLimit-Limit` | Limite de requisições |
| `X-RateLimit-Remaining` | Requisições restantes |

---

## Endpoints

### 1. Health Check

Verifica a saúde da API e serviços Azure.

```
GET /health
```

**Autenticação**: Não requerida

#### Resposta 200 OK

```json
{
  "status": "healthy",
  "version": "1.0.0",
  "timestamp": "2026-04-05T14:30:00Z",
  "servicos_azure": {
    "text_analytics": "disponível",
    "speech": "disponível",
    "computer_vision": "disponível"
  },
  "quota_restante": {
    "text_requests": "4800/5000",
    "audio_minutes": "180/300",
    "vision_requests": "4500/5000"
  }
}
```

#### Resposta 503 Service Unavailable

```json
{
  "status": "degraded",
  "version": "1.0.0",
  "servicos_azure": {
    "text_analytics": "indisponível",
    "speech": "disponível",
    "computer_vision": "disponível"
  },
  "mensagem": "Azure Text Analytics indisponível"
}
```

---

### 2. Análise de Texto

Analisa texto para identificar sentimentos e riscos.

```
POST /analyze/text
```

#### Request Body

```json
{
  "texto": "Estou me sentindo muito ansiosa e tenho medo quando ele chega em casa",
  "tipo": "diario",
  "patient_id": "uuid-anonimo-123"
}
```

#### Schema de Entrada

| Campo | Tipo | Validação | Obrigatório | Descrição |
|-------|------|-----------|-------------|-----------|
| `texto` | string | min: 10, max: 5000 | Sim | Texto para análise |
| `tipo` | string | enum: [diario, prontuario, relato, geral] | Não | Tipo do texto |
| `patient_id` | string | uuid format | Não | ID anônimo do paciente |

#### Resposta 200 OK

```json
{
  "sentimento": "negativo",
  "score": -0.85,
  "risco_violencia": "alto",
  "risco_saude_mental": "alto",
  "palavras_chave": ["ansiosa", "medo", "casa"],
  "indicadores": ["expressao_medo", "contexto_familiar"],
  "metadata": {
    "correlation_id": "abc-123-xyz",
    "timestamp": "2026-04-05T14:30:00Z",
    "tempo_processamento_ms": 450
  }
}
```

#### Resposta 400 Bad Request

```json
{
  "error": {
    "code": "VALIDATION_ERROR",
    "message": "Dados de entrada inválidos",
    "details": [
      {
        "field": "texto",
        "message": "Texto deve ter entre 10 e 5000 caracteres",
        "recebido": 5
      }
    ]
  }
}
```

#### Resposta 429 Too Many Requests

```json
{
  "error": {
    "code": "RATE_LIMIT_EXCEEDED",
    "message": "Limite de requisições ao Azure Text Analytics excedido",
    "retry_after": 3600,
    "limite_diario": 160,
  "limite_atual": 165
  }
}
```

---

### 3. Análise de Áudio

Transcreve e analisa arquivos de áudio.

```
POST /analyze/audio
```

**Content-Type**: `multipart/form-data`

#### Request

```bash
curl -X POST "http://localhost:8000/analyze/audio" \
  -H "Content-Type: multipart/form-data" \
  -F "audio=@consulta.wav" \
  -F "tipo_consulta=pré-natal" \
  -F "patient_id=uuid-anonimo-123"
```

#### Campos do Formulário

| Campo | Tipo | Validação | Obrigatório | Descrição |
|-------|------|-----------|-------------|-----------|
| `audio` | file | WAV, MP3, OGG, max: 50MB | Sim | Arquivo de áudio |
| `tipo_consulta` | string | - | Não | Contexto da consulta |
| `patient_id` | string | uuid | Não | ID anônimo |

#### Resposta 200 OK

```json
{
  "transcricao": "Doutor, eu não sei se posso contar isso, mas tenho medo quando ele chega em casa",
  "idioma_detectado": "pt-BR",
  "sentimento": "negativo",
  "entonação": "hesitante",
  "voz_tremida": true,
  "pausas_suspeitas": 3,
  "duracao_segundos": 45,
  "risco_violencia": "alto",
  "risco_saude_mental": "medio",
  "metadata": {
    "correlation_id": "abc-123-xyz",
    "timestamp": "2026-04-05T14:30:00Z",
    "tempo_processamento_ms": 8500
  }
}
```

#### Resposta 400 Bad Request

```json
{
  "error": {
    "code": "INVALID_AUDIO_FORMAT",
    "message": "Formato de áudio não suportado. Use WAV, MP3 ou OGG",
    "formato_recebido": "application/pdf"
  }
}
```

---

### 4. Análise de Imagem/Vídeo

Analisa imagens ou vídeos curtos para identificar expressões e sinais.

```
POST /analyze/image
```

**Content-Type**: `multipart/form-data`

#### Request

**Imagem:**
```bash
curl -X POST "http://localhost:8000/analyze/image" \
  -H "Content-Type: multipart/form-data" \
  -F "imagem=@foto_consulta.jpg" \
  -F "tipo=consulta" \
  -F "patient_id=uuid-anonimo-123"
```

**Vídeo (frames extraídos automaticamente):**
```bash
curl -X POST "http://localhost:8000/analyze/image" \
  -H "Content-Type: multipart/form-data" \
  -F "imagem=@consulta_video.mp4" \
  -F "tipo=consulta" \
  -F "patient_id=uuid-anonimo-123"
```

#### Campos do Formulário

| Campo | Tipo | Validação | Obrigatório | Descrição |
|-------|------|-----------|-------------|-----------|
| `imagem` | file | JPEG, PNG, MP4, max: 50MB | Sim | Arquivo de imagem ou vídeo |
| `tipo` | string | enum: [consulta, exame, outro] | Não | Tipo da mídia |
| `patient_id` | string | uuid | Não | ID anônimo |

**Nota sobre Vídeos:**
- Vídeos MP4 são aceitos (máximo 30 segundos)
- O sistema extrai automaticamente frames a cada 5 segundos
- Cada frame é analisado com Azure Computer Vision
- Resultados dos frames são combinados

#### Resposta 200 OK (Imagem)

```json
{
  "emoção_principal": "tristeza",
  "confiança": 0.89,
  "expressoes": ["evitando_olho", "expressao_tensa", "ombros_caidos"],
  "sinais_alertas": [],
  "risco_violencia": "medio",
  "risco_saude_mental": "alto",
  "metadata": {
    "correlation_id": "abc-123-xyz",
    "timestamp": "2026-04-05T14:30:00Z",
    "tempo_processamento_ms": 1200,
    "tipo": "imagem"
  }
}
```

#### Resposta 200 OK (Vídeo - frames combinados)

```json
{
  "emoção_principal": "tristeza",
  "confiança": 0.85,
  "expressoes": ["evitando_olho", "expressao_tensa"],
  "sinais_alertas": [],
  "risco_violencia": "medio",
  "risco_saude_mental": "alto",
  "analise_video": {
    "duracao_segundos": 15,
    "frames_analisados": 3,
    "emocoes_por_frame": [
      {"tempo": "0s", "emoção": "neutro", "confiança": 0.75},
      {"tempo": "5s", "emoção": "tristeza", "confiança": 0.88},
      {"tempo": "10s", "emoção": "tristeza", "confiança": 0.92}
    ]
  },
  "metadata": {
    "correlation_id": "abc-123-xyz",
    "timestamp": "2026-04-05T14:30:00Z",
    "tempo_processamento_ms": 4500,
    "tipo": "video"
  }
}
```

---

### 5. Análise Multimodal

Processa texto, áudio e imagem simultaneamente.

```
POST /analyze/multimodal
```

**Content-Type**: `multipart/form-data`

#### Request

```bash
curl -X POST "http://localhost:8000/analyze/multimodal" \
  -H "Content-Type: multipart/form-data" \
  -F "texto=Estou me sentindo muito ansiosa..." \
  -F "audio=@consulta.wav" \
  -F "imagem=@foto.jpg" \
  -F "patient_id=uuid-anonimo-123"
```

#### Campos do Formulário

| Campo | Tipo | Validação | Obrigatório | Descrição |
|-------|------|-----------|-------------|-----------|
| `texto` | string | min: 10, max: 5000 | Sim | Texto para análise |
| `audio` | file | max: 50MB | Sim | Arquivo de áudio |
| `imagem` | file | max: 20MB | Sim | Arquivo de imagem |
| `patient_id` | string | uuid | Não | ID anônimo |

**Nota**: Pelo menos uma modalidade deve ser enviada (texto, áudio ou imagem).

#### Resposta 200 OK

```json
{
  "fusao": {
    "risco_violencia": "alto",
    "risco_saude_mental": "alto",
    "confiança": 0.92,
    "alerta": true,
    "recomendacao": "Encaminhar para equipe multidisciplinar urgentemente"
  },
  "texto": {
    "sentimento": "negativo",
    "score": -0.85,
    "risco": "medio",
    "confiança": 0.75,
    "palavras_chave": ["ansiosa", "medo", "casa"]
  },
  "audio": {
    "transcricao": "Doutor, eu não sei se posso contar isso...",
    "sentimento": "negativo",
    "risco": "alto",
    "confiança": 0.88,
    "voz_tremida": true,
    "pausas_suspeitas": 3
  },
  "imagem": {
    "emoção": "tristeza",
    "risco": "medio",
    "confiança": 0.70,
    "expressoes": ["evitando_olho", "expressao_tensa"]
  },
  "metadata": {
    "correlation_id": "abc-123-xyz",
    "timestamp": "2026-04-05T14:30:00Z",
    "tempo_processamento_ms": 12500
  }
}
```

#### Resposta 400 Bad Request

```json
{
  "error": {
    "code": "MISSING_DATA",
    "message": "Pelo menos uma modalidade deve ser fornecida (texto, áudio ou imagem)"
  }
}
```

---

## Códigos de Erro

| Código | HTTP | Descrição |
|--------|------|-----------|
| `VALIDATION_ERROR` | 400 | Dados de entrada inválidos |
| `MISSING_DATA` | 400 | Dados obrigatórios não fornecidos |
| `INVALID_AUDIO_FORMAT` | 400 | Formato de áudio não suportado |
| `INVALID_IMAGE_FORMAT` | 400 | Formato de imagem não suportado |
| `TEXT_TOO_SHORT` | 400 | Texto muito curto (mínimo 10 caracteres) |
| `FILE_TOO_LARGE` | 400 | Arquivo excede tamanho máximo |
| `UNAUTHORIZED` | 401 | API Key inválida ou ausente |
| `RATE_LIMIT_EXCEEDED` | 429 | Limite de requisições excedido |
| `AZURE_SERVICE_ERROR` | 502 | Erro ao chamar serviço Azure |
| `INTERNAL_ERROR` | 500 | Erro interno do servidor |
| `QUOTA_EXCEEDED` | 429 | Quota do Azure Free Tier excedida |

---

## Exemplos de Uso

### Python

```python
import requests

# Análise de texto
response = requests.post(
    "http://localhost:8000/analyze/text",
    json={
        "texto": "Estou me sentindo muito ansiosa...",
        "tipo": "diario"
    }
)
result = response.json()
print(f"Risco: {result['risco_violencia']}")

# Análise multimodal
with open("consulta.wav", "rb") as audio, \
     open("foto.jpg", "rb") as imagem:
    response = requests.post(
        "http://localhost:8000/analyze/multimodal",
        data={"texto": "Texto aqui..."},
        files={
            "audio": audio,
            "imagem": imagem
        }
    )
    result = response.json()
    print(f"Alerta: {result['fusao']['alerta']}")
```

### cURL

```bash
# Health check
curl http://localhost:8000/health

# Análise de texto
curl -X POST http://localhost:8000/analyze/text \
  -H "Content-Type: application/json" \
  -d '{"texto":"Estou me sentindo ansiosa e com medo"}'

# Análise de áudio
curl -X POST http://localhost:8000/analyze/audio \
  -F "audio=@consulta.wav"
```

---

## Versionamento

A versão atual da API é **v1.0.0**.

Versão incluída em:
- Header `X-API-Version` nas respostas
- Campo `version` no endpoint `/health`
