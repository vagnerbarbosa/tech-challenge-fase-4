# Análise de Decomposição em Microserviços com DDD

> **Data**: 2026-05-03  
> **Versão**: 0.9.0  
> **Escopo**: Análise estratégica - não implementar

---

## 1. Contexto Atual (Monolito)

### Estrutura Monolítica

```
┌─────────────────────────────────────────────────────────────┐
│                    API Monolítica (FastAPI)                 │
├─────────────────────────────────────────────────────────────┤
│  Rotas                                                      │
│  ├── /analyze/text      → TextAnalysisService               │
│  ├── /analyze/audio     → AudioAnalysisService              │
│  ├── /analyze/video     → VideoAnalysisService              │
│  ├── /analyze/multimodal → MultimodalFusionService          │
│  ├── /admin/*           → AdminService                      │
│  └── /auth/*            → AuthService                        │
├─────────────────────────────────────────────────────────────┤
│  Infraestrutura Compartilhada                               │
│  ├── Azure Clients (Text, Speech, Vision)                   │
│  ├── YOLOv8 (vídeo local)                                   │
│  ├── Cache (in-memory)                                      │
│  └── Banco de dados (SQLite)                                │
├─────────────────────────────────────────────────────────────┤
│  Cross-Cutting Concerns                                     │
│  ├── Rate Limiting                                          │
│  ├── Audit Logging                                          │
│  ├── Security (API Keys, CORS)                              │
│  └── LGPD Compliance                                        │
└─────────────────────────────────────────────────────────────┘
```

### Problemas Identificados

| Problema | Impacto |
|----------|---------|
| Acoplamento de serviços Azure | Falha em um serviço derruba todos |
| YOLOv8 pesado (~13GB) | Dificulta deploy e escala independente |
| Cache compartilhado | Não permite escala horizontal |
| SQLite local | Gargalo para múltiplas instâncias |

---

## 2. Análise DDD - Bounded Contexts

### 2.1 Identificação de Contextos Delimitados

Baseado na análise do domínio, identificamos **5 Bounded Contexts**:

```
┌─────────────────────────────────────────────────────────────────┐
│                        Sistema Multimodal                        │
├─────────────────────────────────────────────────────────────────┤
│                                                                  │
│  ┌─────────────────┐  ┌─────────────────┐  ┌─────────────────┐ │
│  │  Contexto de    │  │  Contexto de    │  │  Contexto de    │ │
│  │  Análise Texto  │  │  Análise Áudio  │  │  Análise Vídeo  │ │
│  │  (Text Analysis)│  │  (Audio Analysis)│  │  (Video Analysis)│ │
│  │                 │  │                 │  │                 │ │
│  │  - Azure Text   │  │  - Azure Speech │  │  - YOLOv8       │ │
│  │  - Content Safety │  │  - Librosa      │  │  - OpenCV       │ │
│  │  - Keywords     │  │  - Prosódica    │  │  - Postura      │ │
│  └────────┬────────┘  └────────┬────────┘  └────────┬────────┘ │
│           │                    │                    │          │
│           └────────────────────┼────────────────────┘          │
│                                │                               │
│  ┌─────────────────────────────▼─────────────────────────────┐│
│  │              Contexto de Fusão Multimodal                 ││
│  │              (Multimodal Fusion)                          ││
│  │                                                           ││
│  │  - Late Fusion ponderado                                  ││
│  │  - Agregação de resultados                               ││
│  │  - Coordenação entre contextos                            ││
│  └────────────────────────────────────────────────────────────┘│
│                                                                │
│  ┌─────────────────────────────────────────────────────────────┐
│  │              Contexto de Governança e Segurança             │
│  │              (Governance & Security)                        │
│  │                                                             │
│  │  - Autenticação/Autorização                               │
│  │  - Rate Limiting                                            │
│  │  - Audit Logging                                            │
│  │  - LGPD Compliance                                          │
│  └─────────────────────────────────────────────────────────────┘
│                                                                │
└─────────────────────────────────────────────────────────────────┘
```

---

## 3. Proposta de Decomposição em Microserviços

### 3.1 Arquitetura Alvo

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                           API Gateway + Auth                                 │
│  (Kong / Nginx / AWS API Gateway)                                           │
│                                                                              │
│  Responsabilidades:                                                          │
│  - Roteamento para serviços                                                  │
│  - Autenticação (API Keys) - INTEGRADO                                       │
│  - Rate Limiting global                                                      │
│  - SSL/TLS termination                                                       │
│                                                                              │
│  Por que auth integrado?                                                     │
│  - Latência: sem network hop extra                                           │
│  - Simplicidade: um serviço a menos                                          │
│  - Suficiente para API Keys simples                                          │
└─────────────────────────────────────────────────────────────────────────────┘
                                       │
           ┌───────────────────────────┼───────────────────────────┐
           │                           │                           │
           ▼                           ▼                           ▼
┌─────────────────────┐  ┌─────────────────────┐  ┌─────────────────────┐
│   Text Service      │  │   Audio Service     │  │   Video Service     │
│   (text-service)    │  │   (audio-service)   │  │   (video-service)   │
│                     │  │                     │  │                     │
│  Python + FastAPI   │  │  Python + FastAPI   │  │  Python + FastAPI   │
│  Azure Text         │  │  Azure Speech       │  │  YOLOv8 + OpenCV    │
│  Redis Cache        │  │  Librosa            │  │  Redis Cache        │
│                     │  │  Redis Cache        │  │                     │
│  Replicas: 3-5      │  │  Replicas: 2-3      │  │  Replicas: 2-3      │
│  Memory: 512MB-1GB  │  │  Memory: 1-2GB      │  │  Memory: 4-8GB      │
└──────────┬──────────┘  └──────────┬──────────┘  └──────────┬──────────┘
           │                        │                        │
           └────────────────────────┼────────────────────────┘
                                    │
                                    ▼
                  ┌─────────────────────────────────────┐
                  │      Fusion Service                 │
                  │      (fusion-service)               │
                  │                                     │
                  │  - Orquestra análises              │
                  │  - Agrega resultados               │
                  │  - Saga Pattern (consistência)     │
                  │                                     │
                  └──────────────┬──────────────────────┘
                                 │
                                 ▼
                  ┌─────────────────────────────────────┐
                  │      Audit Service                  │
                  │      (audit-svc)                    │
                  │                                     │
                  │  - Event sourcing                   │
                  │  - LGPD compliance                  │
                  │  - Retenção 5 anos                  │
                  │                                     │
                  └─────────────────────────────────────┘

┌─────────────────────────────────────────────────────────────────────────────┐
│                            Message Broker                                     │
│  (RabbitMQ / Apache Kafka / AWS EventBridge)                                │
│  - Eventos assíncronos                                                      │
│  - Saga coordination                                                        │
│  - Audit events                                                             │
└─────────────────────────────────────────────────────────────────────────────┘

┌─────────────────────────────────────────────────────────────────────────────┐
│                            Shared Data Stores                                 │
│                                                                              │
│  ┌──────────────┐  ┌──────────────┐  ┌──────────────┐  ┌──────────────┐  │
│  │   Redis      │  │  PostgreSQL  │  │  MinIO/S3    │  │ Elasticsearch│  │
│  │   (Cache)    │  │  (Results)    │  │  (Files)     │  │  (Audit)     │  │
│  └──────────────┘  └──────────────┘  └──────────────┘  └──────────────┘  │
└─────────────────────────────────────────────────────────────────────────────┘
```

---

### 3.2 Detalhamento dos Microserviços

#### Serviço 1: Text Analysis Service (`text-service`)

**Responsabilidade**: Análise de texto e sentimento

**Entidades (DDD)**:
```python
# Domain Entities
class TextAnalysis:
    text: str
    sentiment: Sentiment
    risk_score: RiskScore
    language: Language
    
class Sentiment:
    label: str  # positivo/negativo/neutro/misto
    score: float  # -1.0 a 1.0
    confidence: float
    
class RiskScore:
    violence: Level  # baixo/medio/alto
    mental_health: Level
    indicators: List[str]
```

**API REST**:
```yaml
POST /v1/analyze
  Request: { text, type, patient_id }
  Response: TextAnalysisResponse

GET /v1/health
GET /v1/formats
```

**Tecnologia**:
- Python + FastAPI
- Azure Text Analytics (SDK)
- Redis (cache de resultados)
- PostgreSQL (resultados históricos)

**Escalabilidade**:
- Stateless (horizontal)
- 3-5 réplicas
- HPA: CPU > 70% ou memória > 80%

---

#### Serviço 2: Audio Analysis Service (`audio-service`)

**Responsabilidade**: Transcrição e análise prosódica

**Entidades (DDD)**:
```python
class AudioAnalysis:
    transcription: str
    language: str
    prosodic_features: ProsodicFeatures
    risk_score: RiskScore
    
class ProsodicFeatures:
    voice_tremor: bool
    pauses: int
    intonation: str
    pitch_variation: float
    duration_seconds: float
```

**API REST**:
```yaml
POST /v1/analyze (multipart/form-data)
  Request: { audio: File, patient_id }
  Response: AudioAnalysisResponse

GET /v1/health
GET /v1/formats
```

**Tecnologia**:
- Python + FastAPI
- Azure Speech Services
- Librosa (processamento local)
- MinIO/S3 (armazenamento temporário)

**Escalabilidade**:
- 2-3 réplicas
- CPU-intensive (transcrição)
- PodTopologySpread (evitar mesmo nó)

---

#### Serviço 3: Video Analysis Service (`video-service`)

**Responsabilidade**: Análise de vídeo com YOLOv8

**Entidades (DDD)**:
```python
class VideoAnalysis:
    detections: List[Detection]
    alerts: List[Alert]
    risk_score: RiskScore
    frames_analyzed: int
    
class Detection:
    class_name: str  # person, knife, scissors
    confidence: float
    bbox: BoundingBox
    timestamp: float
    
class Alert:
    type: str  # rigidez_detectada, objeto_perigoso
    severity: str
    description: str
```

**API REST**:
```yaml
POST /v1/analyze (multipart/form-data)
  Request: { video: File, patient_id }
  Response: VideoAnalysisResponse

GET /v1/health
GET /v1/formats
GET /v1/cache/stats
POST /v1/cache/clear
```

**Tecnologia**:
- Python + FastAPI
- YOLOv8 (modelo local)
- OpenCV
- GPU support (opcional)

**Escalabilidade**:
- 1-2 réplicas (pesado)
- Node affinity para GPU
- PodDisruptionBudget (evitar interrupções)

---

#### Serviço 4: Multimodal Fusion Service (`fusion-service`)

**Responsabilidade**: Orquestração e agregação

**Padrão**: Saga Pattern para consistência eventual

**Entidades (DDD)**:
```python
class MultimodalAnalysis:
    analysis_id: UUID
    text_result: Optional[TextAnalysis]
    audio_result: Optional[AudioAnalysis]
    video_result: Optional[VideoAnalysis]
    fusion_result: FusionResult
    status: AnalysisStatus  # pending/completed/failed
    
class FusionResult:
    violence_risk: Level
    mental_health_risk: Level
    confidence: float
    alert: bool
    recommendation: str
```

**API REST**:
```yaml
POST /v1/analyze
  Request: { text?, audio?, video?, patient_id }
  Response: MultimodalResponse
  
  # Async processing
  → Returns: 202 Accepted + Location header
  → Callback/Webhook when done

GET /v1/analyses/{id}  # Poll status
DELETE /v1/analyses/{id}  # Cancel
```

**Padrão Saga (Compensação)**:
```python
async def analyze_multimodal(request):
    saga = SagaBuilder()
        .step("analyze_text", text_service)
        .step("analyze_audio", audio_service)
        .step("analyze_video", video_service)
        .step("fuse_results", fusion_service)
        .on_failure(CompensateAll())  # Limpa recursos
        .execute()
```

**Tecnologia**:
- Python + FastAPI
- Celery (task queue) ou Temporal (workflows)
- RabbitMQ/Kafka (event bus)
- PostgreSQL (estado das análises)

**Escalabilidade**:
- 2-3 réplicas
- Stateless
- Auto-scale baseado em fila

---

#### Componente 5: API Gateway com Auth Integrado (`api-gateway`)

**Responsabilidade**: Roteamento, autenticação, rate limiting e segurança

Por que auth no Gateway e não serviço separado?
- **Latência**: Sem network hop extra (+1-5ms evitados)
- **Simplicidade**: Um serviço a menos para operar
- **Suficiente**: Para API Keys simples, não precisa de Identity Service

**Entidades (DDD)**:
```python
class ApiKey:
    key_id: str
    key_hash: str
    roles: List[str]
    permissions: List[str]
    created_at: datetime
    expires_at: Optional[datetime]
    rate_limit: RateLimitConfig
    
class Session:
    session_id: str
    api_key_id: str
    created_at: datetime
    last_activity: datetime
```

**Funcionalidades**:
```yaml
# Auth & Routing
POST /v1/auth/keys          # Criar API Key (admin)
DELETE /v1/auth/keys/{id}   # Revogar (admin)
GET /v1/auth/me             # Info da API Key

# Proxy para serviços (com auth)
/analyze/text/*     → text-service
/analyze/audio/*    → audio-service
/analyze/video/*    → video-service
/analyze/multimodal/* → fusion-service
```

**Tecnologia**:
- Kong / Nginx / Traefik ( Gateway )
- Lua plugins (Kong) ou Nginx modules para auth
- Redis (cache de API Keys para performance)
- PostgreSQL (persistência de API Keys)

**Escalabilidade**:
- Stateless (horizontal)
- 2-3 réplicas
- Sticky sessions (opcional, para rate limiting local)

**Nota**: Identity Service separado só valeria a pena se:
- Múltiplos gateways fossem necessários (mobile, web, partner)
- Auth evoluísse para OAuth2/OIDC complexo
- Time crescesse muito (>10 devs)

---

#### Serviço 5: Audit Service (`audit-service`)

**Responsabilidade**: Auditoria LGPD

**Padrão**: Event Sourcing + CQRS

**Entidades (DDD)**:
```python
class AuditEvent:
    event_id: UUID
    event_type: str  # ANALYSIS_CREATED, DATA_ACCESSED, etc
    timestamp: datetime
    correlation_id: str
    api_key_id: str  # hash
    patient_id_hash: str  # LGPD
    action: str
    resource: str
    result: str
    ip_address: str  # anonimizado
    user_agent_hash: str
    
class DataRetentionPolicy:
    event_type: str
    retention_days: int  # 5 anos LGPD
    encryption: bool
```

**Event Sourcing**:
```python
# Command Side
class CreateAuditEventCommand:
    event_type: str
    payload: dict
    
# Event Store (append-only)
events = [
    AuditEventCreated,
    AuditEventEncrypted,
    AuditEventIndexed,
]

# Query Side (CQRS) - Read Model
class AuditQueryService:
    def get_events_by_patient(patient_id_hash):
        # Elasticsearch
        pass
    
    def export_for_deletion(patient_id_hash):
        # LGPD - Right to be forgotten
        pass
```

**API REST**:
```yaml
POST /v1/events          # Internal (event sourcing)
GET /v1/stats             # Admin stats
GET /v1/export           # LGPD export
POST /v1/anonymize       # LGPD right to be forgotten
```

**Tecnologia**:
- Python + FastAPI
- Event Store (PostgreSQL com JSONB)
- Elasticsearch (query/read model)
- MinIO (logs comprimidos)

---

## 4. Comunicação entre Serviços

### 4.1 Padrões de Comunicação

```
┌─────────────────────────────────────────────────────────────────┐
│                    Sync (REST/gRPC)                              │
├─────────────────────────────────────────────────────────────────┤
│                                                                  │
│  API Gateway → Identity Service (Auth)                        │
│       │                                                          │
│       ▼                                                          │
│  Fusion Service → Text Service (Saga: sync)                   │
│               → Audio Service (Saga: async)                   │
│               → Video Service (Saga: async)                   │
│                                                                  │
│  Quando usar Sync:                                              │
│  - Latência < 500ms                                             │
│  - Operações simples (CRUD)                                     │
│  - Consistência forte necessária                                │
│                                                                  │
└─────────────────────────────────────────────────────────────────┘

┌─────────────────────────────────────────────────────────────────┐
│                   Async (Event-Driven)                           │
├─────────────────────────────────────────────────────────────────┤
│                                                                  │
│  ┌──────────────┐    ┌──────────────┐    ┌──────────────┐      │
│  │   Service    │───▶│   Event Bus  │◀───│   Service    │      │
│  │   (emissor)  │    │  (RabbitMQ)  │    │   (consumidor)│      │
│  └──────────────┘    └──────────────┘    └──────────────┘      │
│                                                                  │
│  Eventos:                                                       │
│  - analysis.completed → Audit Service                         │
│  - quota.exceeded → Rate Limiter                              │
│  - analysis.failed → Alert Manager                              │
│                                                                  │
│  Quando usar Async:                                             │
│  - Processamento > 1s (vídeo, áudio)                          │
│  - Consistência eventual aceitável                            │
│  - Desacoplamento necessário                                  │
│  - Resiliência (retry, DLQ)                                   │
│                                                                  │
└─────────────────────────────────────────────────────────────────┘
```

### 4.2 Saga Pattern para Análise Multimodal

```python
# Saga Definition (Fusion Service)
class MultimodalAnalysisSaga:
    """
    Saga para orquestrar análise multimodal.
    
    Steps:
    1. Analyze Text (sync, compensable)
    2. Analyze Audio (async, compensable)  
    3. Analyze Video (async, compensable)
    4. Fuse Results (sync, final)
    
    Compensation:
    - Delete temporary files
    - Release quotas
    - Log failure audit
    """
    
    async def execute(self, request):
        saga = SagaBuilder()
        
        # Step 1: Text Analysis
        if request.text:
            saga.add_step(
                name="analyze_text",
                action=lambda: self.text_client.analyze(request.text),
                compensate=lambda: self.text_client.release_quota(),
            )
        
        # Step 2: Audio Analysis
        if request.audio:
            saga.add_step(
                name="analyze_audio",
                action=lambda: self.audio_client.analyze(request.audio),
                compensate=lambda: self.audio_client.cleanup(),
            )
        
        # Step 3: Video Analysis
        if request.video:
            saga.add_step(
                name="analyze_video", 
                action=lambda: self.video_client.analyze(request.video),
                compensate=lambda: self.video_client.cleanup(),
            )
        
        # Step 4: Fusion
        saga.add_step(
            name="fuse_results",
            action=lambda: self.fusion_service.fuse(saga.results),
        )
        
        return await saga.execute()
```

---

## 5. Estratégia de Migração (Strangler Fig Pattern)

### Fase 1: Extração Identity Service (Semana 1-2)
```
┌─────────────────────────────────────────────────────────────────┐
│                        API Gateway                              │
└──────────────────┬──────────────────────────────────────────────┘
                   │
       ┌───────────┴───────────┐
       │                       │
       ▼                       ▼
┌──────────────┐      ┌─────────────────────────┐
│ NEW Identity │◀─────│   Monolito (Adaptado)   │
│   Service    │      │   - Auth via API         │
└──────────────┘      │   - Sem lógica de auth   │
                      └─────────────────────────┘
```

### Fase 2: Extração Audit Service (Semana 3-4)
```
┌─────────────────────────────────────────────────────────────────┐
│                        API Gateway                              │
└──────────────────┬──────────────────────────────────────────────┘
                   │
       ┌───────────┴───────────┐
       │                       │
       ▼                       ▼
┌──────────────┐      ┌─────────────────────────┐
│ NEW Audit    │◀─────│   Monolito            │
│   Service    │      │   - Envia eventos      │
└──────────────┘      │   - Não grava logs     │
                      └─────────────────────────┘
```

### Fase 3: Extração Text Service (Semana 5-6)
```
┌─────────────────────────────────────────────────────────────────┐
│                        API Gateway                              │
└──────────────────┬──────────────────────────────────────────────┘
                   │
       ┌───────────┼───────────┐
       │           │           │
       ▼           ▼           ▼
┌────────┐  ┌──────────┐  ┌──────────┐
│  Text  │  │  Audio   │  │  Video   │
│Service │  │ (Mono)   │  │ (Mono)   │
└────────┘  └──────────┘  └──────────┘
```

### Fase 4: Extração Audio e Video (Semana 7-10)
```
┌──────────┐  ┌──────────┐  ┌──────────┐
│  Text    │  │  Audio   │  │  Video   │
│ Service  │  │ Service  │  │ Service  │
└──────────┘  └──────────┘  └──────────┘
```

### Fase 5: Extração Fusion Service (Semana 11-12)
```
┌─────────────────────────────────────────────────────────┐
│                    Fusion Service                        │
│              (Orquestração Saga)                         │
└─────────────────────────────────────────────────────────┘
       │              │              │
       ▼              ▼              ▼
┌──────────┐  ┌──────────┐  ┌──────────┐
│  Text    │  │  Audio   │  │  Video   │
│ Service  │  │ Service  │  │ Service  │
└──────────┘  └──────────┘  └──────────┘
```

---

## 6. Benefícios Esperados

| Benefício | Descrição | Impacto |
|-----------|-----------|---------|
| **Escalabilidade Independente** | Video Service escala separado (GPU) | Custo -30% |
| **Resiliência** | Falha no Azure Text não afeta Vídeo | Uptime 99.9% |
| **Deploy Independente** | Atualizar YOLO sem parar Text | Velocity +40% |
| **Time Autonomy** | Times independentes por domínio | Produtividade +25% |
| **Tecnologia Especializada** | Video Service usa GPU, Text usa CPU | Eficiência +50% |

---

## 7. Trade-offs e Considerações

### Complexidade Adicionada

| Aspecto | Monolito | Microserviços | Mitigação |
|---------|----------|---------------|-----------|
| Operações | Simples | Complexa (K8s, Istio) | GitOps + ArgoCD |
| Debugging | Stack trace único | Distributed tracing | OpenTelemetry |
| Testing | Unit/Integration | + Contract Tests | Pact |
| Transações | ACID | Saga/Eventual | Idempotência |

### Análise de Custos: MVP vs Produção Real em Saúde

#### Cenário MVP (Tech Challenge)

| Item | Monolito (mensal) | Microserviços (mensal) |
|------|-------------------|------------------------|
| Infraestrutura | R$ 500 | R$ 800 (+60%) |
| Operação | R$ 200 | R$ 400 (+100%) |
| **Total** | **R$ 700** | **R$ 1.200** (+71%) |

#### Cenário Produção: Hospital de Médio Porte

Baseado em dados reais do [Hospital da UEM](https://www.parana.pr.gov.br/aen/Noticia/100-SUS-Hospital-da-UEM-alcanca-60-mil-atendimentos-de-urgencia-em-2025) (60K atendimentos/ano = ~5K/mês):

**Volume de Análises de Vídeo Estimado:**
- 50 leitos UTI × 24h × 30 dias × 6 análises/hora (10min intervalo) = **216.000 análises/mês**

##### Opção 1: Azure Computer Vision (HIPAA-Compliant)

| Componente | Custo Mensal (USD) | Custo Mensal (R$) |
|------------|-------------------|-------------------|
| 216K inferências × $0.002 | $432 | R$ 2.160 |
| Azure Health Data Services | $200 | R$ 1.000 |
| Storage LGPD (7 anos) | $150 | R$ 750 |
| Security Center, Monitor | $100 | R$ 500 |
| **Data transfer** (10TB/mês - esquecido!) | $200 | R$ 1.000 |
| **Subtotal Azure** | **$1.082** | **R$ 5.410** |

##### Opção 2: YOLOv8 Local (Self-Hosted)

| Componente | Custo (USD) | Custo (R$) |
|------------|-------------|------------|
| **Hardware inicial** (2x RTX 4090) | $8.000 | R$ 40.000 |
| Energia/mês (400W × 24h) | $40 | R$ 200 |
| Cooling/datacenter | $200 | R$ 1.000 |
| DevOps/SRE (20h/mês) | $1.600 | R$ 8.000 |
| **Subtotal Local (amortizado 3 anos)** | **$1.840/mês** | **R$ 9.200/mês** |

##### Break-Even Analysis

| Volume Mensal | Azure | Local | Vencedor |
|---------------|-------|-------|----------|
| 50K análises | R$ 1.600 | R$ 9.200 | **Azure** (82% mais barato) |
| 200K análises | R$ 5.400 | R$ 9.200 | **Azure** (41% mais barato) |
| **500K análises** | **R$ 11.500** | **R$ 9.500** | **Local** (17% mais barato) |
| 1M análises | R$ 22.000 | R$ 10.000 | **Local** (55% mais barato) |

##### TCO 3 Anos (Cenário Hospital 216K análises/mês)

| Aspecto | Azure | Local |
|---------|-------|-------|
| Infraestrutura (3 anos) | R$ 194.760 | R$ 40.000 (hw) |
| Rede/Transferência | R$ 36.000 | R$ 0 |
| Compliance/LGPD | R$ 25.000 | R$ 15.000 |
| Mão de obra DevOps | R$ 180.000 | R$ 288.000 |
| **TCO Total 3 anos** | **R$ 435.760** | **R$ 343.000** |

**Local é 21% mais barato em 3 anos**, mas com:
- Riscos operacionais maiores (sem SLA de cloud)
- Necessidade de equipe especializada
- Menor elasticidade (não escala "para cima" rapidamente)

##### Recomendação para Produção Real: Arquitetura Híbrida

```
┌─────────────────────────────────────────────────────────┐
│              Hospital (Edge/On-Prem)                   │
│  ┌─────────────────────────────────────────────────┐   │
│  │  YOLOv8 Lite (RTX 4060 Ti - R$ 2.000)          │   │
│  │  - Detecção em tempo real (<50ms)              │   │
│  │  - Processamento de frames (deduplicação)      │   │
│  │  - Alertas críticos offline                    │   │
│  └─────────────────────────────────────────────────┘   │
│                         │                               │
│                         ▼                               │
│  ┌─────────────────────────────────────────────────┐   │
│  │  Gateway Local (filtragem + anonimização)      │   │
│  │  - Envia apenas eventos/metadados              │   │
│  │  - Dados brutos NÃO saem do hospital             │   │
│  └─────────────────────────────────────────────────┘   │
│                         │                               │
└─────────────────────────┼───────────────────────────────┘
                          │ Internet (apenas eventos)
                          ▼
              ┌──────────────────────────┐
              │      Azure Cloud         │
              │  - Dashboard/Analytics   │
              │  - Armazenamento LGPD    │
              │  - Audit trails          │
              └──────────────────────────┘
```

**Custos Híbrido (mensal):**
| Componente | Custo (R$) |
|------------|-----------|
| Edge GPU (RTX 4060 Ti amortizado) | R$ 80 |
| Energia/Cooling | R$ 250 |
| Azure (eventos + storage) | R$ 800 |
| **Total Híbrido** | **R$ 1.130** |

vs **R$ 5.410** do Azure puro = **Economia de 79%**

##### Componentes de Infraestrutura Adicionais (Produção Real)

Além dos custos de processamento acima, um ambiente de produção hospitalar requer:

**Redis (Rate Limiting Distribuído):**
| Aspecto | MVP (Local) | Produção (Redis) |
|---------|-------------|------------------|
| Implementação | In-memory | Azure Cache for Redis |
| Custo mensal | R$ 0 | R$ 50-200 |
| Motivação | Single instance | Multi-instance, persistência de quotas |

**Azure SQL Database (Persistência Histórica):**
| Aspecto | MVP (SQLite) | Produção (Azure SQL) |
|---------|--------------|---------------------|
| Implementação | File-based | Managed cloud database |
| Custo mensal | R$ 0 | R$ 30-150 |
| Motivação | Local storage | Backup automático, alta disponibilidade, LGPD compliance |
| Casos de uso | - | Histórico de análises, dashboard de tendências, auditoria completa |

**Load Testing (Validação de Performance):**
| Aspecto | MVP | Produção |
|---------|-----|----------|
| Ferramenta | pytest (funcional) | Locust/k6 + Azure Load Testing |
| Custo mensal | R$ 0 | R$ 0-500 (variável) |
| Motivação | Testes de funcionalidade | Validar carga: 100+ UTIs simultâneas, latência p95/p99 |
| Execução | - | Periódica (pré-deploy de releases) |

**Custo Total de Produção Real (mensal):**
| Componente | Custo (R$) |
|------------|-----------|
| Processamento (híbrido) | R$ 1.130 |
| Redis (Azure Cache) | R$ 100 |
| Azure SQL Database | R$ 80 |
| Load Testing (estimado) | R$ 100 |
| **Total Produção Real** | **R$ 1.410** |

> **Nota**: Mesmo com esses componentes adicionais, o custo de produção (R$ 1.410/mês) ainda é **74% mais barato** que o Azure puro (R$ 5.410/mês), mantendo o compliance LGPD com dados brutos no hospital.

#### Conclusão

| Cenário | Recomendação | Justificativa |
|---------|--------------|---------------|
| **MVP/Tech Challenge** | Azure puro | Não há volume para justificar GPU |
| **Produção Pequena** (<100K/mês) | Azure puro | Cloud é mais barato e simples |
| **Produção Média** (100-500K/mês) | **Híbrida** | Melhor custo-benefício + LGPD |
| **Produção Grande** (>500K/mês) | Local puro | Economia escala justifica investimento |

> **Nota LGPD**: Videocâmeras de UTIs são dados sensíveis (saúde + localização). A arquitetura híbrida garante que imagens brutas NUNCA saiam do hospital, apenas metadados anonimizados vão para nuvem.

> **Nota sobre Custos**: Os valores apresentados nesta seção são estimativas baseadas em pesquisas rápidas na web e têm caráter meramente didático. Na prática, os custos reais podem variar significativamente devido a flutuações cambiais (USD/BRL), alterações nas políticas de preço dos provedores de cloud, configurações específicas de região e contrato, custos ocultos de networking/egress/compliance, e necessidades particulares de hardware e mão de obra no cenário local. Recomenda-se sempre realizar um orçamento detalhado com os provedores antes de decisões de arquitetura em produção.

---

## 8. Referências

- [The Twelve-Factor App](https://12factor.net/)
- [Domain-Driven Design Reference - Eric Evans](https://domainlanguage.com/ddd/reference/)
- [Microservices Patterns - Chris Richardson](https://microservices.io/)
- [Saga Pattern](https://microservices.io/patterns/data/saga.html)
- [Strangler Fig Pattern](https://martinfowler.com/bliki/StranglerFigApplication.html)

---

**Análise concluída. Não implementar sem aprovação estratégica.**
