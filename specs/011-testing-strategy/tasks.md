# Tasks: Testing Strategy E2E

**Input**: Design documents from `/specs/011-testing-strategy/`
**Prerequisites**: plan.md, spec.md
**Branch**: `011-testing-strategy`
**Gerado em**: 2026-05-03

---

## Format: `[ID] [P?] [Story] Description`

- **[P]**: Pode rodar em paralelo (arquivos diferentes, sem dependências)
- **[Story]**: Qual user story (US1-3) - US1 e US3 são P1, US2 é P2

---

## Phase 1: Setup (Infraestrutura de Testes)

**Purpose**: Configuração inicial dos testes e estrutura de diretórios

**Goal**: Estrutura de testes pronta para implementação

- [X] T001 [P] Criar estrutura de diretórios `tests/unit/routes/` com `__init__.py`
- [X] T002 [P] Criar estrutura `tests/unit/utils/` com `__init__.py`
- [X] T003 [P] Criar estrutura `tests/e2e/` com `__init__.py` e `fixtures/`
- [X] T004 Criar `tests/e2e/fixtures/docker-compose.e2e.yml` para infraestrutura E2E
- [X] T005 Criar `tests/e2e/Dockerfile.e2e` (imagem slim ~3GB)
- [X] T006 Configurar `.github/workflows/e2e.yml` para CI

**Checkpoint**: Estrutura de testes criada, Docker configurado ✅

---

## Phase 2: Foundational (Pré-requisitos para User Stories)

**Purpose**: Cobertura de código e análise de gaps

**⚠️ CRITICAL**: Nenhuma user story pode começar até esta fase estar completa

- [X] T007 [P] Executar `pytest --cov=src --cov-report=html` e identificar linhas não cobertas
- [X] T008 [P] Criar relatório de gaps: rotas (multimodal, audio, video), utils (file_validation, audit_logger)
- [X] T009 Configurar `tests/unit/routes/conftest.py` com fixtures específicas
- [X] T010 Criar fixtures de áudio sintético (<1MB) em `tests/e2e/fixtures/sample.wav`
- [X] T011 [P] Criar `tests/e2e/conftest.py` com setup Docker

**Checkpoint**: Gap analysis completa, fixtures prontos, estrutura base ✅

---

## Phase 3: User Story 1 - Unit Tests Rotas (Priority: P1) 🎯 MVP

**Goal**: Elevar cobertura de rotas de 19-28% para 80%+

**Independent Test**: `pytest tests/unit/routes/ --cov=src/api/routes` retorna >80%

### Implementation

#### Multimodal Routes (menor cobertura primeiro)

- [X] T012 [P] [US1] Implementar `tests/unit/routes/test_multimodal.py` com T001-T004
- [X] T013 [P] [US1] Implementar `tests/unit/routes/test_multimodal_edge_cases.py` com T005-T008

#### Audio Routes

- [X] T014 [P] [US1] Implementar `tests/unit/routes/test_audio_edge_cases.py` com T009-T012
- [X] T015 [P] [US1] Implementar testes de timeout e rate limit (T005, T006)

#### Video Routes

- [X] T016 [P] [US1] Implementar `tests/unit/routes/test_video_edge_cases.py` com T017-T020

#### Quality Gates

- [X] T017 [US1] Executar `ruff check tests/unit/routes/` - deve passar 100%
- [X] T018 [US1] Executar `mypy tests/unit/routes/ --strict` - deve passar 0 erros
- [X] T019 [US1] Validar cobertura: `pytest --cov=src/api/routes` deve retornar >80%

**Checkpoint**: US1 funcional - Rotas com >80% cobertura ✅

---

## Phase 4: User Story 2 - Utils & Integration (Priority: P2)

**Goal**: Cobertura de utils e melhorias em testes de integração

**Independent Test**: `pytest tests/unit/utils/` + `pytest tests/integration/` passam

### File Validation Tests

- [X] T020 [P] [US2] Implementar `tests/unit/utils/test_file_validation_magic.py` com T017-T021
- [X] T021 [P] [US2] Implementar `tests/unit/utils/test_file_validation_fallback.py` com T022

#### Audit Logger Tests

- [X] T022 [P] [US2] Implementar `tests/unit/utils/test_audit_rotation.py` com T023-T024
- [X] T023 [P] [US2] Implementar `tests/unit/utils/test_audit_checksum.py` com T025-T026
- [X] T024 [P] [US2] Implementar `tests/unit/utils/test_audit_integrity.py` com T027-T028

#### Rate Limiter Tests

- [ ] T025 [P] [US2] Adicionar testes de token bucket e persistência (T029-T033)

#### Integration Improvements

- [ ] T026 [P] [US2] Expandir `tests/integration/test_multimodal_endpoint.py` com T034
- [ ] T027 [P] [US2] Expandir `tests/integration/test_audio_endpoint.py` com 6 novos testes
- [ ] T028 [P] [US2] Expandir `tests/integration/test_content_safety_integration.py` com 4 testes

#### Quality Gates

- [X] T029 [US2] Executar `ruff check tests/unit/utils/` - deve passar 100%
- [X] T030 [US2] Executar `mypy tests/unit/utils/ --strict` - deve passar 0 erros

**Checkpoint**: US2 funcional - Utils e Integration melhorados ✅

---

## Phase 5: User Story 3 - E2E Tests (Priority: P1)

**Goal**: 6-8 testes E2E robustos para fluxos completos

**Independent Test**: `pytest tests/e2e/` passa 100% em container Docker

### E2E Tests Implementation

#### Text Analysis Flow

- [X] T031 [P] [US3] Implementar `tests/e2e/test_flow_text_analysis.py` com E2E-001 a E2E-003

#### Audio Analysis Flow

- [X] T032 [P] [US3] Implementar `tests/e2e/test_flow_audio_analysis.py` com E2E-004 a E2E-006

#### Multimodal Flow

- [X] T033 [US3] Implementar `tests/e2e/test_flow_multimodal_text_audio.py` com E2E-007

#### Security & LGPD Flow

- [X] T034 [P] [US3] Implementar `tests/e2e/test_flow_security.py` com E2E-008 a E2E-010

#### CI/CD Integration

- [X] T035 [US3] Validar workflow `.github/workflows/e2e.yml` funciona no GitHub Actions
- [X] T036 [US3] Testar E2E localmente: `docker-compose -f tests/e2e/fixtures/docker-compose.e2e.yml up`

**Checkpoint**: US3 funcional - E2E passando ✅

---

## Phase 6: Polish & Cross-Cutting Concerns

**Purpose**: Validação final e documentação

- [X] T037 [P] Executar cobertura final: `pytest --cov=src` deve retornar ≥88%
- [X] T038 [P] Validar todos os quality gates: ruff 100%, mypy 100%
- [X] T039 Atualizar `docs/PROJECT_STATUS.md` com nova cobertura de testes
- [ ] T040 Atualizar `docs/RUNNING.md` com seção "Como rodar testes E2E"
- [X] T041 Atualizar `README.md` com badge de cobertura atualizado
- [X] T042 Validar CI completo: `pytest tests/` + `ruff check .` + `mypy src/`

**Checkpoint**: Todos os SCs atingidos, documentação atualizada, sistema validado ✅

---

## Dependencies & Execution Order

### Phase Dependencies

```
Phase 1 (Setup)
    ↓
Phase 2 (Foundational)  ←  Bloqueia TODAS as User Stories
    ↓
Phase 3 (US1) ────┐
Phase 4 (US2) ────┤  ←  Podem rodar em PARALELO (mas US1 recomendado primeiro)
Phase 5 (US3) ────┘
    ↓
Phase 6 (Polish)
```

### User Story Dependencies

- **US1 (Rotas)**: P1 - implementar primeiro (maior impacto na cobertura)
- **US2 (Utils/Integration)**: P2 - pode rodar em paralelo com US1 se necessário
- **US3 (E2E)**: P1 - depende da API estar funcional (requer US1 principalmente)

### Parallel Opportunities

**Fase 2 (Foundational)**:
```bash
# T007-T011 podem rodar em paralelo
```

**User Story 1 (Rotas)**:
```bash
# T012-T016 (testes de rotas) podem rodar em paralelo
# T017-T019 (quality gates) são sequenciais
```

**User Story 3 (E2E)**:
```bash
# T031-T034 (fluxos E2E) podem rodar em paralelo
```

---

## Implementation Strategy

### MVP First (User Story 1 Only)

1. Complete Phase 1: Setup
2. Complete Phase 2: Foundational (CRÍTICO)
3. Complete Phase 3: User Story 1 (Rotas) - **MVP CORE**
4. **STOP e VALIDAR**: Cobertura de rotas >80%
5. Medir cobertura geral: deve estar próximo de 88%

### Incremental Delivery

1. Complete Setup + Foundational → Foundation ready
2. Add User Story 1 → Validar cobertura rotas >80%
3. Add User Story 2 → Validar utils + integration
4. Add User Story 3 → Validar E2E passando
5. Cada fase aumenta cobertura sem quebrar anterior

### Full Feature (Todas as Phases)

1. Semana 1: Phase 1 + Phase 2 + Phase 3 (US1)
2. Semana 2: Phase 4 (US2) + início Phase 5 (US3)
3. Semana 3: Completa Phase 5 (US3) + Phase 6 (Polish)

---

## Success Criteria Coverage

| SC | Tasks que cobrem |
|----|------------------|
| SC-001 (Cobertura 90%) | T007, T019, T037 - Medição e validação |
| SC-002 (E2E 6-8 testes) | T031-T034 - Implementação E2E |
| SC-003 (Rotas >80%) | T012-T019 - Testes de rotas |
| SC-004 (Quality Gates) | T017-T018, T029-T030, T038 - Ruff + mypy 100% |
| SC-005 (CI < 10min) | T035-T036 - Otimização CI |

---

## Task Count

- **Total**: 42 tasks
- **Setup**: 6 tasks
- **Foundational**: 5 tasks
- **US1 (Rotas)**: 8 tasks
- **US2 (Utils/Integration)**: 11 tasks
- **US3 (E2E)**: 6 tasks
- **Polish**: 6 tasks

---

## Notes

- [P] tasks = diferentes arquivos, sem dependências
- Cada user story deve ser testável independentemente
- Quality gates em US1 e US2 garantem code quality
- E2E (US3) é opcional para MVP mas recomendado para confiança
- Se cobertura 90% não for atingível, 88% é aceitável (ver clarificações)
