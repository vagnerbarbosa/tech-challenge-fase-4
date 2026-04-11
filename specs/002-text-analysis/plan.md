# Implementation Plan: Análise de Texto

**Branch**: `002-text-analysis` | **Date**: 2026-04-11 | **Spec**: [spec.md](spec.md)
**Input**: Feature specification from `/specs/002-text-analysis/spec.md`

---

## Summary

Implementar endpoint POST `/analyze/text` que recebe texto em português, processa via Azure Text Analytics, aplica detecção local de risco baseada em palavras-chave, e retorna análise completa com sentimento, score, riscos de violência e saúde mental. Inclui cache em memória com TTL 1h para otimizar uso do Azure Free Tier.

---

## Technical Context

**Language/Version**: Python 3.11+
**Primary Dependencies**: FastAPI 0.104+, azure-ai-textanalytics 5.4.0, Pydantic v2
**Storage**: In-memory cache (dict with TTL)
**Testing**: pytest + pytest-asyncio + httpx
**Target Platform**: Linux (Docker)
**Project Type**: web-service
**Performance Goals**: Latência < 2s por requisição
**Constraints**: Azure Free Tier limit 5k req/mês, cache obrigatório
**Scale/Scope**: Single API endpoint, stateless com cache local

---

## Constitution Check

*GATE: Must pass antes de implementar*

- [x] LGPD: Não armazena texto original
- [x] Campos obrigatórios: risco_violencia e risco_saude_mental
- [x] Rate limiting: DEPENDE de 006-rate-limiting (hard stop por quota)
- [x] Type hints: obrigatório (mypy strict)

---

## Project Structure

### Documentation (this feature)

```text
specs/002-text-analysis/
├── spec.md              # Especificação (completed + clarified)
├── plan.md              # Este arquivo
└── tasks.md             # Lista de tarefas
```

### Source Code (repository root)

```text
src/
├── api/
│   ├── main.py           # Add router import
│   └── routes/
│       └── text.py       # NEW: Endpoint /analyze/text
├── core/
│   ├── config.py         # Add Azure Text config + Risk keywords
│   └── cache.py          # NEW: AnalysisCache class
├── models/
│   └── schemas.py        # NEW: TextAnalysisRequest/Response
├── services/
│   ├── text_analysis.py  # NEW: TextAnalysisService with risk detection
│   └── risk_detector.py  # NEW: Risk detection logic
└── infrastructure/
    └── azure_clients.py  # NEW: TextAnalyticsClient singleton

tests/
├── unit/
│   ├── services/
│   │   ├── test_text_analysis.py       # NEW
│   │   └── test_risk_detector.py       # NEW
│   └── core/
│       └── test_cache.py               # NEW
└── integration/
    └── test_text_endpoint.py           # NEW
```

---

## Data Model

### TextAnalysisRequest
```python
class TextAnalysisRequest(BaseModel):
    texto: str = Field(..., min_length=10, max_length=5000)
    tipo: Optional[str] = Field(default="geral", pattern="^(diario|prontuario|relato|geral)$")
    patient_id: Optional[str] = Field(default=None, description="ID anônimo do paciente")
```

### TextAnalysisResponse
```python
class TextAnalysisResponse(BaseModel):
    sentimento: str  # "positivo" | "negativo" | "neutro" | "misto"
    score: float  # -1.0 to 1.0
    risco_violencia: str  # "baixo" | "medio" | "alto" - OBRIGATÓRIO
    risco_saude_mental: str  # "baixo" | "medio" | "alto" - OBRIGATÓRIO
    palavras_chave: List[str]
    indicadores: List[str]  # Palavras de risco encontradas
    metadata: AnalysisMetadata

class AnalysisMetadata(BaseModel):
    correlation_id: str
    timestamp: datetime
    tempo_processamento_ms: int
    cache_hit: bool
    azure_calls: int
```

---

## Architecture Decisions

### Decisões Técnicas

1. **Cache**: In-memory dict com TTL 1h (simplificado, não requer Redis)
2. **Detecção de Risco**: Combinação sentimento Azure + palavras-chave locais
3. **Palavras-chave**: Lista pré-definida em config (não ML)
4. **Azure Client**: Singleton com lru_cache para reutilização
5. **Retry**: Policy padrão do Azure SDK (3 tentativas)

### Fluxo de Processamento

```
POST /analyze/text
    │
    ├──► Validação (Pydantic)
    │
    ├──► Check Cache (hit? retorna cache)
    │
    ├──► Sanitização Input
    │
    ├──► Chamada Azure Text Analytics
    │       ├── Sentimento
    │       └── Confiança
    │
    ├──► Detecção Local de Risco
    │       ├── Match palavras-chave violência
    │       └── Match palavras-chave saúde mental
    │
    ├──► Cálculo Score Final
    │       ├── Combinar sentimento + keywords
    │       └── Determinar níveis de risco
    │
    ├──► Store Cache
    │
    └──► Response
```

---

## Complexity Tracking

| Violation | Why Needed | Simpler Alternative Rejected Because |
|-----------|------------|-------------------------------------|
| Cache em memória | Azure Free Tier protection | Redis seria overkill para MVP |
| Detecção local de risco | Azure não classifica risco específico | Modelo customizado fora de escopo |
| Singleton Azure client | Performance (evita recriar conexão) | Criar a cada request é lento |

---

## Azure Configuration

```python
# Variáveis de ambiente necessárias:
AZURE_TEXT_ENDPOINT=https://<resource>.cognitiveservices.azure.com/
AZURE_TEXT_KEY=<key>
AZURE_TEXT_REGION=brazilsouth

# Configuração de palavras-chave (config/risk_keywords.py)
RISK_KEYWORDS = {
    "violencia": ["violência", "agressão", "ameaça", "bater", "machucar", "xingar"],
    "saude_mental": ["ansiedade", "depressão", "suicídio", "medo", "pânico", "tristeza", "choro"]
}
```

---

## API Contract

### Endpoint
```
POST /analyze/text
Content-Type: application/json
```

### Request
```json
{
  "texto": "Estou me sentindo muito ansiosa e tenho medo quando ele chega em casa",
  "tipo": "diario",
  "patient_id": "uuid-anonimo-123"
}
```

### Response 200
```json
{
  "sentimento": "negativo",
  "score": -0.85,
  "risco_violencia": "alto",
  "risco_saude_mental": "alto",
  "palavras_chave": ["ansiosa", "medo", "casa"],
  "indicadores": ["ansiedade", "medo"],
  "metadata": {
    "correlation_id": "abc-123-xyz",
    "timestamp": "2026-04-11T14:30:00Z",
    "tempo_processamento_ms": 450,
    "cache_hit": false,
    "azure_calls": 1
  }
}
```

### Response 400
```json
{
  "error": "VALIDATION_ERROR",
  "message": "Dados de entrada inválidos",
  "details": [
    {
      "field": "texto",
      "message": "Texto deve ter entre 10 e 5000 caracteres",
      "recebido": 5
    }
  ]
}
```

### Response 429
```json
{
  "error": "QUOTA_EXCEEDED",
  "message": "Limite de requisições ao Azure Text Analytics excedido",
  "retry_after": 3600
}
```

---

## Testing Strategy

### Unit Tests
- **TextAnalysisService**: Testar lógica de análise com mocks Azure
- **RiskDetector**: Testar detecção de palavras-chave
- **AnalysisCache**: Testar TTL e expiração

### Integration Tests
- **Endpoint**: Testar request/response completo
- **Azure Integration**: Testar com Azure real (ou mock)
- **Cache**: Testar cache hit/miss

### Test Cases Principais
1. Texto válido → 200 com análise completa
2. Texto curto (< 10 chars) → 400
3. Texto longo (> 5000 chars) → 400
4. Cache hit → resposta rápida, azure_calls: 0
5. Azure indisponível → 502
6. Texto com palavras de risco → risco alto
7. Texto neutro → risco baixo

### Validação de Precisão (> 80%)
**Método**: Dataset de teste com 20 casos rotulados manualmente
```python
# tests/fixtures/precision_test_cases.py
PRECISION_TEST_CASES = [
    {
        "texto": "Estou muito ansiosa e com medo",
        "expected_risco_saude_mental": "alto",
        "expected_risco_violencia": "baixo"
    },
    {
        "texto": "Ele me bateu ontem",
        "expected_risco_violencia": "alto",
        "expected_risco_saude_mental": "medio"
    },
    # ... 18 casos adicionais
]
```
**Critério de Aceite**: Acertar pelo menos 16/20 casos (80%)

---

## Success Criteria Verification

- [ ] Latência < 2s (medir com pytest benchmarks)
- [ ] Campos obrigatórios sempre presentes
- [ ] Integração Azure testada
- [ ] Cache funciona (hit/miss)
- [ ] Cobertura de testes > 70%
- [ ] Ruff e mypy passam

---

## Risk Mitigation

| Risk | Mitigation |
|------|------------|
| Azure indisponível | Exception handler retorna 502 |
| Quota excedida | Cache + rate limiting (futuro) |
| Latência alta | Cache + timeout 30s |
| Detecção de risco imprecisa | Combinar com sentimento Azure |

---

## Notes

- **Prioridade**: P1 (bloqueia fusão multimodal)
- **Dependências**: 001-bootstrap (completo)
- **Bloqueia**: 005-multimodal-fusion
- **Clarificações aplicadas**: 3 (detecção de risco, cache, keywords)
