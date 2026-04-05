# PRD Técnico - Sistema Multimodal de Análise de Saúde da Mulher

**Versão**: 1.0.0
**Data**: 2026-04-05
**Projeto**: Tech Challenge Fase 4 - FIAP/Alura AI para Devs
**Status**: Pronto para Implementação

---

## 1. Visão Geral do Produto

### 1.1 Objetivo Principal

**"Realizar a análise e fusão de diferentes tipos de dados médicos específicos da saúde da mulher — incluindo texto, áudio e vídeo."**

### 1.2 Escopo do MVP

Sistema **multimodal** que processa **texto, áudio e vídeo** para identificar precocemente:
- Sinais de **violência doméstica**
- Riscos emocionais/psicológicos em **gestantes**
- Indicadores de **saúde mental feminina**

### 1.3 Stack Tecnológica Final

| Camada | Tecnologia | Versão/Config |
|--------|------------|---------------|
| **Framework** | FastAPI | 0.104.0+ (async) |
| **Runtime** | Python | 3.11+ |
| **Package Manager** | Poetry | - |
| **Text Analytics** | Azure AI Language | `azure-ai-textanalytics` 5.4.0+ |
| **Speech** | Azure AI Speech | `azure-cognitiveservices-speech` 1.48.0+ |
| **Vision** | Azure AI Vision | `azure-ai-vision-imageanalysis` 1.0.0+ |
| **Database** | SQLite / Azure SQL | Dev / Prod |
| **Cache** | Redis (opcional) | 7-alpine |
| **Video Processing** | OpenCV + FFmpeg | 4.8.0+ |
| **Container** | Docker + Docker Compose | Multi-stage |
| **Testing** | pytest | Async, cov > 70% |

### 1.4 Arquitetura de Alto Nível

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                              CLIENTES                                        │
│  (Médicos, Enfermeiros, Sistemas de Saúde)                                  │
└─────────────────────────────────────────────────────────────────────────────┘
                                     │
                                     ▼
┌─────────────────────────────────────────────────────────────────────────────┐
│                           API REST (FastAPI)                                 │
│  ┌──────────────┐ ┌──────────────┐ ┌──────────────┐ ┌──────────────┐         │
│  │  /analyze/   │ │  /analyze/   │ │  /analyze/   │ │  /analyze/   │         │
│  │    text      │ │   audio      │ │   image      │ │  multimodal  │         │
│  └──────────────┘ └──────────────┘ └──────────────┘ └──────────────┘         │
│                                                                             │
│  ┌─────────────────────────────────────────────────────────────────────┐   │
│  │                         MIDDLEWARE                                   │   │
│  │  • Rate Limit  • Quota Protection  • Validation  • Error Handling   │   │
│  └─────────────────────────────────────────────────────────────────────┘   │
│                                                                             │
│  ┌─────────────────────────────────────────────────────────────────────┐   │
│  │                         SERVICES                                     │   │
│  │  ┌─────────────┐ ┌─────────────┐ ┌─────────────┐ ┌─────────────┐      │   │
│  │  │TextAnalysis │ │AudioAnalysis│ │ImageAnalysis│ │  Fusion     │      │   │
│  │  │  Service    │ │  Service    │ │  Service    │ │  Service    │      │   │
│  │  └─────────────┘ └─────────────┘ └─────────────┘ └─────────────┘      │   │
│  └─────────────────────────────────────────────────────────────────────┘   │
└─────────────────────────────────────────────────────────────────────────────┘
       │              │                │              │
       ▼              ▼                ▼              ▼
┌──────────────┐ ┌──────────────┐ ┌──────────────┐ ┌──────────────┐
│   Azure      │ │   Azure      │ │   Azure      │ │   SQLite/    │
│   AI         │ │   AI         │ │   AI         │ │   Azure      │
│   Language   │ │   Speech     │ │   Vision     │ │   SQL        │
│              │ │              │ │              │ │              │
│  Sentiment   │ │  Speech-to-  │ │  Face        │ │  Metadata    │
│  Analysis    │ │  Text        │ │  Analysis    │ │  Storage     │
│              │ │              │ │              │ │              │
│  Free: 5k    │ │  Free: 5h    │ │  Free: 5k    │ │  Free: 250GB │
│  req/mês     │ │  áudio/mês   │ │  trans/mês   │ │              │
└──────────────┘ └──────────────┘ └──────────────┘ └──────────────┘
```

---

## 2. Requisitos Técnicos

### 2.1 Requisitos Funcionais (RF)

| ID | Requisito | Endpoint | Azure Service | Prioridade |
|----|-----------|----------|---------------|------------|
| RF01 | Análise de Texto | POST `/analyze/text` | AI Language | Must |
| RF02 | Análise de Áudio | POST `/analyze/audio` | AI Speech | Must |
| RF03 | Análise de Imagem/Vídeo | POST `/analyze/image` | AI Vision | Must |
| RF04 | Análise Multimodal | POST `/analyze/multimodal` | Fusão | Must |
| RF05 | Health Check | GET `/health` | - | Must |

### 2.2 Campos Obrigatórios em TODAS Respostas

```python
{
  "risco_violencia": "baixo" | "medio" | "alto",      # OBRIGATÓRIO
  "risco_saude_mental": "baixo" | "medio" | "alto",   # OBRIGATÓRIO
  "metadata": {
    "correlation_id": "uuid",
    "timestamp": "ISO8601",
    "tempo_processamento_ms": int
  }
}
```

### 2.3 Requisitos Não-Funcionais (RNF)

| ID | Requisito | Métrica | Prioridade |
|----|-----------|---------|------------|
| RNF01 | Latência texto | < 2s | Must |
| RNF02 | Latência áudio | < 10s (arquivo 1min) | Must |
| RNF03 | Latência imagem | < 5s | Must |
| RNF04 | Disponibilidade | ≥ 99% | Must |
| RNF05 | Segurança | LGPD compliant | Must |
| RNF06 | Cobertura testes | > 70% | Must |
| RNF07 | Hard Stop Free Tier | Zero custo garantido | Must |

---

## 3. Especificação de Endpoints

### 3.1 Resumo dos Endpoints

| Método | Endpoint | Descrição | Content-Type |
|--------|----------|-----------|--------------|
| GET | `/health` | Health check + status Azure | JSON |
| POST | `/analyze/text` | Análise de texto | `application/json` |
| POST | `/analyze/audio` | Análise de áudio | `multipart/form-data` |
| POST | `/analyze/image` | Análise imagem/vídeo | `multipart/form-data` |
| POST | `/analyze/multimodal` | Fusão de 3 modalidades | `multipart/form-data` |

### 3.2 Contratos de API Detalhados

Ver arquivo completo: [`docs/api-contracts.md`](docs/api-contracts.md)

### 3.3 Schema Base de Resposta

Todos os endpoints de análise retornam obrigatoriamente:

```json
{
  "risco_violencia": "baixo|medio|alto",
  "risco_saude_mental": "baixo|medio|alto",
  "metadata": { ... }
}
```

---

## 4. Azure Free Tier - Gestão de Limites

### 4.1 Limites por Serviço

| Serviço | Limite Mensal | Limite Diário (Conservador) | SDK Python |
|---------|---------------|----------------------------|------------|
| **Azure AI Language** | 5,000 requests | 160 | `azure-ai-textanalytics` 5.4.0+ |
| **Azure AI Speech** | 5 hours (300 min) | 10 min | `azure-cognitiveservices-speech` 1.48.0+ |
| **Azure AI Vision** | 5,000 transactions | 160 | `azure-ai-vision-imageanalysis` 1.0.0+ |
| **App Service F1** | 60 min CPU/day | - | - |
| **Blob Storage** | 5GB | - | `azure-storage-blob` 12.x+ |

### 4.2 Estratégia de Hard Stop

Implementar proteção de quota em 3 camadas:

```python
# Camada 1: Azure Spending Limit (automático)
# - Desabilita subscription quando créditos acabam

# Camada 2: Application Rate Limiter
# - Contador por serviço (Redis/SQLite)
# - Thresholds: 80% = Alerta, 100% = Hard Stop

# Camada 3: Circuit Breaker Pattern
# - Retorna HTTP 503 quando quota excedida
# - Reset automático às 00:00 UTC
```

Ver implementação completa: [`docs/technical/azure-free-tier-hard-stop.md`](docs/technical/azure-free-tier-hard-stop.md)

---

## 5. Arquitetura de Componentes

### 5.1 Estrutura de Diretórios

```
tech-challenge-fase-4/
├── src/
│   ├── api/
│   │   ├── main.py                 # FastAPI app factory
│   │   ├── dependencies.py         # Injeção de dependências
│   │   ├── middleware.py           # Rate limiting, logging
│   │   ├── routes/
│   │   │   ├── health.py          # GET /health
│   │   │   ├── text.py            # POST /analyze/text
│   │   │   ├── audio.py           # POST /analyze/audio
│   │   │   ├── image.py           # POST /analyze/image
│   │   │   └── multimodal.py      # POST /analyze/multimodal
│   │   └── exceptions.py          # Exception handlers
│   ├── core/
│   │   ├── config.py              # Pydantic Settings
│   │   ├── rate_limiter.py        # QuotaManager + Hard Stop
│   │   ├── logging_config.py      # Logging estruturado
│   │   └── security.py            # LGPD compliance
│   ├── services/
│   │   ├── text_analysis.py      # Azure AI Language
│   │   ├── audio_analysis.py      # Azure AI Speech
│   │   ├── image_analysis.py      # Azure AI Vision
│   │   ├── video_frame_extractor.py  # FFmpeg/OpenCV
│   │   └── fusion.py              # Late Fusion logic
│   ├── models/
│   │   ├── schemas.py             # Pydantic Models
│   │   ├── requests.py            # Request schemas
│   │   └── responses.py           # Response schemas
│   ├── infrastructure/
│   │   └── azure_clients.py       # AzureClientFactory
│   └── utils/
│       └── helpers.py             # Utilitários
├── tests/
│   ├── unit/
│   │   ├── test_text_analysis.py
│   │   ├── test_audio_analysis.py
│   │   ├── test_image_analysis.py
│   │   └── test_fusion.py
│   ├── integration/
│   │   ├── test_api.py
│   │   └── test_azure_services.py
│   └── load/
│       └── locustfile.py          # Load testing
├── docs/
│   └── (documentação existente)
├── tasks/
│   ├── 001-bootstrap.md
│   ├── 002-health-endpoint.md
│   ├── 003-text-analysis.md
│   ├── 004-audio-analysis.md
│   ├── 005-image-analysis.md
│   ├── 006-multimodal-fusion.md
│   ├── 007-rate-limiting.md
│   ├── 008-tests.md
│   ├── 009-deploy-azure.md
│   └── 010-documentation.md
├── pyproject.toml
├── Dockerfile
├── docker-compose.yml
└── README.md
```

### 5.2 Componentes Principais

#### 5.2.1 QuotaManager (Rate Limiting + Hard Stop)

```python
# src/core/rate_limiter.py
class QuotaManager:
    """Gerenciador de quotas com hard stop automático"""

    FREE_TIER_LIMITS = {
        ServiceType.TEXT_ANALYTICS: {"daily": 160, "monthly": 5000},
        ServiceType.SPEECH: {"daily_minutes": 10, "monthly_minutes": 300},
        ServiceType.VISION: {"daily": 160, "monthly": 5000}
    }

    async def check_and_increment(self, service: ServiceType, count: int = 1) -> bool:
        # Verifica quota
        # Se excedida: trigger_hard_stop() → HTTP 503
        # Se OK: incrementa contador → retorna True
```

#### 5.2.2 Services

```python
# src/services/text_analysis.py
class TextAnalysisService:
    async def analyze(self, text: str) -> TextAnalysisResult:
        # 1. Validação de entrada
        # 2. Chamar Azure AI Language
        # 3. Processamento local (padrões de risco)
        # 4. Calcular risco_violencia, risco_saude_mental
        # 5. Retornar resultado

# src/services/audio_analysis.py
class AudioAnalysisService:
    async def analyze(self, audio_file: UploadFile) -> AudioAnalysisResult:
        # 1. Validar formato (WAV, MP3, OGG)
        # 2. Salvar temporariamente
        # 3. Chamar Azure AI Speech (STT)
        # 4. Analisar transcrição (pausas, entonação)
        # 5. Calcular risco_violencia, risco_saude_mental
        # 6. Deletar arquivo (LGPD)

# src/services/image_analysis.py
class ImageAnalysisService:
    async def analyze(self, image_file: UploadFile) -> ImageAnalysisResult:
        # 1. Validar formato (JPEG, PNG, MP4)
        # 2. Se vídeo: extrair frames (OpenCV)
        # 3. Analisar com Azure AI Vision
        # 4. Calcular risco_violencia, risco_saude_mental
        # 5. Deletar arquivo (LGPD)

# src/services/fusion.py
class FusionService:
    async def analyze(self, text, audio, image) -> MultimodalResult:
        # 1. Processar em paralelo (asyncio.gather)
        # 2. Late Fusion: combinar scores
        # 3. Calcular risco combinado
        # 4. Gerar alerta se necessário
```

---

## 6. Pipeline de Implementação

### 6.1 Roadmap de Features

| Task | Feature | Pontos | Dependências | Status |
|------|---------|--------|--------------|--------|
| **001** | Bootstrap (Poetry, Docker, Config) | 8 | - | ✅ **Concluída** |
| **002** | Health Endpoint | 3 | 001 | 🟡 Em progresso |
| **003** | Text Analysis (Azure AI Language) | 8 | 001, 002 | 🔴 Não iniciado |
| **004** | Audio Analysis (Azure AI Speech) | 8 | 001, 002 | 🔴 Não iniciado |
| **005** | Image Analysis (Azure AI Vision) | 8 | 001, 002 | 🔴 Não iniciado |
| **006** | Multimodal Fusion | 13 | 003, 004, 005 | 🔴 Não iniciado |
| **007** | Rate Limiting + Hard Stop | 3 | 001 | 🔴 Não iniciado |
| **008** | Tests (Unit + Integration + Load) | 8 | 001-007 | 🔴 Não iniciado |
| **009** | Deploy Azure (Free Tier) | 10 | 001-008 | 🔴 Não iniciado |
| **010** | Documentation + Video | 5 | 001-009 | 🔴 Não iniciado |

**Total**: 74 pontos

### 6.2 Sequência de Implementação Recomendada

```
Semana 1: Fundação
├── Task 001: Bootstrap
│   ├── Poetry init
│   ├── Dependências (Azure SDKs)
│   ├── Dockerfile multi-stage
│   ├── docker-compose.yml
│   └── Configuração Ruff + mypy + pytest
│
├── Task 002: Health Endpoint
│   ├── FastAPI app base
│   ├── GET /health
│   └── Tests
│
└── Task 007: Rate Limiting (parte 1)
    ├── QuotaManager estrutura base
    └── Middleware inicial

Semana 2: Serviços Individuais
├── Task 003: Text Analysis
│   ├── Azure AI Language integration
│   ├── POST /analyze/text
│   └── Pattern detection local
│
├── Task 004: Audio Analysis
│   ├── Azure AI Speech integration
│   ├── POST /analyze/audio
│   ├── Upload file handling
│   └── Voice analysis (pausas, entonação)
│
└── Task 005: Image Analysis
    ├── Azure AI Vision integration
    ├── POST /analyze/image
    ├── Video frame extraction
    └── Image upload handling

Semana 3: Integração e Testes
├── Task 006: Multimodal Fusion
│   ├── Late fusion implementation
│   ├── POST /analyze/multimodal
│   └── Parallel processing
│
├── Task 007: Rate Limiting (completo)
│   ├── QuotaManager completo
│   ├── Hard stop implementation
│   └── Circuit breaker
│
└── Task 008: Tests
    ├── Unit tests (> 70%)
    ├── Integration tests
    └── Load tests (Locust)

Semana 4: Deploy e Finalização
├── Task 009: Deploy Azure
│   ├── Azure App Service (F1)
│   ├── Configuração variáveis
│   └── CI/CD (opcional)
│
└── Task 010: Documentation
    ├── README final
    ├── Vídeo demonstrativo (YouTube)
    └── Ajustes finais
```

---

## 7. Dependências Python (pyproject.toml)

```toml
[tool.poetry.dependencies]
python = "^3.11"
fastapi = "^0.104.0"
uvicorn = {extras = ["standard"], version = "^0.24.0"}
python-multipart = "^0.0.6"
pydantic = {extras = ["settings"], version = "^2.5.0"}
pydantic-settings = "^2.1.0"

# Azure AI Services (Foundry Tools)
azure-ai-textanalytics = "^5.4.0"           # Texto/Sentimento
azure-cognitiveservices-speech = "^1.48.0"  # Áudio/Speech-to-Text
azure-ai-vision-imageanalysis = "^1.0.0"      # Imagem/Vídeo
azure-storage-blob = "^12.19.0"             # Storage temporário

# Video Processing
opencv-python = "^4.8.1"
ffmpeg-python = "^0.2.0"

# Database
sqlalchemy = {extras = ["asyncpg"], version = "^2.0.0"}
aiosqlite = "^0.19.0"

# Cache (opcional)
redis = {extras = ["hiredis"], version = "^5.0.0", optional = true}

# Security
python-jose = {extras = ["cryptography"], version = "^3.3.0"}
python-dotenv = "^1.0.0"

# Observability
structlog = "^23.2.0"
prometheus-client = "^0.19.0"

[tool.poetry.dev-dependencies]
pytest = "^7.4.0"
pytest-asyncio = "^0.21.0"
pytest-cov = "^4.1.0"
httpx = "^0.25.0"
respx = "^0.20.0"
ruff = "^0.1.6"
mypy = "^1.7.0"
locust = "^2.18.0"
```

---

## 8. Configuração de Ambiente (.env.example)

```bash
# Azure AI Language (Text Analytics)
AZURE_TEXT_KEY=your_text_analytics_key_here
AZURE_TEXT_ENDPOINT=https://<resource>.cognitiveservices.azure.com/

# Azure AI Speech
AZURE_SPEECH_KEY=your_speech_key_here
AZURE_SPEECH_REGION=brazilsouth

# Azure AI Vision
AZURE_VISION_KEY=your_vision_key_here
AZURE_VISION_ENDPOINT=https://<resource>.cognitiveservices.azure.com/

# Azure Blob Storage (opcional, para arquivos temporários)
AZURE_STORAGE_CONNECTION_STRING=your_connection_string_here
AZURE_STORAGE_CONTAINER=temp-files

# Database
DATABASE_URL=sqlite+aiosqlite:///./health_analysis.db
# Para PostgreSQL: postgresql+asyncpg://user:pass@localhost/db

# Redis (opcional, para cache e rate limiting)
REDIS_URL=redis://localhost:6379/0

# App Configuration
APP_NAME="Multimodal Health Analysis API"
APP_VERSION=1.0.0
ENVIRONMENT=development
DEBUG=false
LOG_LEVEL=INFO

# Security
SECRET_KEY=your-secret-key-here

# LGPD / Retention
FILE_RETENTION_HOURS=24
LOG_RETENTION_DAYS=30
MAX_FILE_SIZE_MB=50
```

---

## 9. Critérios de Aceite por Task

### Task 001: Bootstrap ✅
- [x] `poetry install` funciona sem erros
- [x] `docker-compose up --build` inicia a aplicação
- [x] `pytest` executa (mesmo sem testes ainda)
- [x] `ruff check .` passa
- [x] `mypy src/` passa
- [x] Estrutura de diretórios completa

**Status**: Concluída em 2026-04-05 (PR #7)

### Task 002: Health Endpoint
- [ ] GET `/health` retorna 200
- [ ] Retorna versão, timestamp, status dos serviços Azure
- [ ] Retorna quota restante (mockado se necessário)
- [ ] Testes unitários passam

### Task 003: Text Analysis
- [ ] POST `/analyze/text` aceita JSON válido
- [ ] Integração com Azure AI Language funciona
- [ ] Retorna `risco_violencia` e `risco_saude_mental`
- [ ] Pattern detection local implementado
- [ ] Validação de entrada (10-5000 caracteres)
- [ ] Testes unitários > 70%

### Task 004: Audio Analysis
- [ ] POST `/analyze/audio` aceita upload de arquivo
- [ ] Suporta WAV, MP3, OGG
- [ ] Integração com Azure AI Speech funciona
- [ ] Extração de features (pausas, entonação, voz tremida)
- [ ] Retorna `risco_violencia` e `risco_saude_mental`
- [ ] Arquivos são deletados após processamento
- [ ] Testes unitários > 70%

### Task 005: Image Analysis
- [ ] POST `/analyze/image` aceita upload de imagem
- [ ] Suporta JPEG, PNG
- [ ] Suporta vídeos MP4 (extração de frames)
- [ ] Integração com Azure AI Vision funciona
- [ ] Retorna `risco_violencia` e `risco_saude_mental`
- [ ] Arquivos são deletados após processamento
- [ ] Testes unitários > 70%

### Task 006: Multimodal Fusion
- [ ] POST `/analyze/multimodal` aceita texto + áudio + imagem
- [ ] Processamento paralelo implementado
- [ ] Late fusion combina scores corretamente
- [ ] Retorna resultado combinado com confiança
- [ ] Alerta gerado quando risco é alto
- [ ] Testes unitários > 70%

### Task 007: Rate Limiting
- [ ] QuotaManager implementado
- [ ] Middleware protege todos endpoints Azure
- [ ] Hard stop retorna HTTP 503 quando quota excedida
- [ ] Reset diário funciona (cron ou automático)
- [ ] Testes de integração passam

### Task 008: Tests
- [ ] Cobertura de testes > 70%
- [ ] Testes unitários para todos services
- [ ] Testes de integração para todos endpoints
- [ ] Testes de carga (Locust) configurados
- [ ] CI/CD executa testes automaticamente

### Task 009: Deploy Azure
- [ ] App Service F1 criado
- [ ] Variáveis de ambiente configuradas
- [ ] API acessível em URL pública
- [ ] `/health` responde corretamente
- [ ] Endpoints `/analyze/*` testados em produção
- [ ] Nenhum custo além do free tier

### Task 010: Documentation
- [ ] README.md completo e atualizado
- [ ] Vídeo demonstrativo no YouTube (5-10 min)
- [ ] Documentação da API (Swagger) em `/docs`
- [ ] Instruções de deploy claras

---

## 10. Referências

### Documentação do Projeto
- [Especificação do Produto](docs/product-spec.md)
- [Arquitetura](docs/architecture.md)
- [Contratos de API](docs/api-contracts.md)
- [User Stories](docs/user-stories.md)
- [Análise Cloud Free Tier](docs/technical/cloud-free-tier-analysis.md)
- [Estratégia Hard Stop](docs/technical/azure-free-tier-hard-stop.md)

### Documentação Azure
- [Azure AI Language](https://learn.microsoft.com/azure/ai-services/language-service/)
- [Azure AI Speech](https://learn.microsoft.com/azure/ai-services/speech-service/)
- [Azure AI Vision](https://learn.microsoft.com/azure/ai-services/computer-vision/)
- [Azure Free Tier](https://azure.microsoft.com/free)

---

## 11. Checklist Pré-Implementação

Antes de começar cada task, verificar:

- [ ] Task anterior mergeada na `main`
- [ ] Branch nova criada: `feature/task-XXX-nome`
- [ ] Azure credentials configuradas no `.env`
- [ ] Recursos Azure provisionados (Free Tier)
- [ ] MCP Context7 validado para patterns (se necessário)
- [ ] Testes da task anterior passando

---

**Próximo Passo**: Começar Task 001 (Bootstrap) criando a estrutura base do projeto.

---

*Este PRD é um documento vivo. Atualizações devem ser refletidas em commits com `docs: atualiza PRD`.*
