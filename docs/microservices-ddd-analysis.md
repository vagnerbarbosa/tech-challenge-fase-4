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
│                              API Gateway                                      │
│  (Kong / Nginx / AWS API Gateway)                                           │
│  - Roteamento                                                                │
│  - Rate Limiting global                                                      │
│  - Autenticação inicial (JWT validation)                                     │
└─────────────────────────────────────────────────────────────────────────────┘
                                       │
           ┌───────────────────────────┼───────────────────────────┐
           │                           │                           │
           ▼                           ▼                           ▼
┌─────────────────────┐  ┌─────────────────────┐  ┌─────────────────────┐
│   Text Service      │  │   Audio Service     │  │   Video Service     │
│   (text-service)    │  │   (audio-service)   │  │   (video-service)   │
│                     │  │                     │  │                     │
│  Python + FastAPI   │  │  Python + FastAPI │  │  Python + FastAPI   │
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
           ┌──────────────────────┼──────────────────────┐
           │                      │                      │
           ▼                      ▼                      ▼
┌─────────────────────┐  ┌─────────────────────┐  ┌─────────────────────┐
│   Identity Service  │  │   Audit Service     │  │   Gateway Config    │
│   (identity-svc)    │  │   (audit-svc)       │  │   (kong/nginx)      │
│                     │  │                     │  │                     │
│  - JWT/OAuth2       │  │  - Event sourcing   │  │  - Rate limiting    │
│  - API Keys         │  │  - LGPD compliance  │  │  - SSL/TLS          │
│  - RBAC             │  │  - Retenção 5 anos  │  │  - Routing          │
└─────────────────────┘  └─────────────────────┘  └─────────────────────┘

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

#### Serviço 5: Identity & Access Service (`identity-service`)

**Responsabilidade**: Autenticação e autorização

**Entidades (DDD)**:
```python
class ApiKey:
    key_id: str
    key_hash: str
    tenant_id: str
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

**API REST**:
```yaml
POST /v1/auth/keys          # Criar API Key (admin)
DELETE /v1/auth/keys/{id}   # Revogar (admin)
POST /v1/auth/verify        # Verificar token (internal)
GET /v1/auth/me             # Info da API Key
```

**Tecnologia**:
- Python + FastAPI
- JWT (para tokens temporários)
- Redis (sessões)
- PostgreSQL (API Keys persistentes)

**Alternativa: Gateway com Auth Integrado**

| Aspecto | Gateway + Auth Integrado | Identity Service Separado |
|---------|---------------------------|----------------------------|
| **Latência** | ✅ Menor (sem network hop) | ❌ +1-5ms (chamada interna) |
| **Complexidade** | ✅ Menor (um serviço a menos) | ❌ Maior (mais um serviço) |
| **Acoplamento** | ❌ Gateway "gordo" | ✅ Separação de concerns |
| **Escalabilidade** | ⚠️ Gateway precisa escalar junto com auth | ✅ Auth escala independente |
| **Reutilização** | ❌ Só funciona com esse Gateway | ✅ Múltiplos gateways podem usar |
| **LGPD/Audit** | ⚠️ Mesmo serviço faz tudo | ✅ Identity focado, Audit separado |
| **Hot reload config** | ❌ Requer restart do Gateway | ✅ Config muda sem afetar routing |
| **Testabilidade** | ⚠️ Mais difícil testar isolado | ✅ Fácil testar auth separado |

**Quando usar Gateway com Auth:**
- Time pequeno (3-5 devs)
- Só existe um gateway
- Auth simples (só API Keys, sem RBAC complexo)
- Latência é crítica (sub-10ms)

**Quando usar Identity Service separado:**
- Multi-tenancy ou múltiplos gateways
- Auth complexo (OAuth2, OIDC, RBAC)
- Need de evoluir auth sem tocar no gateway
- Compliance requer isolamento de responsabilidades

> **Recomendação para este projeto**: Gateway com auth integrado é suficiente. Identity Service só vale a pena se:
> 1. Surge necessidade de múltiplos gateways (mobile, web, partner)
> 2. Auth evolui para OAuth2/SSO
> 3. Time cresce e precisa de especialização

---

#### Serviço 6: Audit Service (`audit-service`)

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

### Custos

| Item | Monolito (mensal) | Microserviços (mensal) |
|------|-------------------|------------------------|
| Infraestrutura | R$ 2.000 | R$ 3.500 (+75%) |
| Operação | R$ 1.000 | R$ 2.000 (+100%) |
| Desenvolvimento | R$ 5.000 | R$ 4.000 (-20%) |
| **Total** | **R$ 8.000** | **R$ 9.500** (+19%) |

> Nota: Custo adicional compensado pela redução de incidentes, maior velocity e capacidade de escalar serviços pesados (áudio/vídeo com GPU) independentemente dos serviços leves (texto).

---

## 8. Referências

- [The Twelve-Factor App](https://12factor.net/)
- [Domain-Driven Design Reference - Eric Evans](https://domainlanguage.com/ddd/reference/)
- [Microservices Patterns - Chris Richardson](https://microservices.io/)
- [Saga Pattern](https://microservices.io/patterns/data/saga.html)
- [Strangler Fig Pattern](https://martinfowler.com/bliki/StranglerFigApplication.html)

---

**Análise concluída. Não implementar sem aprovação estratégica.**
