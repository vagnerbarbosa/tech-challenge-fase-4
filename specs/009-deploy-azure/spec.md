# Feature Specification: Deploy Azure

**Feature Branch**: `[009-deploy-azure]`  
**Created**: 2026-04-11  
**Updated**: 2026-05-01  
**Status**: ✅ COMPLETED  
**Input**: User description: "Realizar deploy da aplicação em Azure"

---

## Clarifications

### Session 2026-04-29
- **Q**: Qual container registry será usado para as imagens Docker?  
  **A**: GitHub Container Registry (ghcr.io) - gratuito para repositórios públicos, integração nativa com GitHub Actions
- **Q**: Qual estratégia de rollback será implementada?  
  **A**: GitHub Actions health check - Pipeline falha se health check não passar, necessitando novo deploy
- **Q**: Qual banco de dados será usado em produção?  
  **A**: SQLite em disco temporário (/tmp) - adequado para Azure Container Instances (ACI)
- **Q**: Qual será a URL do serviço?  
  **A**: IP público atribuído dinamicamente pelo Azure Container Instances: `http://<your-azure-ip>:8000` (substitua pelo IP real após deploy)
- **Q**: Qual nível de integração com Azure Monitor será implementado?  
  **A**: Logs via Azure CLI `az container logs` e health check no workflow

### Session 2026-05-01 (Decisões de Arquitetura)
- **Q**: Por que Azure Container Instances em vez de App Service?  
  **A**: App Service apresentou problemas de persistência de configuração (linuxFxVersion). ACI é mais previsível para containers Docker customizados.
- **Q**: Como lidar com serviços Azure AI soft-deleted?  
  **A**: Workflow verifica se serviço existe antes de tentar recriar; purga soft-deleted se necessário

---

## User Scenarios & Testing

### User Story 1 - Deploy Azure Container Instances (Priority: P1) ✅ COMPLETED

Como desenvolvedor, quero fazer deploy da API em Azure Container Instances para produção.

**Why this priority**: Deploy em produção Azure é obrigatório conforme brief oficial.

**Independent Test**: Aplicação acessível via IP público do Azure.

**Acceptance Scenarios**:

1. **Given** código pronto, **When** faço deploy, **Then** aplicação está no ar em Azure ✅
2. **Given** Container Instance configurado, **When** acesso IP, **Then** health check responde 200 ✅
3. **Given** variáveis de ambiente, **When** configuradas no Azure, **Then** aplicação as lê corretamente ✅

### User Story 2 - CI/CD Pipeline (Priority: P2) ✅ COMPLETED

Como desenvolvedor, quero pipeline automatizada para deploy contínuo.

**Why this priority**: Automação reduz erros manuais e acelera entregas.

**Independent Test**: Push na branch main dispara deploy automático.

**Acceptance Scenarios**:

1. **Given** push na branch main, **When** pipeline executa, **Then** roda build e deploy ✅
2. **Given** build completo, **When** deploy inicia, **Then** container é recriado com nova imagem ✅
3. **Given** deploy concluído, **When** health check executa, **Then** valida que API responde 200 ✅

### User Story 3 - Configuração de Produção (Priority: P1) ✅ COMPLETED

Como operador, quero configurações otimizadas para ambiente de produção.

**Why this priority**: Configurações de dev não são adequadas para produção.

**Independent Test**: Aplicação roda estável em produção.

**Acceptance Scenarios**:

1. **Given** ambiente production, **When** inicio, **Then** logs estruturados ativados ✅
2. **Given** ambiente production, **When** erro ocorre, **Then** não expõe stack traces ✅
3. **Given** ambiente production, **When** health check, **Then** não loga spam ✅

---

## Requirements

### Functional Requirements ✅ ALL COMPLETED

- **FR-001**: Deploy em Azure Container Instances ✅
- **FR-002**: Container Docker funcionando no Azure ✅
- **FR-003**: Variáveis de ambiente configuradas via CI/CD ✅
- **FR-004**: IP público acessível ✅
- **FR-005**: Health check configurado no workflow ✅
- **FR-006**: Logs via Azure CLI ✅
- **FR-007**: CI/CD com GitHub Actions ✅
- **FR-008**: Health check validation após deploy ✅

### Key Entities

- **Azure Container Instances (ACI)**: Plataforma de hospedagem de containers
- **Azure AI Services**: Serviços cognitivos (Text, Speech, Vision)
- **GitHub Container Registry**: Registro de imagens Docker (ghcr.io)
- **GitHub Actions**: CI/CD pipeline
- **Azure CLI**: Gerenciamento de recursos

---

## Success Criteria ✅ ALL ACHIEVED

- **SC-001**: Aplicação acessível via IP público ✅
  - URL: `http://<your-azure-ip>:8000`
- **SC-002**: Swagger disponível em /docs ✅
  - `http://<your-azure-ip>:8000/docs`
- **SC-003**: Health check retorna healthy ✅
  - Response: `{"status": "healthy", ...}`
- **SC-004**: Azure AI Services integrados ✅
  - Text, Speech e Vision criados e funcionando
- **SC-005**: Uptime > 99% ⏳ (Monitorado pelo Azure)

---

## Implementation Summary

### Arquitetura Final

```
┌─────────────────────────────────────────────────────────────┐
│                      GitHub                                 │
│  ┌──────────────────────────────────────────────────────┐  │
│  │  GitHub Actions (deploy-azure.yml)                    │  │
│  │  • Build Docker image                                 │  │
│  │  • Push to ghcr.io                                    │  │
│  │  • Deploy to Azure Container Instances                │  │
│  └──────────────────────────────────────────────────────┘  │
└─────────────────────────┬───────────────────────────────────┘
                          │
                          ▼
┌─────────────────────────────────────────────────────────────┐
│                  Azure Cloud                                │
│  ┌─────────────────────────────────────────────────────┐   │
│  │  Resource Group: rg-tech-challenge-fase4            │   │
│  │                                                     │   │
│  │  ┌──────────────────────────────────────────────┐   │   │
│  │  │  Azure Container Instances                  │   │   │
│  │  │  • tech-challenge-api (image: ghcr.io/...)   │   │   │
│  │  │  • IP: <DEPLOY_IP>:8000                  │   │   │
│  │  └──────────────────────────────────────────────┘   │   │
│  │                                                     │   │
│  │  ┌──────────────────────────────────────────────┐   │   │
│  │  │  Azure AI Services                          │   │   │
│  │  │  • tech-challenge-text (TextAnalytics)      │   │   │
│  │  │  • tech-challenge-speech (SpeechServices) │   │   │
│  │  │  • tech-challenge-vision (ComputerVision)   │   │   │
│  │  └──────────────────────────────────────────────┘   │   │
│  └─────────────────────────────────────────────────────┘   │
└─────────────────────────────────────────────────────────────┘
```

### Files Created/Modified

**CI/CD Pipeline:**
- `.github/workflows/deploy-azure.yml` - Workflow completo de deploy
- `.github/workflows/ci.yml` - Workflow de testes para PRs

**Scripts:**
- `scripts/check-azure.sh` - Diagnóstico e gerenciamento local

**Docker:**
- `Dockerfile` - Multi-stage build otimizado
- `entrypoint.sh` - Script de inicialização (opcional, pode ser bypassed)

**Documentation:**
- `docs/environment.json` - Configurações Postman/Insomnia
- `docs/collection.json` - Collection atualizada com URL de produção

---

## Technical Notes

### Azure Container Instances Configuration

**Specs:**
- CPU: 1 core
- Memory: 2 GB
- OS: Linux
- Port: 8000 (public)
- Restart Policy: OnFailure

**Environment Variables:**
```
ENVIRONMENT=production
LOG_LEVEL=INFO
AZURE_TEXT_ENDPOINT=<auto-configured>
AZURE_TEXT_KEY=<auto-configured>
AZURE_SPEECH_KEY=<auto-configured>
AZURE_SPEECH_REGION=brazilsouth
AZURE_VISION_ENDPOINT=<auto-configured>
AZURE_VISION_KEY=<auto-configured>
DATABASE_URL=sqlite:///tmp/app.db
REDIS_ENABLED=false
SECURITY_API_KEY=<from secrets>
SECURITY_ADMIN_KEY=<from secrets>
SECRET_KEY=<from secrets>
```

### CI/CD Pipeline Steps

1. **Check Image**: Verifica se imagem com hash já existe (cache)
2. **Build**: Docker multi-stage build com cache
3. **Push**: Envia para ghcr.io
4. **Create Resources**: Resource Group e AI Services (se necessário)
5. **Deploy Container**: Cria/Atualiza Container Instance
6. **Health Check**: Valida que API responde em /health

### Known Issues & Workarounds

| Issue | Solution |
|-------|----------|
| AI Services soft-deleted | Workflow purga antes de recriar |
| PublicNetworkAccess required | Usar `az resource create` com propriedades JSON |
| SECRET_KEY validation | Adicionar ao workflow de deploy |
| Container crash em startup | Verificar todas as env vars obrigatórias |

---

## Scripts Úteis

```bash
# Verificar status do deploy
./scripts/check-azure.sh check

# Ver logs do container
./scripts/check-azure.sh logs

# Status detalhado
./scripts/check-azure.sh status

# Deploy manual (se necessário)
./scripts/check-azure.sh deploy

# Limpar todos os recursos
./scripts/check-azure.sh delete
```

---

## URLs de Acesso

| Endpoint | URL |
|----------|-----|
| API Base | `http://<your-azure-ip>:8000` |
| Health | `http://<your-azure-ip>:8000/health` |
| Swagger | `http://<your-azure-ip>:8000/docs` |
| ReDoc | `http://<your-azure-ip>:8000/redoc` |

> **Nota**: Substitua `<your-azure-ip>` pelo IP público atribuído pelo Azure Container Instances após o deploy.

---

## Changelog

### 2026-05-01 - Deploy Concluído
- ✅ Azure Container Instances configurado
- ✅ CI/CD pipeline funcionando
- ✅ Health check passando
- ✅ Azure AI Services integrados
- ✅ Collection e environment atualizados

### 2026-04-29 - Planejamento Inicial
- Escolha de App Service como target
- Configuração de GitHub Actions
- Definição de secrets necessários
