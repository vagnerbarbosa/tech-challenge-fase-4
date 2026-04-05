# Task 009: Deploy em Produção Azure (OBRIGATÓRIO)

## Objetivo

Realizar o deploy da API em produção na Azure utilizando apenas serviços do **Free Tier**, garantindo que o sistema esteja acessível publicamente para avaliação.

> **⚠️ CRÍTICO**: Este deploy é obrigatório para o escopo do Tech Challenge Fase 4.

## Critérios de Aceite

### CA1: Provisionamento de Recursos Azure
- [ ] Criar conta Azure (se não existir)
- [ ] Provisionar recursos no Free Tier:
  - [ ] **Azure App Service** (F1 tier - 60 min CPU/dia, 1GB RAM, 1GB storage)
  - [ ] **Azure Container Registry** (opcional, para armazenar imagem Docker)
  - [ ] **Azure Cognitive Services** (Text Analytics, Speech, Computer Vision)
  - [ ] Configurar variáveis de ambiente nos recursos Azure

### CA2: Containerização para Produção
- [ ] Imagem Docker otimizada para produção:
  - Multi-stage build
  - Non-root user
  - Tamanho mínimo
- [ ] `.dockerignore` configurado corretamente
- [ ] Health check no Dockerfile
- [ ] Testar localmente: `docker-compose up --build`

### CA3: Deploy Azure App Service
- [ ] Criar App Service Plan (F1 - Free Tier)
- [ ] Configurar deployment via:
  - Opção A: GitHub Actions (CI/CD)
  - Opção B: Azure CLI (`az webapp up`)
  - Opção C: Docker Hub + Azure Container Registry
- [ ] Configurar variáveis de ambiente no App Service:
  ```
  AZURE_TEXT_KEY
  AZURE_TEXT_ENDPOINT
  AZURE_SPEECH_KEY
  AZURE_SPEECH_REGION
  AZURE_VISION_KEY
  AZURE_VISION_ENDPOINT
  ```

### CA4: Validação do Deploy
- [ ] API acessível em URL pública (ex: `https://<app-name>.azurewebsites.net`)
- [ ] Endpoint `/health` respondendo corretamente
- [ ] Swagger em `/docs` acessível e funcional
- [ ] Testar endpoint `/analyze/text` em produção
- [ ] Verificar logs no Azure Portal

### CA5: Documentação do Deploy
- [ ] URL de produção documentada no README.md
- [ ] Instruções de deploy no `docs/deploy.md`:
  - Como criar recursos Azure
  - Como configurar variáveis de ambiente
  - Como fazer deploy
  - Como verificar se está funcionando
- [ ] Screenshot do App Service rodando no Azure Portal

## Azure Free Tier - Limites do App Service F1

| Recurso | Limite |
|---------|--------|
| CPU | 60 minutos/dia |
| Memória | 1 GB |
| Storage | 1 GB |
| Banda | 165 MB/dia (aproximadamente) |
| Custom domain | ❌ Não suportado |
| SSL | ✅ Gratuito |

## Comandos Úteis

```bash
# Login Azure
az login

# Criar resource group
az group create --name tech-challenge-rg --location brazilsouth

# Criar App Service Plan (Free Tier)
az appservice plan create \
  --name tech-challenge-plan \
  --resource-group tech-challenge-rg \
  --sku F1 \
  --location brazilsouth

# Criar Web App
az webapp create \
  --name tech-challenge-api \
  --resource-group tech-challenge-rg \
  --plan tech-challenge-plan \
  --runtime "PYTHON:3.11"

# Configurar variáveis de ambiente
az webapp config appsettings set \
  --name tech-challenge-api \
  --resource-group tech-challenge-rg \
  --settings AZURE_TEXT_KEY=xxx AZURE_SPEECH_KEY=xxx

# Deploy via zip (se não usar Docker)
az webapp deployment source config-zip \
  --resource-group tech-challenge-rg \
  --name tech-challenge-api \
  --src api.zip
```

## Docker Deploy

```bash
# Build imagem
docker build -t tech-challenge-api:latest .

# Tag para ACR (Azure Container Registry)
docker tag tech-challenge-api:latest <acr-name>.azurecr.io/tech-challenge-api:latest

# Push para ACR
az acr login --name <acr-name>
docker push <acr-name>.azurecr.io/tech-challenge-api:latest

# Configurar App Service para usar imagem
az webapp config container set \
  --name tech-challenge-api \
  --resource-group tech-challenge-rg \
  --docker-custom-image-name <acr-name>.azurecr.io/tech-challenge-api:latest \
  --docker-registry-server-url https://<acr-name>.azurecr.io
```

## GitHub Actions (CI/CD)

```yaml
# .github/workflows/deploy-azure.yml
name: Deploy to Azure

on:
  push:
    branches: [main]

jobs:
  deploy:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4

      - name: Azure Login
        uses: azure/login@v1
        with:
          creds: ${{ secrets.AZURE_CREDENTIALS }}

      - name: Deploy to Azure Web App
        uses: azure/webapps-deploy@v2
        with:
          app-name: tech-challenge-api
          slot-name: production
          publish-profile: ${{ secrets.AZURE_WEBAPP_PUBLISH_PROFILE }}
```

## Checklist Final de Deploy

- [ ] Recursos Azure criados no Free Tier
- [ ] API deployada e acessível publicamente
- [ ] Todas as variáveis de ambiente configuradas
- [ ] Endpoints testados em produção
- [ ] Documentação atualizada com URL de produção
- [ ] Screenshots/evidências do deploy

## Pontos de Atenção

1. **Cold Start**: App Service F1 tem cold start (demora ~10-30s para responder após período de inatividade)
2. **Quota CPU**: Monitorar uso de CPU (limite de 60 min/dia)
3. **Sleep**: App Service F1 "dorme" após período de inatividade (normal para free tier)
4. **Logs**: Verificar logs em "Monitoring > Log stream" no Azure Portal
5. **CORS**: Configurar CORS se necessário para acesso do frontend

## Recursos

- [Azure App Service Documentation](https://docs.microsoft.com/azure/app-service/)
- [Deploy Python to Azure App Service](https://docs.microsoft.com/azure/app-service/quickstart-python)
- [Azure Free Tier Limits](https://azure.microsoft.com/free/)
