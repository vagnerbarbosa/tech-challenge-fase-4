# Implementation Plan: Testing Strategy E2E

**Branch**: `[011-testing-strategy]` | **Date**: 2026-05-03 | **Spec**: [spec.md](spec.md)
**Input**: Feature specification from `/specs/011-testing-strategy/spec.md`

## Summary

Elevar cobertura de testes de **81.61% para 90%** através de estratégia híbrida:
- **Unit Tests**: Rotas multimodal, audio, video (19-28% → 80%+)
- **Integration Tests**: Melhorias em testes existentes de endpoints
- **E2E Tests**: Fluxos completos de texto e áudio com Docker (imagem slim ~3GB)

**Meta**: 90% cobertura + 6-8 testes E2E robustos em 3 semanas.

**Obrigatório**: Consultar Context7 para melhores práticas 2026 antes de cada fase de implementação. Code quality: Ruff e mypy 100% limpos.

## Technical Context

**Language/Version**: Python 3.11+
**Primary Dependencies**: pytest, pytest-asyncio, requests, FastAPI TestClient
**Storage**: SQLite (test DB), Local filesystem (temp files)
**Testing**: pytest com pytest-cov, pytest-asyncio para testes async
**Target Platform**: Docker containers (GitHub Actions + Local)
**Project Type**: web-service (test infrastructure)
**Performance Goals**: CI < 10 min (build + test), E2E < 5 min
**Constraints**: Imagem Docker slim (~3GB, sem YOLO/PyTorch), cobertura 90%
**Scale/Scope**: ~330 statements adicionais para cobrir

## Constitution Check

*GATE: Must pass before Phase 0 research. Re-check after Phase 1 design.*

| Principle | Status | Notes |
|-----------|--------|-------|
| LGPD Compliance | ✅ PASS | Testes não logam dados sensíveis; patient IDs hasheados |
| Azure Free Tier Protection | ✅ PASS | Mock mode obrigatório para E2E; não consome quota |
| Test Coverage >70% | ⚠️ CONDITIONAL | Meta é 90%; gap de 330 statements |
| Container-First | ✅ PASS | E2E roda em containers Docker |
| Documentação em Português | ✅ PASS | Spec e plan em português; testes em inglês (código) |
| Security-First | ✅ PASS | Testes validam autenticação e rate limiting |
| Multimodal Architecture | ✅ PASS | Testes cobrem independência de modalidades |
| **Code Quality** | **⚠️ CRITICAL** | **Ruff e mypy 100% limpos obrigatório** |

## Project Structure

### Documentation (this feature)

```text
specs/011-testing-strategy/
├── plan.md              # This file
├── research.md          # Phase 0 output
├── data-model.md        # Phase 1 output (N/A - testes não têm modelo)
├── quickstart.md        # Phase 1 output
└── tasks.md             # Phase 2 output
```

### Source Code (repository root)

```text
tests/
├── unit/routes/         # Testes de rotas (multimodal, audio, video)
│   ├── test_multimodal.py
│   ├── test_multimodal_edge_cases.py
│   ├── test_audio_edge_cases.py
│   ├── test_video_edge_cases.py
│   └── conftest.py
├── unit/utils/          # Testes de utilitários
│   ├── test_file_validation_magic.py
│   ├── test_file_validation_fallback.py
│   ├── test_audit_rotation.py
│   ├── test_audit_checksum.py
│   └── test_audit_integrity.py
├── integration/         # Testes existentes (melhorias)
├── e2e/                 # Testes end-to-end (NOVO)
│   ├── conftest.py
│   ├── test_flow_text_analysis.py
│   ├── test_flow_audio_analysis.py
│   ├── test_flow_multimodal_text_audio.py
│   ├── test_flow_security.py
│   └── fixtures/
│       ├── Dockerfile.e2e
│       ├── docker-compose.e2e.yml
│       └── sample_files/
└── e2e-video/           # Melhoria futura (full com YOLO)
```

**Structure Decision**: Organização hierárquica por tipo de teste (unit/integration/e2e), com e2e separado para infraestrutura Docker.

## Phase 0: Research & Decisions

### Context7 Research (Obrigatório)

**Consultas obrigatórias antes da implementação:**

1. **pytest best practices 2026** — Context7
   - Fixtures modernas, parametrização, async patterns
   
2. **Docker optimization Python 2026** — Context7
   - Multi-stage builds, layer caching, slim images
   
3. **E2E testing patterns 2026** — Context7
   - Testcontainers vs docker-compose, health checks

### NEEDED: Research Topics

1. **E2E Frameworks**: Comparar pytest-docker vs docker-compose + requests puro
2. **Coverage Strategy**: Identificar exatamente quais linhas faltam nas rotas
3. **Imagem Docker Slim**: Confirmar tamanho sem YOLO (~3GB vs 13GB)

### Decisions

| Decision | Rationale |
|----------|-----------|
| E2E sem vídeo | Imagem 13GB muito pesada para CI; vídeo coberto por integration tests |
| Docker slim | Apenas texto + áudio; sem PyTorch/OpenCV/YOLO |
| requests puro | Simplicidade; sem pytest-docker adicional |

## Phase 1: Design

### Test Architecture

```
┌─────────────────────────────────────────────────────────────┐
│                    Test Pyramid                              │
├─────────────────────────────────────────────────────────────┤
│  E2E (6-8 tests)    → Fluxos completos (texto + áudio)      │
│  Integration (40+)  → Endpoints com mocks                  │
│  Unit (80+)         → Rotas, utils, edge cases             │
└─────────────────────────────────────────────────────────────┘
```

### E2E Test Matrix

| ID | Cenário | Validations |
|----|---------|-------------|
| E2E-001 | Texto → análise completa | risco_saude_mental, content_safety, audit log |
| E2E-002 | Texto espanhol | auto-detect idioma funciona |
| E2E-003 | Rate limiting 60 req | 429 retornado, headers presentes |
| E2E-004 | Áudio WAV → transcrição | transcricao, idioma_detectado, prosódica |
| E2E-005 | Áudio múltiplos formatos | WAV, MP3, OGG aceitos |
| E2E-006 | Áudio >50MB rejeitado | 413 retornado |
| E2E-007 | Multimodal texto+áudio | fusão com confiança, metadados |
| E2E-008 | Auth inválida → 401 | X-API-Key validado |
| E2E-009 | LGPD patient_id hash | audit log sem dados brutos |

### Docker Configuration

```yaml
# Dockerfile.e2e (Slim)
FROM python:3.11-slim
# Sem: ultralytics, opencv-python, torch
# Com: fastapi, librosa, azure-speech, pytest
```

### Contracts

N/A - Testes consomem API existente; não expõem novas interfaces.

## Phase 2: Planning

### Quality Gates por Fase

**Antes de iniciar cada fase:**
- [ ] `ruff check tests/` — Deve passar 100% limpo
- [ ] `mypy tests/ --strict` — Deve passar sem erros
- [ ] `ruff format --check tests/` — Código formatado

**Consulta Context7 obrigatória:**
- Antes de implementar: consultar melhores práticas pytest 2026
- Antes de Docker: consultar otimização Docker Python 2026
- Durante E2E: consultar padrões de testes E2E com requests

### Week 1: Unit Tests (Rotas)

- [ ] Consultar Context7: "pytest best practices 2026"
- [ ] T001-T008: Multimodal happy path + edge cases
- [ ] T009-T016: Audio edge cases
- [ ] T017-T020: Video edge cases (básico)
- [ ] **Gate**: Ruff + mypy 100% limpos

### Week 2: Utils + Integration

- [ ] Consultar Context7: "file validation testing patterns 2026"
- [ ] T021-T028: File validation (magic + fallback)
- [ ] T029-T032: Audit logger (rotação, checksum)
- [ ] T033-T038: Integration improvements
- [ ] **Gate**: Ruff + mypy 100% limpos

### Week 3: E2E

- [ ] Consultar Context7: "E2E testing with Docker and requests 2026"
- [ ] Consultar Context7: "Docker optimization Python multi-stage 2026"
- [ ] E2E-001 a E2E-003: Texto fluxos
- [ ] E2E-004 a E2E-007: Áudio + multimodal
- [ ] E2E-008 a E2E-009: Security + LGPD
- [ ] **Gate**: Ruff + mypy 100% limpos

### Success Metrics

| Metric | Target | How to Measure |
|--------|--------|----------------|
| Coverage | 90% | `pytest --cov=src` |
| E2E Pass | 100% | `pytest tests/e2e` |
| CI Time | < 10 min | GitHub Actions |
| Flaky Tests | 0% | Monitor 5 runs |

## Complexity Tracking

| Violation | Why Needed | Simpler Alternative Rejected Because |
|-----------|------------|-------------------------------------|
| E2E sem vídeo | Imagem 13GB inviável | Testar vídeo em integration é suficiente |
| Docker slim adicional | Imagem prod muito pesada | Não alterar Dockerfile prod para testes |
| 3 tipos de testes | Coverage 90% requer camadas | Apenas unit não cobre fluxos completos |

## Phase 3: Documentation Update

Após implementação dos testes, atualizar documentação do projeto:

### Documentação a Atualizar

- [ ] `docs/PROJECT_STATUS.md` — Atualizar cobertura de testes (81% → 90%)
- [ ] `docs/RUNNING.md` — Adicionar seção "Como rodar testes E2E"
- [ ] `README.md` — Atualizar badge de cobertura e adicionar seção de testes
- [ ] `CLAUDE.md` — Atualizar contexto técnico se necessário
- [ ] `.github/workflows/README.md` — Documentar novo workflow e2e.yml

### Definition of Done

- [ ] Cobertura 90% verificada via `pytest --cov=src`
- [ ] Todos os testes E2E passando no GitHub Actions
- [ ] **Ruff 100% limpo**: `ruff check tests/` — 0 erros, 0 warnings
- [ ] **mypy 100% limpo**: `mypy tests/ --strict` — 0 erros
- [ ] Documentação atualizada e revisada
- [ ] PR mergeado para main

## Generated Artifacts

- [ ] research.md (Phase 0)
- [ ] quickstart.md (Phase 1)
- [ ] tasks.md (Phase 2 - via speckit.tasks)

