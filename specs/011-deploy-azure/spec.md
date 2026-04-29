# Feature Specification: Deploy Azure

**Feature Branch**: `[009-deploy-azure]`
**Created**: 2026-04-11
**Status**: Draft
**Input**: User description: "Realizar deploy da aplicação em Azure App Service (Free Tier)"

---

## Clarifications

### Session 2026-04-29
- **Q**: Qual container registry será usado para as imagens Docker?  
  **A**: GitHub Container Registry (ghcr.io) - gratuito para repositórios públicos, integração nativa com GitHub Actions
- **Q**: Qual estratégia de rollback será implementada?  
  **A**: GitHub Actions rollback - Pipeline reverte para última imagem estável se health check falhar após deploy
- **Q**: Qual banco de dados será usado em produção?  
  **A**: SQLite com Azure Files - mantém compatibilidade com arquitetura atual e funciona no Free Tier F1 sem custos adicionais
- **Q**: Qual será a URL do App Service?  
  **A**: Usar URL do Azure padrão: `tech-challenge-api-grupo-27.azurewebsites.net` (nome customizado para identificação do grupo)
- **Q**: Qual nível de integração com Azure Monitor será implementado?  
  **A**: App Service Logs padrão - logs do console/container acessíveis via Azure Portal, sem custo adicional no Free Tier

---

## User Scenarios & Testing

### User Story 1 - Deploy App Service (Priority: P1)

Como desenvolvedor, quero fazer deploy da API em Azure App Service para produção.

**Why this priority**: Deploy em produção Azure é obrigatório conforme brief oficial.

**Independent Test**: Aplicação acessível via URL pública do Azure.

**Acceptance Scenarios**:

1. **Given** código pronto, **When** faço deploy, **Then** aplicação está no ar em Azure
2. **Given** App Service configurado, **When** acesso URL, **Then** health check responde 200
3. **Given** variáveis de ambiente, **When** configuradas no Azure, **Then** aplicação as lê corretamente

### User Story 2 - CI/CD Pipeline (Priority: P2)

Como desenvolvedor, quero pipeline automatizada para deploy contínuo.

**Why this priority**: Automação reduz erros manuais e acelera entregas.

**Independent Test**: Push na branch main dispara deploy automático.

**Acceptance Scenarios**:

1. **Given** push na branch main, **When** pipeline executa, **Then** roda testes
2. **Given** testes passando, **When** build completa, **Then** deploy automático inicia
3. **Given** falha nos testes, **When** detectada, **Then** deploy é bloqueado

### User Story 3 - Configuração de Produção (Priority: P1)

Como operador, quero configurações otimizadas para ambiente de produção.

**Why this priority**: Configurações de dev não são adequadas para produção.

**Independent Test**: Aplicação roda estável em produção.

**Acceptance Scenarios**:

1. **Given** ambiente production, **When** inicio, **Then** logs estruturados ativados
2. **Given** ambiente production, **When** erro ocorre, **Then** não expõe stack traces
3. **Given** ambiente production, **When** health check, **Then** não loga spam

---

## Requirements

### Functional Requirements

- **FR-001**: Deploy em Azure App Service (Free Tier F1)
- **FR-002**: Container Docker funcionando no Azure
- **FR-003**: Variáveis de ambiente configuradas no Azure Portal
- **FR-004**: HTTPS obrigatório
- **FR-005**: Health check configurado no Azure
- **FR-006**: Logs no Azure App Service Logs (padrão do Free Tier)
- **FR-007**: CI/CD com GitHub Actions (opcional)
- **FR-008**: Rollback automático via GitHub Actions se health check falhar após deploy

### Key Entities

- **Azure App Service**: Plataforma de hospedagem
- **Azure Container Registry**: Registro de imagens Docker
- **GitHub Actions**: CI/CD pipeline
- **Azure Monitor**: Logs e métricas

---

## Success Criteria

- **SC-001**: Aplicação acessível via HTTPS pública
- **SC-002**: Swagger disponível em /docs
- **SC-003**: Health check retorna healthy
- **SC-004**: Testes de integração passam contra produção
- **SC-005**: Uptime > 99%

---

## Assumptions

- Conta Azure Free Tier disponível
- Azure CLI instalado localmente
- GitHub Actions disponível (repositório público)
- Docker build funciona localmente

---

## Technical Notes

### Azure App Service Plan
- Tier: Free (F1) - 1GB RAM, 1 CPU core
- SKU: B1 (se precisar de custom domain)
- Runtime: Container (Docker)

### Configurações Necessárias
```bash
# Criar Resource Group
az group create --name rg-tech-challenge --location brazilsouth

# Criar App Service Plan (Free Tier)
az appservice plan create \
  --name plan-tech-challenge \
  --resource-group rg-tech-challenge \
  --sku F1 \
  --is-linux

# Criar Web App
az webapp create \
  --name tech-challenge-api-grupo-27 \
  --plan plan-tech-challenge \
  --resource-group rg-tech-challenge \
  --deployment-container-image-name ghcr.io/vagnerbarbosa/tech-challenge-fase4:latest
```

### Environment Variables no Azure
- AZURE_TEXT_KEY
- AZURE_SPEECH_KEY
- AZURE_VISION_KEY
- SECURITY_API_KEY
- SECURITY_ADMIN_KEY
- DATABASE_URL=sqlite:///app/data/app.db
- LOG_LEVEL=INFO
- ENVIRONMENT=production
