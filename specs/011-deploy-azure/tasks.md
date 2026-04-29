# Tasks: Deploy Azure

**Input**: Design documents from `/specs/011-deploy-azure/`  
**Prerequisites**: plan.md, spec.md  
**Branch**: `011-deploy-azure`  
**Gerado em**: 2026-04-29

---

## Format: `[ID] [P?] [Story] Description`

- **[P]**: Pode rodar em paralelo (arquivos diferentes, sem dependências)
- **[Story]**: Qual user story (US1-3) - US1 e US3 são P1, US2 é P2

---

## Phase 1: Setup (Preparação de Ferramentas)

**Purpose**: Configuração de CLI e variáveis de ambiente locais

**Goal**: Azure CLI configurado e autenticado

- [ ] T001 Instalar Azure CLI localmente (se não instalado)
- [ ] T002 [P] Executar `az login` e verificar acesso à subscription
- [ ] T003 [P] Verificar permissões de criação de resources (Owner ou Contributor)
- [ ] T004 Configurar GitHub Secret `AZURE_CREDENTIALS` (se não existir)

**Checkpoint**: `az account show` retorna subscription válida

---

## Phase 2: Foundational (Infraestrutura Azure) ⚠️ CRÍTICO

**Purpose**: Recursos Azure base que TODAS as user stories precisam

**⚠️ CRITICAL**: Nenhuma user story pode começar até esta fase estar completa

### Resource Group e App Service Plan
- [ ] T005 Criar Resource Group `rg-tech-challenge-fase4` em `brazilsouth`
- [ ] T006 Criar App Service Plan `plan-tech-challenge` (SKU F1 - Free Tier)
- [ ] T007 Verificar quotas da subscription antes de criar

### Container Registry
- [ ] T008 [P] Verificar/criar GitHub Container Registry access
- [ ] T009 [P] Gerar GitHub PAT com permissões `write:packages` (se necessário)

### Configuração de Segredos
- [ ] T010 Criar GitHub Secret `AZURE_SUBSCRIPTION_ID`
- [ ] T011 [P] Criar GitHub Secret `AZURE_TENANT_ID`
- [ ] T012 [P] Criar GitHub Secret `AZURE_CLIENT_ID`
- [ ] T013 Criar GitHub Secret `AZURE_CLIENT_SECRET`

**Checkpoint**: Foundation pronta - User Stories podem começar

---

## Phase 3: User Story 1 - Deploy App Service (Priority: P1) 🎯 MVP

**Goal**: Aplicação rodando no Azure App Service

**Independent Test**: Acessar URL pública do Azure e receber health check 200

### Implementation
- [ ] T014 [P] Criar Web App `tech-challenge-api-grupo-27` no App Service Plan F1
- [ ] T015 [P] Configurar container image para `ghcr.io/vagnerbarbosa/tech-challenge-fase4:latest`
- [ ] T016 Configurar porta do container (8000) em `WEBSITES_PORT`
- [ ] T017 Configurar startup command: `uvicorn src.api.main:app --host 0.0.0.0 --port 8000`
- [ ] T018b Configurar Azure Files para persistência SQLite em `/app/data`
- [ ] T019 [P] Configurar variáveis de ambiente no Azure Portal:
  - `ENVIRONMENT=production`
  - `LOG_LEVEL=INFO`
- [ ] T020 Configurar `AZURE_TEXT_KEY` no Azure Portal (secret)
- [ ] T021 Configurar `AZURE_SPEECH_KEY` no Azure Portal (secret)
- [ ] T022 Configurar `AZURE_VISION_KEY` no Azure Portal (secret)
- [ ] T023 Configurar `SECURITY_API_KEY` no Azure Portal (secret)
- [ ] T024 Configurar `SECURITY_ADMIN_KEY` no Azure Portal (secret)
- [ ] T025 Configurar `DATABASE_URL` no Azure Portal
- [ ] T026 Habilitar HTTPS-only no App Service
- [ ] T027 Configurar health check no Azure (endpoint `/health`)

**Checkpoint**: US1 funcional - URL `tech-challenge-api-grupo-27.azurewebsites.net` retorna health check 200

---

## Phase 4: User Story 3 - Configuração de Produção (Priority: P1)

**Goal**: Configurações otimizadas para ambiente de produção

**Independent Test**: Aplicação não expõe stack traces em erros 500

### Implementation
- [ ] T028 [P] Atualizar `src/core/config.py` - detectar ambiente Azure
- [ ] T029 [P] Configurar logs estruturados para App Service Logs (não Azure Monitor)
- [ ] T030 Implementar error handling genérico para produção (não expõe stack)
- [ ] T031 [P] Desabilitar reload do uvicorn em produção
- [ ] T032 Configurar log level INFO para produção
- [ ] T033 Verificar que `/docs` está acessível via HTTPS
- [ ] T034 Testar endpoint de análise com API key válida

**Checkpoint**: US3 funcional - Erros não expõem detalhes internos

---

## Phase 5: User Story 2 - CI/CD Pipeline (Priority: P2)

**Goal**: Pipeline automatizado para deploy contínuo

**Independent Test**: Push na main dispara deploy automático

### Implementation
- [X] T035 [P] Criar workflow `.github/workflows/deploy-azure.yml`
- [ ] T036 [P] Configurar job de testes no workflow
- [ ] T037 [P] Configurar build e push Docker image para ghcr.io
- [ ] T038 Configurar job de deploy para Azure App Service
- [ ] T039 Implementar verificação de health check após deploy
- [ ] T040 Configurar rollback automático via GitHub Actions se health check falhar
- [X] T041 [P] Adicionar notificação de falha no workflow (via job rollback)
- [ ] T042 Testar pipeline completo com push na main (requer merge)

**Checkpoint**: US2 funcional - Push na main dispara deploy com rollback automático se health check falhar

---

## Phase 6: Polish & Cross-Cutting Concerns

**Purpose**: Documentação e validação final

- [X] T043 [P] Criar `quickstart.md` com passo a passo do deploy manual
- [ ] T044 [P] Atualizar `README.md` com seção Deploy Azure
- [ ] T045 [P] Documentar variáveis de ambiente necessárias no Azure
- [ ] T046 Validar quickstart.md seguindo passo a passo
- [ ] T047 Testar endpoint `/analyze/text` em produção
- [ ] T048 Testar endpoint `/analyze/audio` em produção
- [ ] T049 Testar endpoint `/analyze/video` em produção
- [ ] T050 Testar endpoint `/analyze/multimodal` em produção
- [ ] T051 [P] Verificar segurança: HTTPS forçado, secrets não expostos
- [ ] T052 Verificar LGPD compliance: logs sem dados sensíveis
- [ ] T053 Verificar rate limiting funcionando em produção
- [ ] T054 [P] Verificar App Service Logs funcionando no Azure Portal

**Checkpoint**: Todos os SCs atingidos, documentação atualizada, sistema em produção

---

## Dependencies & Execution Order

### Phase Dependencies

```
Phase 1 (Setup)
    ↓
Phase 2 (Foundational)  ←  Bloqueia TODAS as User Stories
    ↓
Phase 3 (US1) ────┐
Phase 4 (US3) ────┤  ←  Podem rodar em PARALELO
Phase 5 (US2) ────┘     (US2 pode vir depois)
    ↓
Phase 6 (Polish)
```

### User Story Dependencies

- **US1 (Deploy)**: Sem dependências de outras stories
- **US2 (CI/CD)**: Depende de US1 (precisa de App Service criado)
- **US3 (Config Produção)**: Sem dependências

### Parallel Opportunities

**Fase 2 (Foundational)**:
```bash
# T005, T006, T008, T009, T010, T011, T012, T013 podem rodar em paralelo
```

**User Stories (após Fase 2)**:
```bash
# Dev A: US1 (Deploy App Service)
# Dev B: US3 (Config Produção) - paralelo ao US1
# Dev C: US2 (CI/CD) - após US1 completo
```

---

## Implementation Strategy

### MVP First (User Stories P1)

1. ✅ Complete Phase 1: Setup
2. ✅ Complete Phase 2: Foundational (CRÍTICO - bloqueia tudo)
3. ✅ Complete Phase 3: User Story 1 (Deploy App Service)
4. ✅ Complete Phase 4: User Story 3 (Config Produção)
5. **STOP e VALIDAR**: Testar manualmente em produção
6. Deploy funcional - Sistema está NO AR!

### Full Feature (Adicionar P2)

7. Complete Phase 5: User Story 2 (CI/CD)
8. Complete Phase 6: Polish
9. Auditoria e documentação

### Execution Flow

**Semana 1**:
- Todos: Phase 1 + Phase 2 (infraestrutura base)
- Dev A: US1 (criar App Service)
- Dev B: US3 (config produção)

**Semana 2**:
- Dev A: US2 (CI/CD pipeline)
- Todos: Phase 6 (polish, docs, validação)

---

## Success Criteria Coverage

| SC | Tasks que cobrem |
|----|------------------|
| SC-001 (HTTPS público) | T026 (HTTPS-only) |
| SC-002 (Swagger) | T033 (/docs acessível) |
| SC-003 (Health check) | T027 (config health), T047-050 (testes) |
| SC-004 (Testes em prod) | T047-050 (testes endpoints) |
| SC-005 (Uptime 99%) | Depende de Azure SLA |

---

## Notes

- **[P]** tasks = arquivos diferentes, sem dependências
- Cada User Story é independentemente testável (conforme spec)
- US1 e US3 podem rodar em paralelo após Fase 2
- US2 (CI/CD) depende de US1 ter criado o App Service
- Testes manuais em produção são necessários (T047-T050)
- **Novo**: Task T018b configura Azure Files para SQLite
- **Novo**: Task T040 implementa rollback via GitHub Actions
- **Novo**: Task T054 verifica App Service Logs
- Total: **54 tasks** organizadas em 6 fases
