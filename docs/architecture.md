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

## Azure AI Vision vs YOLOv8: Por que Ambos?

O sistema utiliza duas tecnologias complementares para análise visual, cada uma com propósito específico:

### Azure AI Vision

**Propósito**: Análise contextual de imagem para compreensão geral da cena.

**Capacidades**:
- Geração de descrições detalhadas do conteúdo visual
- Extração de tags e categorias semânticas
- Detecção de objetos genéricos (mobília, pessoas, ambientes)
- Análise de contexto e relacionamentos entre elementos

**Casos de uso no projeto**:
- Descrever o ambiente de uma consulta médica
- Identificar objetos gerais presentes na cena
- Prover contexto sobre a situação capturada

**Considerações**:
- Consome quota do Azure Free Tier (5.000 requests/mês)
- API externa com latência de rede (~100-500ms)
- Cobertura multilíngue nas descrições

### YOLOv8 (Ultralytics)

**Propósito**: Detecção específica para domínio médico/saúde da mulher.

**Capacidades**:
- Detecção de instrumentos médicos (tesouras, bisturis, agulhas)
- Identificação de sangramento via análise de cor HSV
- Análise de postura e linguagem corporal
- Detecção em tempo real em CPU

**Casos de uso no projeto**:
- Detectar instrumentos cirúrgicos em procedimentos
- Identificar sangramento anômalo (hemorragia)
- Analisar postura da paciente (sinais de desconforto, medo)
- Calcular riscos específicos de violência e saúde mental

**Considerações**:
- Processamento 100% local (zero custo Azure)
- Modelo YOLOv8n (~6MB) otimizado para edge/CPU
- Latência baixa (<100ms por frame)
- Especializado para casos de uso de saúde da mulher

### Por que Usar Ambos?

| Aspecto | Azure AI Vision | YOLOv8 |
|---------|----------------|--------|
| **Propósito** | Contexto geral da imagem | Detalhes médicos específicos |
| **Objetos detectados** | Genéricos (cadeiras, mesas, pessoas) | Médicos (tesouras, sangue, posturas) |
| **Custo** | Consome quota Azure | Gratuito (local) |
| **Latência** | ~100-500ms | ~10-50ms |
| **Idioma** | Multilíngue | Agnóstico (visão pura) |
| **Precisão médica** | Limitada | Alta (modelo customizado) |

**Arquitetura complementar**:
```
Vídeo/Imagem de Entrada
         │
         ├──→ YOLOv8 (local) ──→ Detecção instrumentos, sangue, postura
         │                              │
         │                              ▼
         │                    Cálculo de risco específico
         │                              │
         ▼                              ▼
Azure AI Vision (opcional) ──→ Contexto geral da cena
         │                              │
         └────────────┬─────────────────┘
                      ▼
              Fusão de análises
                      │
         ┌────────────┼────────────┐
         ▼            ▼            ▼
   risco_violencia  risco_saude_mental  metadata
```

**Exemplo prático de trabalho conjunto**:

Considerando um vídeo de uma consulta de emergência:

1. **YOLOv8 detecta**:
   - Uma tesoura cirúrgica (classe: `scissors`, confiança: 92%)
   - Área de sangue no campo visual (severidade: alta)
   - Postura retraída da paciente (indicador de medo)

2. **Resultado combinado**:
   - `risco_violencia: alto` (instrumento + postura de medo)
   - `risco_saude_mental: médio` (sangramento pode indicar autoagressão ou acidente)
   - Alerta específico: "Instrumento cirúrgico + sangue detectado"

3. **Sem Azure AI Vision** (modo padrão para economia):
   - Apenas YOLOv8 executa
   - Detecções médicas são priorizadas
   - Zero consumo de quota Azure para vídeo

**Decisão de design**:
- **YOLOv8 é obrigatório**: Fornece detecções médicas específicas necessárias para o domínio
- **Azure AI Vision é opcional**: Pode ser usado em casos onde contexto geral da cena é necessário, mas priorizamos YOLOv8 para manter o uso dentro do Azure Free Tier

## Technology Decisions

Esta seção documenta as motivações para escolha de cada tecnologia principal do projeto.

### FastAPI

**Por que FastAPI?**
- **Async nativo**: Processamento paralelo de múltiplas modalidades (texto + áudio + vídeo simultaneamente)
- **Documentação automática**: Gera Swagger UI e ReDoc sem código extra
- **Validação automática**: Integração nativa com Pydantic para validação de requests/responses
- **Performance**: Um dos frameworks Python mais rápidos (baseado em Starlette)
- **Type hints**: Suporte completo a type hints modernos do Python 3.11+

**Alternativas consideradas**: Flask (síncrono, mais lento), Django (pesado, não focado em APIs)

### Pydantic v2

**Por que Pydantic?**
- **Validação de dados**: Garante que dados de entrada estão corretos antes de processar
- **Serialização**: Conversão automática entre JSON e objetos Python
- **Documentação**: Gera schemas OpenAPI automaticamente para o Swagger
- **Configurações**: `pydantic-settings` para validação de variáveis de ambiente
- **Performance**: Pydantic v2 é 5-50x mais rápido que v1 (core em Rust)

**Uso no projeto**: Schemas de API (`TextAnalysisRequest`, `AudioAnalysisResponse`), configuração (`Settings`), validação cross-field

### Poetry

**Por que Poetry em vez de requirements.txt?**
- **Lock file** (`poetry.lock`): Garante versões idênticas em todos os ambientes (dev, CI/CD, produção)
- **Resolução de conflitos**: Resolve automaticamente dependências conflitantes (SAT solver)
- **Grupos de dependências**: Separa dependências de produção, desenvolvimento e opcionais
- **Virtualenv automático**: Cria e gerencia ambiente isolado automaticamente
- **Build para produção**: Exporta requirements.txt quando necessário

**Alternativas**: pip + requirements.txt (sem lock file, versões flutuantes), conda (mais pesado, para data science)

### Azure AI Services

**Por que Azure?**
- **Free Tier**: 5.000 requests/mês (Text Analytics), 300 minutos/mês (Speech)
- **SDK Python oficial**: APIs bem documentadas e mantidas pela Microsoft
- **Multilíngue**: Suporte nativo a 100+ idiomas (importante para Content Safety)
- **LGPD compliance**: Azure é certificado para dados de saúde no Brasil

**Serviços utilizados**:
- **Text Analytics**: Análise de sentimento em prontuários e diários
- **Speech**: Transcrição de consultas de telemedicina
- **Content Safety**: Detecção multilíngue de riscos (violência, autoagressão)

**Alternativas**: Google Cloud (custo similar), AWS Comprehend (menos foco em saúde)

### YOLOv8 (Ultralytics)

**Por que YOLOv8?**
- **Processamento local**: Zero custo de cloud, zero latência de rede
- **Modelo pequeno**: YOLOv8n (~6MB) roda em CPU sem GPU
- **Detecção em tempo real**: 10-50ms por frame, suficiente para análise de vídeo
- **Customizável**: Possibilidade de treinar com dados específicos de saúde
- **Requisito obrigatório**: Especificação do PDF menciona "YOLOv8 customizado"

**Uso no projeto**: Detecção de instrumentos cirúrgicos, sangramento (análise HSV), postura da paciente

**Alternativas**: Azure AI Vision (custo, latência), TensorFlow Object Detection (mais complexo)

### Librosa + SoundFile

**Por que Librosa?**
- **Padrão em análise de áudio**: Biblioteca mais usada para processamento de sinais de áudio em Python
- **Prosódia**: Extrai pitch, energia, pausas (features relevantes para detectar voz tremida)
- **Integração com scikit-learn**: Pipelines de ML para análise de emoção na voz

**Uso no projeto**: Análise prosódica após transcrição Azure (pitch analysis, detecção de pausas suspeitas)

### OpenCV

**Por que OpenCV?**
- **Extração de frames**: De vídeos MP4/AVI/MOV para análise YOLOv8
- **Processamento de imagem**: Operações básicas (resize, convert, HSV color space)
- **Padrão da indústria**: Estável, bem documentado, bindings Python oficiais

**Uso no projeto**: Extração de frames, conversão de color space para detecção de sangue

### Ruff + mypy

**Por que ambos?**

**Ruff**:
- **Linter + Formatter**: Substitui flake8, black, isort em uma ferramenta só
- **Performance**: 10-100x mais rápido que alternativas (Rust core)
- **Formato consistente**: Line length 88 (padrão Black), imports organizados

**mypy**:
- **Type checking**: Verifica se tipos estão corretos antes de runtime
- **Strict mode**: Modo rigoroso para código crítico de saúde
- **Catching bugs**: Detecta `None` onde deveria ter `dict`, `str` onde deveria ter `int`

**Por que os dois**: Ruff cuida de estilo/código; mypy cuida de lógica/tipos

### SQLAlchemy + aiosqlite

**Por que SQLAlchemy?**
- **Async**: `aiosqlite` permite queries SQLite sem bloquear a API
- **ORM**: Abstração para modelo de dados (AuditLog)
- **Migrations**: Estrutura para evolução do schema

**Por que SQLite**: Suficiente para MVP (metadados, audit logs), sem servidor extra, LGPD-friendly (dados locais)

**Alternativas**: PostgreSQL (overkill para escala), Azure SQL (custo, latência)

### structlog

**Por que structlog?**
- **JSON logging**: Logs estruturados para análise e parsing automatizado
- **Context binding**: Correlation ID tracking através de toda a requisição
- **Sanitização**: Integração com `SecretMasker` para não logar PII

**Uso no projeto**: Logs de auditoria LGPD-compliant, tracking de requisições

## Technology Stack

| Category | Technology | Version |
|----------|-----------|---------|
| Runtime | Python | 3.11+ |
| Framework | FastAPI | 0.115+ |
| Validation | Pydantic | v2 |
| Azure SDK | azure-ai-textanalytics | 5.4.0 |
| Azure SDK | azure-cognitiveservices-speech | 1.48.x |
| Azure SDK | azure-ai-vision-imageanalysis | 1.0+ |
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
