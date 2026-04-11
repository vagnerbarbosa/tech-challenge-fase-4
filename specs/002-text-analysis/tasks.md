---
description: "Task list for text analysis feature implementation"
---

# Tasks: Análise de Texto

**Input**: Design documents from `/specs/002-text-analysis/`
**Prerequisites**: plan.md (required), spec.md (required for user stories)
**Tests**: Sim, incluídos nas tasks

---

## Phase 1: Setup e Configuração

**Purpose**: Configurar Azure e estrutura de cache

- [ ] T001 Adicionar dependência azure-ai-textanalytics no pyproject.toml
  - `poetry add azure-ai-textanalytics>=5.4.0`
  - Rodar `poetry install`
  - [Link para spec](spec.md#technical-notes)

- [ ] T002 Configurar Azure Text Analytics no Portal Azure
  - Criar recurso Cognitive Services
  - Copiar endpoint e key para .env
  - [Link para spec](spec.md#azure-configuration)

---

## Phase 2: Foundational (Blocking Prerequisites)

**Purpose**: Core infrastructure que BLOQUEIA todas as user stories

**⚠️ CRITICAL**: No user story work can begin until this phase is complete

- [X] T003 [P] Criar `src/models/schemas.py` com TextAnalysisRequest
  - Atributos: texto (str, min=10, max=5000), tipo (str), patient_id (str)
  - Validadores Pydantic v2
  - **Depends**: Nenhum

- [X] T004 [P] Criar `src/models/schemas.py` com TextAnalysisResponse
  - Atributos: sentimento, score, risco_violencia, risco_saude_mental, palavras_chave, indicadores, metadata
  - **Depends**: Nenhum

- [X] T005 Criar `src/core/cache.py` com AnalysisCache
  - Métodos: get(key), set(key, value), clear_expired()
  - TTL: 60 minutos
  - **Depends**: T003, T004

- [X] T006 Criar `src/core/config.py` com RISK_KEYWORDS
  - Dicionário de palavras-chave de violência e saúde mental
  - **Depends**: Nenhum

- [X] T007 Criar `src/infrastructure/azure_clients.py`
  - Singleton get_text_analytics_client() com @lru_cache
  - Retry policy configurada
  - **Depends**: T002

**Checkpoint**: Foundation ready - user story implementation can now begin in parallel

---

## Phase 3: User Story 1 - Análise de Sentimento (Priority: P1) 🎯 MVP

**Goal**: Implementar endpoint POST /analyze/text com análise completa

**Independent Test**: POST /analyze/text retorna análise com sentimento, riscos e palavras-chave

### Tests for User Story 1 (REQUIRED)

> **NOTE: Write these tests FIRST, ensure they FAIL before implementation**

- [X] T008 [P] Contract test em `tests/integration/test_text_endpoint.py`
  - Testa request/response schema
  - Verifica HTTP 200 para input válido
  - Verifica HTTP 400 para input inválido

- [X] T009 [P] Unit test em `tests/unit/services/test_risk_detector.py`
  - Testa detecção de palavras-chave
  - Testa cálculo de risco

### Implementation for User Story 1

- [X] T010 [P] Criar `src/services/risk_detector.py`
  - Função calculate_risk(text, sentiment) -> dict
  - Match de palavras-chave contra RISK_KEYWORDS
  - Retorna risco_violencia, risco_saude_mental, indicadores
  - **Depends**: T006

- [X] T011 Criar `src/services/text_analysis.py`
  - Classe TextAnalysisService
  - Método analyze(text) -> TextAnalysisResult
  - Integra cache, Azure SDK, risk_detector
  - **Depends**: T005, T007, T010

- [X] T012 Criar `src/api/routes/text.py`
  - Endpoint POST /analyze/text
  - Injeção de dependências FastAPI
  - Tratamento de exceções
  - **Depends**: T011

- [X] T013 Atualizar `src/api/main.py`
  - Incluir router text
  - **Depends**: T012

**Checkpoint**: User Story 1 should be fully functional and testable independently

---

## Phase 4: User Story 2 - Integração Azure (Priority: P1)

**Goal**: Garantir integração robusta com Azure Text Analytics

**Independent Test**: Chamadas Azure funcionam corretamente com retry e error handling

### Tests for User Story 2 (REQUIRED)

- [X] T014 [P] Integration test em `tests/integration/test_azure_services.py`
  - Testa chamada real (ou mockada) ao Azure
  - Testa retry em falhas
  - Testa timeout

### Implementation for User Story 2

- [X] T015 Criar tratamento de exceções em `src/infrastructure/azure_clients.py`
  - safe_azure_call() wrapper
  - Mapeia HttpResponseError para exceções da aplicação
  - **Depends**: T007

- [X] T016 Adicionar sanitização de input em `src/services/text_analysis.py`
  - Função sanitize_text_input()
  - Remove zero-width characters, control chars
  - **Depends**: T011

- [X] T017 Adicionar logging estruturado em `src/services/text_analysis.py`
  - structlog para auditoria
  - Log: correlation_id, duration, cache_hit
  - **Depends**: T011

**Checkpoint**: User Stories 1 AND 2 should both work independently

---

## Phase 5: User Story 3 - Extração de Palavras-Chave (Priority: P2)

**Goal**: Retornar palavras-chave significativas do texto

**Independent Test**: Response inclui array palavras_chave extraídas do texto

### Implementation for User Story 3

- [X] T018 [P] Implementar extração de palavras-chave em `src/services/text_analysis.py`
  - Extrair palavras relevantes do texto (TF-IDF simples ou regex)
  - Limitar a 10 palavras mais relevantes
  - **Depends**: T011

- [X] T019 Atualizar `src/services/text_analysis.py`
  - Incluir palavras_chave no resultado
  - **Depends**: T018

**Checkpoint**: Todas user stories funcionam

---

## Phase 6: Polish & Cross-Cutting Concerns

**Purpose**: Melhorias que afetam todas as user stories

- [X] T020 [P] Criar unit tests em `tests/unit/core/test_cache.py`
  - Testa TTL, expiração, clear
  - **Depends**: T005

- [X] T021 Adicionar headers de rate limit em `src/api/routes/text.py`
  - X-RateLimit-Remaining
  - **Depends**: T012

- [X] T022 Atualizar documentação em `specs/README.md`
  - Mudar status de 002-text-analysis para "Em Progresso"

- [X] T023 Commit e PR
  - Mensagem: `feat: implementa análise de texto com Azure Text Analytics`
  - Branch: `002-text-analysis`
  - Todos testes passando
  - Ruff e mypy passando

- [X] T024 [P] Criar teste de stress/cache invalidation em `tests/unit/core/test_cache_stress.py`
  - Testa comportamento com múltiplas threads/concorrência
  - Testa invalidação manual de entradas
  - Verifica memory leaks com grandes volumes
  - **Depends**: T005

---

## Dependencies & Execution Order

### Phase Dependencies

```
Setup (Phase 1): T001, T002
    ↓
Foundational (Phase 2): T003-T007 (CRITICAL - blocks all user stories)
    ↓
User Story 1 (Phase 3): T008-T013
    ↓
User Story 2 (Phase 4): T014-T017
    ↓
User Story 3 (Phase 5): T018-T019
    ↓
Polish (Phase 6): T020-T023
```

### Task Dependencies

```
T001 → T007 → T011 → T012 → T013
  ↓
T002 ─┘      ↑
           T005 → T011
             ↑
T003 ────────┘

T006 → T010 → T011

T004 ────────────┘
```

### Parallel Opportunities

- T003 e T004 (models independentes)
- T005, T006, T007 (infra independente)
- T008 e T009 (testes independentes)
- T010 (risk_detector) pode rodar em paralelo com T011 setup

---

## Implementation Strategy

### MVP First (User Story 1 Only)

1. Complete Phase 1: Setup
2. Complete Phase 2: Foundational (CRITICAL)
3. Complete Phase 3: User Story 1
4. **STOP and VALIDATE**: Test User Story 1 independently
5. Deploy/demo se ready

### Incremental Delivery

1. Complete Setup + Foundational → Foundation ready
2. Add User Story 1 → Test → Demo (MVP!)
3. Add User Story 2 → Test → Demo
4. Add User Story 3 → Test → Demo
5. Polish → Final

---

## Validation Checklist

Antes de marcar como completo:

- [ ] Endpoint POST /analyze/text responde em localhost:8000
- [ ] Testes unitários passam: `pytest tests/unit/ -v`
- [ ] Testes integração passam: `pytest tests/integration/ -v`
- [ ] Campos obrigatórios presentes: risco_violencia, risco_saude_mental
- [ ] Cache funciona (hit/miss verificável)
- [ ] Azure integration testada
- [ ] Ruff passa: `poetry run ruff check .`
- [ ] Mypy passa: `poetry run mypy src/`
- [ ] Swagger mostra endpoint em /docs
