# Tasks: Security Hardening 2026

**Input**: Design documents from `/specs/007-security-hardening/`
**Prerequisites**: plan.md, spec.md, data-model.md, contracts/
**Branch**: `007-security-hardening`
**Gerado em**: 2026-04-22

---

## Format: `[ID] [P?] [Story] Description`

- **[P]**: Pode rodar em paralelo (arquivos diferentes, sem dependências)
- **[Story]**: Qual user story (US1-7) - US1-4 são P1, US5-7 são P2

---

## Phase 1: Setup (Infraestrutura de Segurança)

**Purpose**: Configuração inicial das dependências e estrutura de segurança

**Goal**: Adicionar bibliotecas de segurança sem quebrar o build existente

- [ ] T001 Atualizar `pyproject.toml` com dependências de segurança (`python-magic`, `slowapi` como extras)
- [ ] T002 [P] Criar estrutura de pastas `src/core/security/` (módulo de segurança isolado)
- [ ] T003 Adicionar configurações de segurança em `src/core/config.py` (`SecurityConfig` Pydantic)
- [ ] T004 Atualizar `.env.example` com variáveis de segurança (`SECURITY_API_KEY`, `SECURITY_CORS_ORIGINS`, etc.)

**Checkpoint**: Build passa, dependências instaláveis via `poetry install --extras security`

---

## Phase 2: Foundational (Pré-requisitos Bloqueantes) ⚠️ CRÍTICO

**Purpose**: Middlewares e serviços base que TODAS as user stories precisam

**⚠️ CRITICAL**: Nenhuma user story pode começar até esta fase estar completa

### Exceções e Configuração Base
- [ ] T005 [P] Criar exceções de segurança em `src/core/exceptions.py` (`UnauthorizedException`, `ForbiddenException`, `RateLimitExceeded`)
- [ ] T006 Implementar `SecurityContext` Pydantic model em `src/core/security/models.py` (request-scoped security data)

### Log Sanitization (Base para US3)
- [ ] T007 [P] Implementar `LogSanitizer` em `src/core/security/log_sanitizer.py` (mascaramento de secrets)
- [ ] T008 Adicionar structlog processor para sanitização automática em `src/core/logging_config.py`

### Audit Logger Base (Base para US6)
- [ ] T009 [P] Implementar `AuditLogger` em `src/utils/audit_logger.py` (JSON Lines append-only)
- [ ] T010 Configurar rotação de logs de auditoria em `src/core/config.py`

**Checkpoint**: Foundation pronta - User Stories podem começar em paralelo

---

## Phase 3: User Story 1 - Autenticação e Autorização (Priority: P1) 🎯 MVP

**Goal**: API Key authentication funcional em todos os endpoints protegidos

**Independent Test**: Endpoint `/health` retorna 401 sem API Key, 200 com API Key válida

### Tests (TDD obrigatório - testes primeiro)
- [ ] T011 [P] [US1] Teste unitário `test_api_key_validator.py` - validação de key válida/inválida/vazia
- [ ] T012 [P] [US1] Teste de integração `test_auth_endpoints.py` - 401 sem key, 200 com key
- [ ] T013 [P] [US1] Teste de segurança `test_bola_protection.py` - acesso a recurso de outro usuário retorna 403

### Implementation
- [ ] T014 [P] [US1] Implementar `APIKeyValidator` em `src/core/security/auth.py` (validação de key)
- [ ] T015 [P] [US1] Implementar RBAC básico em `src/core/security/auth.py` (roles: read, write, admin)
- [ ] T016 [US1] Criar FastAPI dependency `require_api_key()` em `src/api/dependencies.py`
- [ ] T017 [US1] Implementar `BOLAProtector` em `src/core/security/auth.py` (verificação de ownership)
- [ ] T018 [US1] Aplicar autenticação em endpoints protegidos em `src/api/routes/*.py` (exceto health em dev)
- [ ] T019 [US1] Atualizar endpoint `/health` em `src/api/routes/health.py` (requer auth em produção)

**Checkpoint**: US1 funcional - `curl -H "X-API-Key: key" /health` funciona; sem key retorna 401

---

## Phase 4: User Story 2 - Validação de Uploads (Priority: P1)

**Goal**: Arquivos maliciosos e path traversal são bloqueados antes do processamento

**Independent Test**: Upload de `.exe` renomeado para `.mp3` é rejeitado; path traversal sanitizado

### Tests (TDD obrigatório)
- [ ] T020 [P] [US2] Teste unitário `test_magic_bytes_validator.py` - validação MIME real
- [ ] T021 [P] [US2] Teste unitário `test_filename_sanitizer.py` - path traversal removal
- [ ] T022 [P] [US2] Teste de integração `test_upload_security.py` - uploads maliciosos bloqueados

### Implementation
- [ ] T023 [P] [US2] Implementar `MagicBytesValidator` em `src/core/security/file_validator.py` (python-magic)
- [ ] T024 [P] [US2] Implementar `FilenameSanitizer` em `src/core/security/file_validator.py` (path traversal)
- [ ] T025 [US2] Criar FastAPI dependency `validate_upload_file()` em `src/api/dependencies.py`
- [ ] T026 [US2] Integrar validação em `/analyze/audio` em `src/api/routes/audio.py`
- [ ] T027 [US2] Integrar validação em `/analyze/video` em `src/api/routes/video.py`
- [ ] T028 [US2] Adicionar validação de tamanho de arquivo (streaming) em `src/utils/file_validation.py`

**Checkpoint**: US2 funcional - uploads maliciosos rejeitados; nomes sanitizados

---

## Phase 5: User Story 3 - Sanitização de Dados (Priority: P1)

**Goal**: Secrets e dados sensíveis nunca expostos em logs ou erros

**Independent Test**: Grep em logs de teste não encontra API keys ou patient_ids em plaintext

### Tests (TDD obrigatório)
- [ ] T029 [P] [US3] Teste unitário `test_log_sanitizer.py` - mascaramento de secrets
- [ ] T030 [P] [US3] Teste de segurança `test_secrets_in_logs.py` - grep não encontra secrets
- [ ] T031 [P] [US3] Teste de integração `test_error_handling.py` - mensagens genéricas em produção

### Implementation
- [ ] T032 [P] [US3] Refinar `LogSanitizer` em `src/core/security/log_sanitizer.py` (Azure keys, patient_id)
- [ ] T033 [US3] Implementar `PatientIdHasher` em `src/core/security/log_sanitizer.py` (SHA256)
- [ ] T034 [US3] Criar exception handlers genéricos em `src/api/main.py` (produção vs dev)
- [ ] T035 [US3] Atualizar todos os services para usar `PatientIdHasher` em logs (audio, video, text)
- [ ] T036 [US3] Implementar `SecretMasker` em `src/core/security/log_sanitizer.py` (Azure keys)
- [ ] T037 [US3] Garantir que `AuditLogger` não loga dados sensíveis em `src/utils/audit_logger.py`

**Checkpoint**: US3 funcional - `grep -r "sua-api-key" logs/` retorna vazio

---

## Phase 6: User Story 4 - Rate Limiting (Priority: P1)

**Goal**: Proteção contra DDoS e credential stuffing via rate limiting

**Independent Test**: Após 60 req/min, cliente recebe 429 com Retry-After

### Tests (TDD obrigatório)
- [ ] T038 [P] [US4] Teste unitário `test_rate_limiter.py` - token bucket algorithm
- [ ] T039 [P] [US4] Teste de integração `test_rate_limit_endpoints.py` - 429 após limite
- [ ] T040 [P] [US4] Teste de carga `test_rate_limit_parallel.py` - concorrência

### Implementation
- [ ] T041 [P] [US4] Implementar `TokenBucketRateLimiter` em `src/core/security/rate_limiter.py`
- [ ] T042 [P] [US4] Criar Redis backend para rate limit em `src/core/security/rate_limiter.py` (opcional)
- [ ] T043 [US4] Criar Memory backend para rate limit em `src/core/security/rate_limiter.py` (fallback)
- [ ] T044 [US4] Configurar slowapi/limiter em `src/api/main.py`
- [ ] T045 [US4] Aplicar rate limits diferenciados em `src/api/routes/*.py` (auth 5/min, analyze 60/min)
- [ ] T046 [US4] Adicionar headers X-RateLimit-* em todas as respostas em `src/api/middleware/rate_limit.py`
- [ ] T047 [US4] Implementar rate limiting específico para auth em `src/api/routes/auth.py` (brute force protection)

**Checkpoint**: US4 funcional - `curl` 61x em 1 min, última retorna 429

---

## Phase 7: User Story 5 - Headers de Segurança (Priority: P2)

**Goal**: Todas as respostas HTTP incluem headers de segurança OWASP

**Independent Test**: `curl -I` em qualquer endpoint retorna HSTS, CSP, X-Frame-Options, etc.

### Tests (TDD obrigatório)
- [ ] T048 [P] [US5] Teste de integração `test_security_headers.py` - headers presentes em todas respostas
- [ ] T049 [P] [US5] Teste de segurança `test_csp_policy.py` - CSP válido

### Implementation
- [ ] T050 [P] [US5] Implementar `SecurityHeadersMiddleware` em `src/core/security/middleware.py`
- [ ] T051 [US5] Configurar headers HSTS em `src/core/security/middleware.py` (produção apenas)
- [ ] T052 [US5] Configurar CSP em `src/core/security/middleware.py` (configurável via .env)
- [ ] T053 [US5] Adicionar X-Content-Type-Options em `src/core/security/middleware.py`
- [ ] T054 [US5] Adicionar X-Frame-Options em `src/core/security/middleware.py`
- [ ] T055 [US5] Adicionar Referrer-Policy em `src/core/security/middleware.py`
- [ ] T056 [US5] Registrar middleware em `src/api/main.py`

**Checkpoint**: US5 funcional - `curl -I /health | grep "X-Frame-Options"` retorna DENY

---

## Phase 8: User Story 6 - Auditoria LGPD (Priority: P2)

**Goal**: Logs de auditoria estruturados para compliance LGPD

**Independent Test**: Cada acesso a dados de paciente gera entrada JSON Lines em logs/audit/

### Tests (TDD obrigatório)
- [ ] T057 [P] [US6] Teste unitário `test_audit_logger.py` - geração de logs estruturados
- [ ] T058 [P] [US6] Teste de integração `test_audit_endpoints.py` - eventos auditáveis geram logs
- [ ] T059 [P] [US6] Teste de LGPD `test_audit_export.py` - exportação para formato ANPD

### Implementation
- [ ] T060 [P] [US6] Finalizar `AuditLogger` em `src/utils/audit_logger.py` (JSON Lines append-only)
- [ ] T061 [US6] Implementar `AuditLogEntry` model em `src/models/schemas.py`
- [ ] T062 [US6] Criar rotação de logs diária em `src/utils/audit_logger.py`
- [ ] T063 [US6] Integrar AuditLogger em endpoints de análise em `src/api/routes/*.py` (acesso a dados)
- [ ] T064 [US6] Implementar exportação de logs em `src/utils/audit_logger.py` (JSON para ANPD)
- [ ] T065 [US6] Criar endpoint `/admin/audit/export` em `src/api/routes/admin.py` (admin only)
- [ ] T066 [US6] Garantir imutabilidade de logs (append-only, permissões read-only)

**Checkpoint**: US6 funcional - `cat logs/audit-2026-04-22.jsonl` mostra eventos estruturados

---

## Phase 9: User Story 7 - CORS Restritivo (Priority: P2)

**Goal**: CORS configurado com whitelist explícita, nunca `*` em produção

**Independent Test**: Requisições de origem não-permitida são bloqueadas; whitelist funciona

### Tests (TDD obrigatório)
- [ ] T067 [P] [US7] Teste de integração `test_cors_origins.py` - bloqueio de origens não-permitidas
- [ ] T068 [P] [US7] Teste de segurança `test_cors_production.py` - `*` nunca em produção

### Implementation
- [ ] T069 [P] [US7] Implementar `CORSValidation` em `src/core/security/middleware.py`
- [ ] T070 [US7] Configurar CORS em `src/api/main.py` (whitelist explícita)
- [ ] T071 [US7] Adicionar warning log se CORS `*` em não-local em `src/core/security/middleware.py`
- [ ] T072 [US7] Validar CORS em preflight requests em `src/core/security/middleware.py`
- [ ] T073 [US7] Testar múltiplas origens permitidas em `tests/security/test_cors.py`

**Checkpoint**: US7 funcional - `curl -H "Origin: https://evil.com" /health` retorna erro CORS

---

## Phase 10: Polish & Cross-Cutting Concerns

**Purpose**: Testes de segurança automatizados, documentação e validação

### Security Scanning
- [ ] T074 [P] Configurar Bandit em `pyproject.toml` (SAST Python)
- [ ] T075 [P] Configurar Safety em CI/CD (`poetry run safety check`)
- [ ] T076 [P] Rodar Bandit e corrigir findings em `src/` (exceto false positives)
- [ ] T077 Rodar Safety e atualizar dependências vulneráveis

### Test Coverage
- [ ] T078 [P] Testes de segurança em `tests/security/` (cobertura >70% em módulos de segurança)
- [ ] T079 Testes de carga para rate limiting em `tests/load/test_rate_limit.py`

### Documentation
- [ ] T080 Atualizar `README.md` com seção "Segurança" (setup de API Key, rate limits)
- [ ] T081 Atualizar `CLAUDE.md` se necessário (novas dependências de segurança)
- [ ] T082 Validar `quickstart.md` - seguir passo a passo deve funcionar

### Final Validation
- [ ] T083 Rodar `ruff check .` - zero erros
- [ ] T084 Rodar `mypy src/core/security/` - zero erros
- [ ] T085 Rodar `pytest tests/security/ -v` - 100% passando
- [ ] T086 Verificar cobertura `pytest --cov=src/core/security --cov-report=term` - >70%
- [ ] T087 Executar auditoria `@speckit.clarify` - documentar discrepâncias

### Docker
- [ ] T088 Atualizar `Dockerfile` com `libmagic1` para python-magic
- [ ] T089 Validar build Docker com `docker-compose up --build`

**Checkpoint**: Todos os SCs atingidos, testes passando, documentação atualizada

---

## Dependencies & Execution Order

### Phase Dependencies

```
Phase 1 (Setup)
    ↓
Phase 2 (Foundational)  ←  Bloqueia TODAS as User Stories
    ↓
Phase 3 (US1) ────┐
Phase 4 (US2) ────┤
Phase 5 (US3) ────┤  ←  Podem rodar em PARALELO
Phase 6 (US4) ────┤
Phase 7 (US5) ────┤
Phase 8 (US6) ────┤
Phase 9 (US7) ────┘
    ↓
Phase 10 (Polish)
```

### User Story Dependencies

- **US1 (Auth)**: Sem dependências de outras stories
- **US2 (Uploads)**: Sem dependências (exceto Foundational)
- **US3 (Sanitização)**: Sem dependências (usa LogSanitizer da Fase 2)
- **US4 (Rate Limiting)**: Sem dependências
- **US5 (Headers)**: Sem dependências
- **US6 (Auditoria)**: Usa AuditLogger da Fase 2
- **US7 (CORS)**: Sem dependências

**Todas as US podem rodar em paralelo após Phase 2 completa!**

### Parallel Opportunities

**Fase 2 (Foundational)**:
```bash
# T005, T006, T007, T008, T009, T010 podem rodar em paralelo
```

**User Stories (após Fase 2)**:
```bash
# Com múltiplos desenvolvedores:
Dev A: Phase 3 (US1 - Auth)
Dev B: Phase 4 (US2 - Uploads)
Dev C: Phase 5 (US3 - Sanitização)
Dev D: Phase 6 (US4 - Rate Limiting)
# etc.
```

**Tests dentro de cada US**:
```bash
# T011, T012, T013 (US1 tests) podem rodar em paralelo
# T020, T021, T022 (US2 tests) podem rodar em paralelo
```

---

## Implementation Strategy

### MVP First (User Stories P1)

1. ✅ Complete Phase 1: Setup
2. ✅ Complete Phase 2: Foundational (CRÍTICO - bloqueia tudo)
3. ✅ Complete Phase 3: User Story 1 (Auth) - **MVP CORE**
4. ✅ Complete Phase 4: User Story 2 (Uploads)
5. ✅ Complete Phase 5: User Story 3 (Sanitização)
6. ✅ Complete Phase 6: User Story 4 (Rate Limiting)
7. **STOP e VALIDAR**: Testar US1-4 independentemente
8. Deploy/demo - Sistema já está SEGURO para MVP

### Full Feature (Adicionar P2)

9. Complete Phase 7: User Story 5 (Headers)
10. Complete Phase 8: User Story 6 (Auditoria)
11. Complete Phase 9: User Story 7 (CORS)
12. Complete Phase 10: Polish & Scanning
13. Auditoria `@speckit.clarify` e correções

### Parallel Team Strategy

Com 4 desenvolvedores:

**Semana 1**:
- Todos: Phase 1 + Phase 2 (foundational)

**Semana 2-3** (paralelo):
- Dev A: US1 (Auth) + US5 (Headers)
- Dev B: US2 (Uploads) + US6 (Auditoria)
- Dev C: US3 (Sanitização) + US7 (CORS)
- Dev D: US4 (Rate Limiting) + Phase 10 (Polish)

**Semana 4**:
- Todos: Integração, testes finais, auditoria

---

## Success Criteria Coverage

| SC | Tasks que cobrem |
|----|------------------|
| SC-001 (Zero vulns) | T074, T075, T076, T077 (Bandit + Safety) |
| SC-002 (Auth 100%) | T011-T019 (US1 completa) |
| SC-003 (Rate limit) | T038-T047 (US4 completa) |
| SC-004 (Headers 100%) | T048-T056 (US5 completa) |
| SC-005 (Secrets nunca) | T029-T037, T086 (US3 + grep verification) |
| SC-006 (BOLA protegido) | T013, T017 (BOLA tests + implementation) |
| SC-007 (Latência <10ms) | Performance test em T079 |
| SC-008 (LGPD logs) | T057-T066 (US6 completa) |

---

## Notes

- **[P]** tasks = arquivos diferentes, sem dependências
- Cada User Story é independentemente testável (conforme spec)
- Tests primeiro (TDD) para garantir comportamento correto
- Security scanning (T074-T077) deve ser executado antes do merge
- `@speckit.clarify` ao final para validar contra spec e constitution
- Total: **87 tasks** organizadas em 10 fases
