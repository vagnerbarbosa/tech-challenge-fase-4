# 🏥💜 Tech Challenge Fase 4 - Sistema multimodal de análise de saúde da mulher usando Azure AI Services

[![Python](https://img.shields.io/badge/Python-3.11+-3776AB?style=flat-square&logo=python&logoColor=white)](https://www.python.org/)
[![FastAPI](https://img.shields.io/badge/FastAPI-0.115+-009688?style=flat-square&logo=fastapi&logoColor=white)](https://fastapi.tiangolo.com/)
[![Pydantic](https://img.shields.io/badge/Pydantic-v2-E92063?style=flat-square&logo=pydantic&logoColor=white)](https://docs.pydantic.dev/)
[![Azure](https://img.shields.io/badge/Azure%20AI-0089D6?style=flat-square&logo=microsoft-azure&logoColor=white)](https://azure.microsoft.com/)
[![YOLOv8](https://img.shields.io/badge/YOLOv8-Ultralytics-111F4D?style=flat-square&logo=ultralytics&logoColor=white)](https://ultralytics.com/)
[![Docker](https://img.shields.io/badge/Docker-2496ED?style=flat-square&logo=docker&logoColor=white)](https://www.docker.com/)
[![Poetry](https://img.shields.io/badge/Poetry-60A5FA?style=flat-square&logo=poetry&logoColor=white)](https://python-poetry.org/)
[![Ruff](https://img.shields.io/badge/Ruff-EF3939?style=flat-square&logo=ruff&logoColor=white)](https://docs.astral.sh/ruff/)
[![License](https://img.shields.io/badge/License-MIT-yellow.svg?style=flat-square)](LICENSE)

> **📅 Última Atualização**: 2026-05-01
> **✅ Status**: 4/4 Módulos Core + Deploy Azure Concluído (Texto + Áudio + Vídeo + Multimodal + Produção)

## Objetivo

**Realizar a análise e fusão de diferentes tipos de dados médicos específicos da saúde da mulher** — incluindo **texto, áudio e vídeo**.

### Opções Selecionadas:
1. ✅ **Detectar precocemente riscos em saúde materna e ginecológica**
2. ✅ **Identificar sinais de violência doméstica ou abuso**
3. ✅ **Utilizar serviços em nuvem** (Azure Free Tier)

### Foco do Projeto: Saúde Mental Feminina

Sistema multimodal para identificação de sinais de **violência doméstica** e **riscos à saúde materna** através da análise de:
- 📝 **Texto**: Prontuários, diários, relatórios
- 🎙️ **Áudio**: Consultas de telemedicina (voz)
- 🎥 **Vídeo/Imagem**: Análise de expressões faciais, linguagem corporal

---

## Visão Geral

Este projeto integra processamento de **texto, áudio e vídeo** para identificar precocemente:
- Sinais de violência doméstica em consultas médicas
- Riscos emocionais/psicológicos em gestantes
- Indicadores de estresse e ansiedade

### Tecnologias Multimodais:

| Tipo | Tecnologia | SDK Python | Uso |
|------|------------|------------|-----|
| **Texto** | Azure AI Language (Text Analytics) | `azure-ai-textanalytics` | Análise de sentimento, NLP |
| **Áudio** | Azure AI Speech | `azure-cognitiveservices-speech` | Transcrição + análise de voz |
| **Vídeo** | **YOLOv8** (local) | `ultralytics` + `opencv-python` | Detecção instrumentos, sangramento, postura |

> **Nota YOLOv8**: YOLOv8 roda **localmente no container** (custo zero), atendendo requisito obrigatório do PDF de "YOLOv8 customizado para instrumentos cirúrgicos, áreas críticas e sangramento anômalo". Aceita vídeos MP4 e imagens (processadas como vídeo de 1 frame).

> **Nota**: Azure Cognitive Services foi renomeado para **Azure AI Services** (2024) e agora faz parte do **Azure AI Foundry** (2025). O SDK `azure-cognitiveservices-vision-computervision` foi deprecated; usar `azure-ai-vision-imageanalysis`.

---

## Tecnologias

- **Framework**: FastAPI (Python 3.11+)
- **Cloud**: Azure AI Services (Free Tier) - **Deploy em produção obrigatório**
  - Azure App Service: Hospedagem API
  - Azure AI Speech: Transcrição (5h/mês free)
  - Azure AI Language: NLP (5k requests/mês free)
  - Azure SQL Database: Metadados (250GB free)
- **SDKs Azure**:
  - `azure-ai-textanalytics` 5.4.0 (Texto)
  - `azure-cognitiveservices-speech` 1.48.x (Áudio)
- **ML**: scikit-learn, transformers, **YOLOv8** (detecção objetos em vídeo)
- **Vídeo**: FFmpeg/OpenCV (extração de frames), **ultralytics** (YOLOv8 local)
- **Container**: Docker + Docker Compose
- **Testes**: pytest

> **ℹ️ Sobre o Rebranding**: Os serviços anteriormente chamados "Azure Cognitive Services" foram renomeados para **Azure AI Services** em 2024 e agora fazem parte do **Azure AI Foundry**. Os SDKs Python foram atualizados conforme lista acima.

---

## Como Executar

> 📖 **[Guia Completo de Execução](docs/RUNNING.md)** - Instruções detalhadas para:
> - Rodar localmente com Docker ou Poetry
> - Usar a API já hospedada no Azure
> - Exemplos de chamadas com autenticação

### Pré-requisitos

- **Docker e Docker Compose** (recomendado) ou **Python 3.11+ + Poetry**
- **Git**

> 💡 **Dica**: Use Docker para evitar problemas com dependências nativas (librosa, python-magic).

---

## Executar Localmente

```bash
# Clone e execute com Docker
git clone https://github.com/vagnerbarbosa/tech-challenge-fase-4.git
cd tech-challenge-fase-4
./scripts/run-mock.sh

# Teste
curl http://localhost:8000/health
```

Veja o [guia completo](docs/RUNNING.md) para outras opções (Docker manual, Poetry, Azure).

---

## 🚀 Deploy em Produção (Azure)

[![Deploy Status](https://img.shields.io/badge/Deploy-Azure%20Container%20Instances-0089D6?style=flat-square&logo=microsoft-azure)](http://20.226.196.195:8000/health)

✅ **API Online**: http://20.226.196.195:8000

A aplicação está hospedada em **Azure Container Instances** com CI/CD via GitHub Actions.

### Endpoints de Produção

| Endpoint | URL | Descrição |
|----------|-----|-----------|
| API Base | http://20.226.196.195:8000 | API principal |
| Health | http://20.226.196.195:8000/health | Status e quotas |
| Swagger | http://20.226.196.195:8000/docs | Documentação interativa |
| ReDoc | http://20.226.196.195:8000/redoc | Documentação alternativa |

### CI/CD Pipeline

Deploy automático a cada push na branch `main`:

1. **Build**: Docker multi-stage com cache
2. **Push**: Imagem para GitHub Container Registry (ghcr.io)
3. **Deploy**: Azure Container Instances atualizado
4. **Health Check**: Validação automática da API

### Collection Postman

Importe `docs/collection.json` e use o environment **"Azure Production"**:
```bash
curl http://20.226.196.195:8000/health
```

---

## Configurar Azure (Opcional)

**Principais variáveis:**

| Categoria | Variável | Descrição | Padrão |
|-----------|----------|-----------|--------|
| **Azure** | `AZURE_TEXT_KEY` / `AZURE_TEXT_ENDPOINT` | Azure AI Language (Text Analytics) | - |
| **Azure** | `AZURE_SPEECH_KEY` / `AZURE_SPEECH_REGION` | Azure AI Speech Services | `brazilsouth` |
| **App** | `APP_VERSION` | Versão da API | `0.6.0` |
| **App** | `DEBUG` | Modo debug (logs/docs) | `true` |
| **Rate Limit** | `RATE_LIMIT_ENABLED` | Proteção Azure Free Tier | `true` |
| **Rate Limit** | `MAX_TEXT_REQUESTS_PER_DAY` | Limite diário texto | `160` |
| **Rate Limit** | `MAX_SPEECH_MINUTES_PER_DAY` | Limite diário áudio | `10` |
| **Upload** | `MAX_UPLOAD_SIZE_MB` | Tamanho máximo arquivo | `50` |
| **Upload** | `ALLOWED_VIDEO_EXTENSIONS` | Formatos vídeo permitidos | `mp4,avi,mov` |
| **LGPD** | `DATA_RETENTION_DAYS` | Retenção de dados | `30` |
| **LGPD** | `ANONYMIZE_PII` | Anonimização de PII | `true` |

### Passo 3: Iniciar o Servidor

```bash
# Usando o script (recomendado)
./scripts/run.sh

# Ou comando Poetry direto
poetry run uvicorn src.api.main:app --reload --port 8000
```

### Passo 4: Testar

```bash
# Health check
curl http://localhost:8000/health

# Análise de texto
curl -X POST http://localhost:8000/analyze/text \
  -H "Content-Type: application/json" \
  -d '{"texto": "Estou me sentindo muito ansiosa e com medo"}'

# Ou use a interface Swagger
# Abra no navegador: http://localhost:8000/docs

# Ou importe as collections do Postman
# Arquivos: docs/collection.json e docs/environment.json
```

---

## Scripts Disponíveis

A pasta `/scripts` contém utilitários para facilitar o desenvolvimento:

| Script | Descrição | Uso |
|--------|-----------|-----|
| `setup.sh` | Configuração inicial do projeto | `./scripts/setup.sh` |
| `run-mock.sh` | Inicia com Docker + Mocks | `./scripts/run-mock.sh` |
| `run.sh` | Inicia localmente com Poetry | `./scripts/run.sh` |
| `test.sh` | Executa testes localmente | `./scripts/test.sh [unit\|integration\|coverage]` |
| `test-docker.sh` | Executa testes via Docker (recomendado) | `./scripts/test-docker.sh [unit\|coverage\|lint\|all]` |
| `lint.sh` | Verifica código (Ruff + mypy) | `./scripts/lint.sh` |
| `check-azure.sh` | Verifica credenciais Azure | `./scripts/check-azure.sh` |

**Nota para Windows:** Execute os scripts via Git Bash, WSL ou use `bash ./scripts/nome-do-script.sh`.

> 💡 **Dica**: Use sempre `./scripts/test-docker.sh` para testes! Ele garante um ambiente Linux consistente e evita problemas com dependências nativas no Windows.

---

## 🔒 Segurança

Esta API implementa hardening de segurança completo seguindo OWASP API Top 10 2023/2026 e LGPD compliance.

> 📖 **[Guia de Segurança](docs/technical/security-guide.md)** - Arquitetura de segurança, testes e deploy seguro

### Autenticação

Todas as rotas protegidas requerem autenticação via API Key:

```bash
# Gerar uma API Key segura
openssl rand -hex 32

# Configurar no .env
SECURITY_API_KEY=sua-key-aqui
SECURITY_ENVIRONMENT=production
```

**Uso nas requisições:**
```bash
curl -H "X-API-Key: sua-key-aqui" http://localhost:8000/health
```

### Rate Limiting

Proteção contra DDoS e brute force:

| Endpoint | Limite | Janela |
|----------|--------|--------|
| Geral | 60 req/min | 1 minuto |
| Auth | 5 req/min | 1 minuto |
| Health/Docs | Ilimitado | - |

**Headers de resposta:**
- `X-RateLimit-Limit`: Limite total
- `X-RateLimit-Remaining`: Requisições restantes
- `X-RateLimit-Reset`: Tempo até reset (segundos)

### Upload de Arquivos

Validações de segurança implementadas:
- ✅ **Magic Bytes**: Verificação real do tipo de arquivo (não apenas extensão)
- ✅ **Sanitização**: Remoção de path traversal (`../`)
- ✅ **Extensões**: Apenas formatos permitidos (WAV, MP3, OGG, MP4, AVI, MOV)
- ✅ **Tamanho**: Máximo 50MB por arquivo
- ✅ **Conteúdo**: Bloqueio de arquivos executáveis

### Headers de Segurança

Todos as respostas incluem headers OWASP:
- `Strict-Transport-Security`: HSTS (produção)
- `X-Content-Type-Options: nosniff`
- `X-Frame-Options: DENY`
- `Content-Security-Policy`: CSP restritivo
- `X-XSS-Protection: 1; mode=block`
- `Referrer-Policy: strict-origin-when-cross-origin`

### Auditoria LGPD

Logs de auditoria estruturados para compliance:
- 📁 Local: `logs/audit/`
- 📄 Formato: JSON Lines (NDJSON)
- 🔐 Integridade: SHA-256 checksums
- ⏱️ Retenção: 365 dias (configurável)
- 🛡️ Hash de PII: patient_id e IPs são hasheados

**Endpoints de admin:**
```bash
# Estatísticas de auditoria
GET /admin/audit/stats

# Exportação ANPD (LGPD)
GET /admin/audit/export?start_date=2026-01-01&end_date=2026-04-23

# Verificação de integridade
GET /admin/audit/verify
```

### CORS

Configuração restritiva com whitelist explícita:

```bash
# .env
SECURITY_CORS_ORIGINS="https://app-segura.com,https://app2.com"
```

- ❌ `*` nunca permitido em produção
- ✅ Preflight requests validados
- ✅ Warning em logs se CORS insecure

### Sanitização de Logs

Dados sensíveis são automaticamente mascarados:
- 🔑 API Keys
- 🔐 Azure credentials
- 🪪 Tokens JWT
- 📡 Connection strings
- 🔒 Private keys

### Dependências de Segurança

Para instalar dependências de segurança:
```bash
poetry install --extras security
```

Inclui:
- `slowapi`: Rate limiting
- `redis`: Backend distribuído para rate limit
- `python-magic`: Validação de magic bytes

---

## Testando a API

### Exemplo: Análise de Texto

```bash
curl -X POST http://localhost:8000/analyze/text \
  -H "Content-Type: application/json" \
  -d '{"texto": "Estou me sentindo ansiosa", "tipo": "diario"}'
```

**Resposta:**
```json
{
  "sentimento": "negativo",
  "risco_violencia": "alto",
  "risco_saude_mental": "alto",
  "palavras_chave": ["ansiosa"]
}
```

### Endpoints

| Endpoint | Método | Descrição |
|----------|--------|-----------|
| `/health` | GET | Health check com quotas Azure |
| `/ready` | GET | Readiness check (Kubernetes) |
| `/` | GET | Informações da API |
| `/docs` | GET | Swagger UI (documentação interativa) |
| `/analyze/text` | POST | Análise de texto |
| `/analyze/audio` | POST | Análise de áudio |
| `/analyze/audio/formats` | GET | Lista formatos de áudio suportados |
| `/analyze/video` | POST | Análise de vídeo YOLOv8 |
| `/analyze/video/formats` | GET | Lista formatos de vídeo suportados |

---

## Executando Testes

> 🔗 **Rápido**: [Por que Docker?](#-por-que-usar-docker-para-testes) | [Testes Unitários](#passo-2-executar-testes-unitários) | [Linting](#passo-3-executar-linting-e-type-check) | [Testes Locais](#-opção-alternativa-testes-locais-sem-docker)

### ⚠️ Por que usar Docker para testes?

Os testes deste projeto **dependem de bibliotecas nativas complexas** (especialmente `librosa` e `python-magic`) que podem apresentar problemas no Windows:

- **Librosa**: Requer FFmpeg para processamento de áudio
- **python-magic**: Depende da biblioteca system `libmagic` (Linux/Mac)
- **Segmentation faults**: Ocorrências comuns no Windows devido a incompatibilidades de bibliotecas C

**A solução**: Executar testes via Docker garante um ambiente Linux consistente e funcional.

---

### 🐳 Opção Recomendada: Testes via Docker

> 💡 **Opção mais fácil**: Use o script `./scripts/test-docker.sh` que automatiza todo o processo:
> ```bash
> # Testes unitários
> ./scripts/test-docker.sh unit
>
> # Todos os checks (lint + typecheck + testes)
> ./scripts/test-docker.sh all
>
> # Ver todas as opções
> ./scripts/test-docker.sh help
> ```

#### Executar Testes Unitários

```bash
# Executar todos os testes unitários (reutiliza imagem existente)
./scripts/test-docker.sh unit

# Executar testes com cobertura
./scripts/test-docker.sh coverage

# Executar testes específicos do módulo de áudio
docker run --rm \
  -v "$(pwd)/src:/app/src:ro" \
  -v "$(pwd)/tests:/app/tests:ro" \
  -w /app \
  tech-challenge-fase-4-api:latest \
  poetry run pytest tests/unit/services/test_audio_analysis.py -v
```

#### Executar Linting e Type Check

```bash
# Ruff linting + mypy type checking + testes
./scripts/test-docker.sh all

# Ou individualmente:
./scripts/test-docker.sh lint
./scripts/test-docker.sh typecheck
```

> **Nota sobre a imagem**: O script reutiliza automaticamente a imagem `tech-challenge-fase-4-api` (a mesma da API), economizando ~20GB de espaço. Se a imagem não existir, ela será buildada automaticamente via `run-mock.sh`. Use `./scripts/test-docker.sh rebuild` quando adicionar novos testes ou dependências.

#### Passo 4: Testes de Integração (requer API rodando)

```bash
# Iniciar a API em um container
docker-compose up -d api

# Executar testes de integração
docker run --rm --network=host health-api-test:latest \
  poetry run pytest tests/integration/ -v

# Parar a API
docker-compose down
```

---

### 💻 Opção Alternativa: Testes Locais (sem Docker)

> ⚠️ **Nota**: Esta opção pode apresentar erros no Windows devido a dependências nativas.

```bash
# Todos os testes
./scripts/test.sh

# Apenas testes unitários
./scripts/test.sh unit

# Testes de integração
./scripts/test.sh integration

# Com relatório de cobertura
./scripts/test.sh coverage
```

Ou diretamente com Poetry:
```bash
poetry run pytest tests/ -v --cov=src
```

---

## Verificação de Qualidade de Código

```bash
# Usando o script
./scripts/lint.sh

# Ou comandos individuais
poetry run ruff check src/ tests/
poetry run ruff format src/ tests/
poetry run mypy src/
```

---

## Endpoints

| Endpoint | Método | Status | Descrição | Tecnologia | Modalidade |
|----------|--------|--------|-----------|------------|------------|
| `/health` | GET | ✅ Implementado | Health check com quotas Azure | - | - |
| `/analyze/text` | POST | ✅ Implementado | Análise de sentimento e riscos | Azure AI Language | 📝 Texto |
| `/analyze/audio` | POST | ✅ Implementado | Transcrição + análise prosódica | Azure AI Speech + librosa | 🎙️ Áudio |
| `/analyze/audio/formats` | GET | ✅ Implementado | Lista formatos suportados | - | 🎙️ Áudio |
| `/analyze/audio/cache/stats` | GET | ✅ Implementado | Estatísticas do cache de áudio | - | 🎙️ Áudio |
| `/analyze/audio/cache/clear` | POST | ✅ Implementado | Limpa cache de áudio | - | 🎙️ Áudio |
| `/analyze/video` | POST | ✅ Implementado | Análise com YOLOv8 | YOLOv8 Local | 🎥 Vídeo |
| `/analyze/video/formats` | GET | ✅ Implementado | Lista formatos suportados | - | 🎥 Vídeo |
| `/analyze/video/cache/stats` | GET | ✅ Implementado | Estatísticas do cache de vídeo | - | 🎥 Vídeo |
| `/analyze/video/cache/clear` | POST | ✅ Implementado | Limpa cache de vídeo | - | 🎥 Vídeo |
| `/analyze/multimodal` | POST | ✅ Implementado | Fusão de 3 modalidades (late fusion) | Combinação | 📝🎙️🎥 |
| `/docs` | GET | ✅ Implementado | Documentação Swagger interativa | - | - |

**Legenda:**
- ✅ Implementado e testado
- 🔄 Parcialmente implementado
- ⏳ Pendente

---

## Exemplo de Uso

### Análise de Texto

```bash
curl -X POST "http://localhost:8000/analyze/text" \
  -H "Content-Type: application/json" \
  -d '{
    "texto": "Estou me sentindo muito ansiosa e tenho medo de falar sobre o que acontece em casa...",
    "tipo": "diario"
  }'
```

**Resposta:**
```json
{
  "sentimento": "negativo",
  "score": -0.85,
  "risco_violencia": "alto",
  "risco_saude_mental": "alto",
  "palavras_chave": ["ansiosa", "medo", "casa"],
  "indicadores": ["sinalizacao_isolamento", "expressao_medo"]
}
```

### Análise de Áudio

Analisa arquivos de áudio (WAV, MP3, OGG) extraindo transcrição e features prosódicas.

**Exemplo de Request:**
```bash
curl -X POST "http://localhost:8000/analyze/audio" \
  -H "Content-Type: multipart/form-data" \
  -F "file=@consulta.wav" \
  -F "patient_id=550e8400-e29b-41d4-a716-446655440000"
```

**Exemplo de Response:**
```json
{
  "transcricao": "Doutor, eu estou muito ansiosa e com medo quando ele chega em casa",
  "idioma_detectado": "pt-BR",
  "sentimento": "negativo",
  "entonação": "hesitante",
  "voz_tremida": true,
  "pausas_suspeitas": 3,
  "duracao_segundos": 32.5,
  "risco_violencia": "alto",
  "risco_saude_mental": "alto",
  "metadata": {
    "correlation_id": "audio-1234567890",
    "timestamp": "2026-04-12T14:30:00Z",
    "tempo_processamento_ms": 8200,
    "cache_hit": false,
    "azure_calls": 1
  }
}
```

**Parâmetros:**
| Campo | Tipo | Obrigatório | Descrição |
|-------|------|-------------|-----------|
| `file` | file | Sim | Arquivo de áudio (WAV, MP3, OGG) - máx 50MB |
| `patient_id` | string | Não | ID anônimo do paciente (UUID recomendado) |

**Features Extraídas:**
- ✅ Transcrição via Azure Speech Services
- ✅ Pitch analysis (detecção de voz tremida)
- ✅ Energy analysis (classificação: calmo/hesitante/agitado)
- ✅ Detecção de pausas suspeitas
- ✅ Análise de risco combinando texto + prosódia

### Análise de Vídeo (YOLOv8 Local) ✅ IMPLEMENTADO

Analisa vídeos (MP4, AVI, MOV) usando YOLOv8 localmente para detecção de objetos, instrumentos médicos e comportamento. Processamento em CPU com modelo YOLOv8n (nano, ~6MB).

**Exemplo de Request:**
```bash
curl -X POST "http://localhost:8000/analyze/video" \
  -H "Content-Type: multipart/form-data" \
  -F "video=@consulta.mp4" \
  -F "tipo=consulta" \
  -F "patient_id=550e8400-e29b-41d4-a716-446655440000"
```

**Exemplo de Response:**
```json
{
  "risco_violencia": "medio",
  "risco_saude_mental": "baixo",
  "detecoes": [
    {
      "classe": "person",
      "confianca": 0.9234,
      "bbox": {"x": 0.2341, "y": 0.1567, "w": 0.4532, "h": 0.6789},
      "frame": 1,
      "timestamp": 0.0
    },
    {
      "classe": "scissors",
      "confianca": 0.8765,
      "bbox": {"x": 0.5678, "y": 0.4321, "w": 0.1234, "h": 0.0876},
      "frame": 5,
      "timestamp": 5.0
    }
  ],
  "alertas": [
    {
      "tipo": "instrumento_cirurgico",
      "severidade": "media",
      "mensagem": "Instrumento cirúrgico detectado (scissors) com confiança 87.65%"
    }
  ],
  "metadata": {
    "correlation_id": "video-1234567890",
    "tempo_processamento_ms": 1250,
    "cache_hit": false,
    "frames_analisados": 12,
    "duracao_video_segundos": 60.0,
    "modelo": "yolov8n",
    "local_processing": true
  }
}
```

**Parâmetros:**
| Campo | Tipo | Obrigatório | Descrição |
|-------|------|-------------|-----------|
| `video` | file | Sim | Arquivo de vídeo (MP4, AVI, MOV) - máx 50MB |
| `tipo` | string | Não | Tipo de análise: `consulta`, `procedimento`, `exame` (padrão: consulta) |
| `patient_id` | string | Não | ID anônimo do paciente (UUID recomendado) |

**Features Extraídas:**
- ✅ Detecção de objetos via YOLOv8 (pessoas, tesouras, facas)
- ✅ Detecção de sangramento via análise de cor HSV
- ✅ Cálculo de risco de violência e saúde mental
- ✅ FPS adaptativo (1 FPS ≤30s, 0.2 FPS >30s)
- ✅ Cache de resultados para reprocessamento

**Limites:**
- Formatos: MP4, AVI, MOV
- Tamanho máximo: 50MB
- Duração máxima: 2 minutos
- Processamento local (sem custo Azure)

### Análise Multimodal ✅ IMPLEMENTADO

Processa texto, áudio e/ou vídeo em paralelo, combinando resultados via **late fusion ponderado por confiança**.

**Exemplo de Request (1 modalidade - texto):**
```bash
curl -X POST "http://localhost:8000/analyze/multimodal" \
  -H "Content-Type: multipart/form-data" \
  -F "texto=Estou me sentindo muito ansiosa e com medo"
```

**Exemplo de Request (3 modalidades):**
```bash
curl -X POST "http://localhost:8000/analyze/multimodal" \
  -H "Content-Type: multipart/form-data" \
  -F "texto=Estou me sentindo muito ansiosa" \
  -F "audio=@consulta.wav" \
  -F "video=@cirurgia.mp4"
```

**Exemplo de Response:**
```json
{
  "fusao": {
    "risco_violencia": "medio",
    "risco_saude_mental": "alto",
    "confiança": 0.75,
    "alerta": false,
    "recomendacao": "Acompanhamento prioritário recomendado",
    "scores_por_modalidade": {
      "texto": 0.5,
      "audio": 0.5,
      "video": 0.0
    }
  },
  "texto": {
    "sentimento": "negativo",
    "score": -0.85,
    "risco_violencia": "medio",
    "risco_saude_mental": "alto",
    ...
  },
  "audio": {
    "transcricao": "Estou muito ansiosa",
    "risco_violencia": "medio",
    ...
  },
  "video": {
    "risco_violencia": "baixo",
    ...
  },
  "metadata": {
    "correlation_id": "abc-123",
    "timestamp": "2026-04-21T14:30:00Z",
    "tempo_processamento_ms": 12500,
    "cache_hit": false,
    "azure_calls": 2,
    "modalidades_processadas": ["texto", "audio", "video"]
  }
}
```

**Parâmetros:**
| Campo | Tipo | Obrigatório | Descrição |
|-------|------|-------------|-----------|
| `texto` | string | Não | Texto para análise (10-5000 caracteres) |
| `audio` | file | Não | Arquivo de áudio (WAV, MP3, OGG) - máx 50MB |
| `video` | file | Não | Arquivo de vídeo (MP4, AVI, MOV) - máx 50MB |
| `patient_id` | string | Não | ID anônimo do paciente (UUID recomendado) |

**Regras:**
- Pelo menos uma modalidade deve ser fornecida
- Processamento paralelo com timeout de 30s por modalidade
- Se uma modalidade falhar, as demais continuam (graceful degradation)
- Vídeo não consome quota Azure (processamento local)

**Features:**
- ✅ Late fusion ponderado por confiança
- ✅ Alerta automático (2+ riscos altos ou confiança > 0.8)
- ✅ Recomendação clínica baseada no risco combinado
- ✅ Fallback para 1 modalidade (retorna resultado direto)
- ✅ Graceful degradation (continua se uma modalidade falhar)

---

## Modalidades de Dados

### 📝 Texto (Azure Text Analytics)

**Processamento:**
- Análise de sentimento
- Extração de entidades médicas
- Detecção de idioma
- Identificação de padrões de violência

**Exemplos de entrada:**
- Prontuários médicos
- Diários pessoais
- Relatos de consultas
- Questionários

### 🎙️ Áudio (Azure Speech Services)

**Processamento:**
- Speech-to-text (transcrição)
- Análise de entonação
- Detecção de pausas suspeitas
- Identificação de voz tremida

**Exemplos de entrada:**
- Gravações de consultas (com consentimento)
- Telemedicina
- Depoimentos

### 🎥 Vídeo/Imagem (YOLOv8 Local + OpenCV)

**Processamento:**
- **Vídeos**: Extração automática de frames (1 a cada 5s) + análise YOLOv8
- **Imagens**: Processadas como vídeo de 1 frame via YOLOv8
- Detecção de instrumentos cirúrgicos
- Detecção de sangramento anômalo
- Análise de linguagem corporal

**Exemplos de entrada:**
- Vídeos curtos de atendimento (MP4, max 30s)
- Fotos de consulta (JPEG, PNG)

---

## Azure Free Tier - Limites

| Serviço | Limite Free | Estimativa de Uso |
|---------|-------------|-------------------|
| Speech Services | 5h áudio/mês | ~300 consultas |
| Text Analytics | 5k requests/mês | Suficiente para MVP |
| SQL Database | 250GB | Metadados + logs |
| App Service | 60min CPU/dia | API contínua |
| Blob Storage | 5GB | Áudios + vídeos |

**Custo total: $0** (dentro do free tier)

> **💡 Nota sobre YOLOv8**: A análise de vídeo/imagem usa YOLOv8 local (dentro do container), consumindo **zero** da quota Azure AI Vision.

### 🔒 Proteção Contra Custos (Hard Stop)

O sistema implementa uma **estratégia de hard stop** que garante **zero custos**:

- **Contadores internos** por serviço (Texto, Áudio)
- **Interrupção automática** quando quotas forem atingidas
- **Retorno HTTP 503** com informação de retry
- **Reset automático** às 00:00 UTC

> Ver detalhes em: [`specs/006-rate-limiting/spec.md`](specs/006-rate-limiting/spec.md)

---

## Testes

⚠️ **Importante**: Veja a seção [Executando Testes](#executando-testes) acima para instruções detalhadas.

### 🚀 Modo Fácil (Script Recomendado)

```bash
# Executar via script (faz build e roda testes automaticamente)
./scripts/test-docker.sh unit        # Testes unitários
./scripts/test-docker.sh coverage    # Com cobertura
./scripts/test-docker.sh all         # Lint + typecheck + testes
./scripts/test-docker.sh help        # Ver todas as opções
```

### Comandos Manuais (Docker)

```bash
# Build e execução completa
./scripts/test-docker.sh coverage  # Reutiliza imagem existente (economiza ~20GB)
```

### Comandos Locais (sem Docker)

```bash
# Testes unitários e integração
poetry run pytest -v

# Testes de carga (Locust)
cd tests/load
poetry run locust -f locustfile.py
```

---

## Documentação

### Guias de Uso

| Documento | Descrição | Público |
|-----------|-----------|---------|
| [Como Executar](docs/RUNNING.md) | Passo a passo para rodar localmente ou usar Azure | Todos |
| [Segurança](docs/technical/security-guide.md) | Arquitetura de segurança e deploy seguro | DevOps/SRE |
| [Compliance](docs/technical/compliance-analysis.md) | Análise LGPD e OWASP | Arquitetos |

### Specs Kit (Status)

| ID | Feature | Status | Link |
|----|---------|--------|------|
| 001 | Bootstrap do Projeto | ✅ Concluído | [spec.md](specs/001-bootstrap/spec.md) |
| 002 | Análise de Texto | ✅ Concluído | [spec.md](specs/002-text-analysis/spec.md) |
| 003 | Análise de Áudio | ✅ Concluído | [spec.md](specs/003-audio-analysis/spec.md) |
| 004 | Análise de Vídeo (YOLOv8) | ✅ Concluído | [spec.md](specs/004-video-analysis/spec.md) |
| 005 | Fusão Multimodal | ✅ Concluído | [spec.md](specs/005-multimodal-fusion/spec.md) |
| 006 | Rate Limiting | ✅ Concluído | [spec.md](specs/006-rate-limiting/spec.md) |
| 007 | Security Hardening | 🔄 Parcial | [spec.md](specs/007-security-hardening/spec.md) |
| 008 | Testes Automatizados | ✅ Concluído | [spec.md](specs/008-tests/spec.md) |
| 009 | Deploy Azure | ⏳ Pendente | [spec.md](specs/009-deploy-azure/spec.md) |
| 010 | Documentação Final | ⏳ Pendente | [spec.md](specs/010-documentation/spec.md) |

### Outros Documentos
- [📋 Índice de Especificações](specs/README.md)
- [📊 Context7 - Melhores Práticas](docs/technical/context7-best-practices.md)

---

## Vídeo de Demonstração

📹 [Assista ao vídeo de demonstração no YouTube](https://www.youtube.com/watch?v=dQw4w9WgXcQ)

O vídeo demonstra:
- Arquitetura multimodal
- Análise de texto, áudio e vídeo
- Identificação de sinais de alerta
- Dashboard de resultados
- Deploy na Azure

---

## Collection API

Arquivos de coleção compatíveis com **Postman**, **Insomnia** e **Bruno** estão disponíveis em `docs/`.

### Arquivos

- **`docs/collection.json`**: Coleção com todos os endpoints da API
- **`docs/environment.json`**: Variáveis de ambiente (`base_url`, `api_key`)

### Como Importar

#### Postman
1. File → Import → Upload Files
2. Selecione `docs/collection.json` e `docs/environment.json`
3. Clique em "Import"
4. Selecione o environment "Multimodal Health Analysis API" no dropdown superior direito

#### Insomnia
1. Application → Preferences → Data → Import Data
2. Selecione "From File"
3. Escolha `docs/collection.json`
4. Repita para `docs/environment.json`

#### Bruno
1. Collections → Import Collection
2. Selecione "Postman Collection"
3. Escolha o arquivo `docs/collection.json`
4. Para o environment, use: Environments → Create Environment e importe `docs/environment.json`

### Variáveis de Ambiente

| Variável | Descrição | Padrão |
|----------|-----------|--------|
| `{{base_url}}` | URL base da API | `http://localhost:8000` |
| `{{api_key}}` | Chave de API | `test-api-key` |

---

## Estrutura do Projeto

```
tech-challenge-fase-4/
├── src/                      # Código fonte
│   ├── api/                  # FastAPI app e rotas
│   │   ├── main.py                # Ponto de entrada FastAPI
│   │   └── routes/
│   │       ├── health.py          # Health check com quotas Azure
│   │       ├── text.py            # Análise de texto (✅ Task 002)
│   │       ├── audio.py           # Análise de áudio (✅ Task 003)
│   │       ├── video.py           # Análise de vídeo YOLOv8 (✅ Task 004)
│   │       ├── multimodal.py      # Fusão multimodal (✅ Task 005)
│   │       └── dependencies.py    # Injeção de dependências
│   ├── core/                 # Configurações, logging, exceções
│   │   ├── config.py              # Configurações da aplicação (Pydantic Settings)
│   │   ├── logging_config.py      # Logging estruturado (structlog)
│   │   ├── exceptions.py          # Exceções customizadas da aplicação
│   │   ├── cache.py               # Cache em memória com TTL
│   │   ├── rate_limit.py          # QuotaManager - proteção Azure Free Tier (✅ Task 006)
│   │   └── temp_file_manager.py   # Gerenciamento LGPD-compliant de arquivos temporários
│   ├── services/             # Lógica de negócio
│   │   ├── text_analysis.py       # Serviço de análise de texto Azure
│   │   ├── audio_analysis.py      # Serviço de análise de áudio (✅ Task 003)
│   │   ├── video_analysis.py      # Análise de vídeo com YOLOv8 (✅ Task 004)
│   │   ├── multimodal_fusion.py   # Serviço de fusão multimodal (✅ Task 005)
│   │   ├── video_processor.py     # Processamento de frames de vídeo
│   │   ├── yolo_service.py        # Serviço YOLOv8 local
│   │   ├── bleeding_detector.py   # Detecção de sangramento via HSV
│   │   ├── posture_analyzer.py    # Análise de postura/locomoção
│   │   ├── risk_calculator_video.py # Cálculo de risco para vídeo
│   │   └── risk_detector.py       # Detecção unificada de risco
│   ├── models/               # Schemas Pydantic
│   │   └── schemas.py             # Modelos de request/response
│   ├── infrastructure/       # Clientes Azure e externo
│   │   ├── azure_clients.py       # Client Azure AI Language (Text Analytics)
│   │   └── azure_speech_client.py # Client Azure Speech (✅ Task 003)
│   └── utils/                # Helpers e utilitários
│       ├── file_validation.py     # Validação de uploads (MIME, magic bytes)
│       └── text_utils.py          # Utilitários de processamento de texto
├── tests/                    # Testes
│   ├── unit/                 # Testes unitários
│   │   ├── core/                  # Testes de cache, temp manager
│   │   ├── services/              # Testes de todos os serviços
│   │   │   ├── test_text_analysis.py
│   │   │   ├── test_audio_analysis.py
│   │   │   ├── test_video_analysis.py
│   │   │   ├── test_yolo_service.py
│   │   │   ├── test_video_processor.py
│   │   │   ├── test_bleeding_detector.py
│   │   │   ├── test_posture_analyzer.py
│   │   │   └── test_risk_calculator_video.py
│   │   ├── utils/                 # Testes de utilitários
│   │   └── infrastructure/        # Testes de clientes Azure
│   ├── integration/          # Testes de integração (end-to-end)
│   │   ├── test_text_endpoint.py
│   │   ├── test_audio_endpoint.py
│   │   ├── test_video_endpoint.py
│   │   └── test_azure_services.py
│   └── load/                 # Testes de carga (Locust)
├── specs/                    # Especificações Spec Kit
│   ├── 001-bootstrap/        # ✅ Concluído
│   ├── 002-text-analysis/      # ✅ Concluído
│   ├── 003-audio-analysis/     # ✅ Concluído
│   ├── 004-video-analysis/     # ✅ Concluído
│   ├── 005-multimodal-fusion/  # ✅ Concluído
│   ├── 006-rate-limiting/      # ✅ Concluído
│   ├── 007-security-hardening/ # 🔄 Parcial
│   ├── 008-tests/              # ✅ Concluído
│   ├── 009-deploy-azure/       # ⏳ Pendente
│   └── 010-documentation/        # ⏳ Pendente
├── docs/                     # Documentação
│   └── technical/
├── .claude/                  # Configuração Claude Code
├── .specify/                 # Configuração Spec Kit
├── docker-compose.yml
├── docker-compose.mock.yml
├── Dockerfile                # Multi-stage production
├── scripts/test-docker.sh    # Script para testes (reutiliza imagem da API, economiza ~20GB)
└── README.md
```

---

## ⚠️ Notas Importantes

- **Consentimento**: Todos os dados de áudio/vídeo devem ter consentimento explícito
- **LGPD**: Dados sensíveis são anonimizados antes do processamento
- **Ética**: Sistema é ferramenta de apoio, não substitui julgamento médico
- **Free Tier**: Monitorar uso para não ultrapassar limites Azure

---

## Integrantes do Grupo 27

Este projeto é desenvolvido pela mesma equipe das Fases 1, 2 e 3:

| Nome | GitHub |
|------|--------|
| Adriel Santos | [@AdrielCandido](https://github.com/AdrielCandido) |
| Leticia Nepomuceno | [@LeticiaNepomucena](https://github.com/LeticiaNepomucena) |
| Lucas Silva | [@lucfsilva](https://github.com/lucfsilva) |
| Vagner Barbosa | [@vagnerbarbosa](https://github.com/vagnerbarbosa) |

**Curso**: FIAP/Alura - AI para Devs (IADT)
**Fase**: 4 (Análise Multimodal de Dados em Saúde da Mulher)

---

## Fases Anteriores

- [Fase 1 - Diabetes Prediction](https://github.com/vagnerbarbosa/tech-challenge-fase-1)
- [Fase 2 - Otimização com Algoritmos Genéticos](https://github.com/vagnerbarbosa/tech-challenge-fase-2)
- [Fase 3 - Assistente Virtual Médico](https://github.com/vagnerbarbosa/tech-challenge-fase-3)

---

## Licença

MIT License - Copyright (c) 2026 Grupo 27 Tech Challenge
