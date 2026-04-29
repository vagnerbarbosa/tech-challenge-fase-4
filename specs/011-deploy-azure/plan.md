# Implementation Plan: Deploy Azure

**Branch**: `011-deploy-azure` | **Date**: 2026-04-29 | **Spec**: [spec.md](spec.md)
**Input**: Feature specification from `/specs/011-deploy-azure/spec.md`

## Summary

Deploy da API Multimodal Health Analysis em Azure App Service (Free Tier F1). Inclui configuração de infraestrutura Azure, container Docker, CI/CD pipeline com GitHub Actions, e configurações otimizadas para produção. Mantém compliance LGPD e OWASP em ambiente cloud.

## Technical Context

**Language/Version**: Python 3.11+  
**Primary Dependencies**: FastAPI, Docker, Azure CLI  
**Storage**: GitHub Container Registry (ghcr.io) para imagens Docker, SQLite com Azure Files para persistência  
**Testing**: pytest, GitHub Actions workflows  
**Target Platform**: Azure App Service (Linux Container)  
**Project Type**: web-service  
**Performance Goals**: Resposta < 2s para endpoints de análise  
**Constraints**: Azure Free Tier (F1: 1GB RAM, 1 CPU core), HTTPS obrigatório  
**Scale/Scope**: Single instance, até 5.000 requests/mês (Azure Free Tier limits)

## Constitution Check

*GATE: Must pass before Phase 0 research. Re-check after Phase 1 design.*

| Principle | Status | Notes |
|-----------|--------|-------|
| LGPD Compliance | ✅ PASS | Dados já anonimizados antes de chegar ao deploy |
| Azure Free Tier Protection | ✅ PASS | Configuração de quotas mantida |
| Test Coverage >70% | ✅ PASS | CI/CD incluirá testes obrigatórios |
| Container-First | ✅ PASS | Docker já configurado |
| Documentação em Português | ✅ PASS | README atualizado |
| Security-First | ✅ PASS | HTTPS obrigatório, secrets em env vars |
| Multimodal Architecture | ✅ PASS | API já implementada |

## Project Structure

### Documentation (this feature)

```text
specs/011-deploy-azure/
├── plan.md              # This file
├── research.md          # Phase 0 output
├── data-model.md        # N/A - deploy não altera modelos
├── quickstart.md        # Phase 1 output - guia de deploy
├── contracts/           # N/A
└── tasks.md             # Phase 2 output (speckit.tasks)
```

### Source Code (repository root)

```text
src/
├── api/
│   ├── routes/          # Endpoints da API (existentes)
│   ├── middleware/      # Middlewares de segurança
│   └── main.py          # Entry point
├── core/
│   └── config.py        # Configurações por ambiente
├── services/            # Lógica de negócio
└── utils/               # Utilitários

.github/
└── workflows/
    └── deploy-azure.yml  # CI/CD pipeline (NOVO)

infra/
├── azure/
│   ├── main.bicep        # IaC Azure (opcional)
│   └── parameters.json
└── docker/
    └── Dockerfile.prod   # Dockerfile otimizado para prod

scripts/
└── deploy-azure.sh       # Script de deploy manual
```

**Structure Decision**: Mantemos estrutura existente e adicionamos `.github/workflows/` para CI/CD e `infra/` para IaC (Infrastructure as Code).

## Phase 0: Research & Decisions

**Azure App Service Free Tier (F1)**:
- 1 GB RAM, 1 vCPU
- 5 GB storage
- Não suporta custom domains em F1 (requer B1+)
- HTTPS automaticamente habilitado
- Container Linux com Docker

**GitHub Actions vs Azure DevOps**:
- GitHub Actions escolhido (repositório já no GitHub)
- Native integration com Azure via `azure/login` action

**Container Registry**: GitHub Container Registry (ghcr.io) - gratuito para públicos
**Banco de Dados**: SQLite com Azure Files (persistência no Free Tier F1)
**Rollback**: GitHub Actions com health check - reverte se falhar
**URL**: tech-challenge-api-grupo-27.azurewebsites.net
**Logs**: App Service Logs padrão (sem custo adicional)

## Phase 1: Design

### Deploy Strategy

1. **Build**: Docker multi-stage build
2. **Push**: Imagem para ghcr.io
3. **Deploy**: Azure App Service atualiza via webhook

### CI/CD Pipeline

```yaml
on:
  push:
    branches: [main]

jobs:
  test:
    - Checkout
    - Setup Python
    - Run tests with coverage
    - Lint (ruff)
    - Type check (mypy)

  build:
    needs: test
    - Build Docker image
    - Push to ghcr.io

  deploy:
    needs: build
    - Azure login
    - Deploy to App Service
```

### Environment Variables

Variáveis sensíveis configuradas via Azure Portal (não no código):
- `AZURE_TEXT_KEY`
- `AZURE_SPEECH_KEY`
- `AZURE_VISION_KEY`
- `SECURITY_API_KEY`
- `SECURITY_ADMIN_KEY`
- `DATABASE_URL=sqlite:///app/data/app.db`
- `ENVIRONMENT=production`
- `LOG_LEVEL=INFO`

### Rollback Strategy

- **GitHub Actions health check**: Após deploy, workflow verifica se aplicação responde em `/health`
- **Rollback automático**: Se health check falhar, pipeline reverte para última imagem estável
- **Azure App Service**: Mantém últimas 10 versões de imagem como backup adicional

## Success Criteria Check

| SC | Como atingir |
|----|--------------|
| SC-001 (HTTPS público) | Azure App Service provê TLS automático |
| SC-002 (Swagger) | Endpoint /docs já implementado |
| SC-003 (Health check) | Endpoint /health já implementado |
| SC-004 (Testes em prod) | CI/CD roda testes antes de deploy |
| SC-005 (Uptime 99%) | Azure SLA para App Service |

## Implementation Strategy

### MVP (P1 Stories)

1. US1: Deploy App Service - Configurar Azure resources
2. US3: Configuração Produção - Otimizar para F1 tier

### Full Feature (Adicionar P2)

3. US2: CI/CD Pipeline - Automação completa

### Execution Order

1. Setup Azure resources (manual)
2. Criar workflow GitHub Actions
3. Testar deploy manual
4. Testar CI/CD automático
5. Documentar no quickstart.md

## Dependencies

- Azure CLI local para setup inicial
- Permissões no Azure subscription
- GitHub Secrets: `AZURE_CREDENTIALS`

## Complexity Tracking

N/A - Deploy não introduz complexidade arquitetural nova, apenas orquestração de recursos existentes.
