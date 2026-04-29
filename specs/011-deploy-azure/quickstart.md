# Quickstart: Deploy Azure

Guia rápido para fazer deploy da API no Azure App Service (Free Tier F1).

## Pré-requisitos

- Conta Azure (Free Tier disponível em [azure.microsoft.com/free](https://azure.microsoft.com/free))
- Azure CLI instalado: `curl -sL https://aka.ms/InstallAzureCLIDeb | sudo bash`
- Repositório clonado e Docker funcionando localmente

## Setup Inicial (Executar uma vez)

### 1. Login Azure

```bash
az login
# Selecione a subscription correta se tiver múltiplas
az account set --subscription "Sua Subscription"
```

### 2. Criar Resource Group

```bash
az group create \
  --name rg-tech-challenge-fase4 \
  --location brazilsouth
```

### 3. Criar App Service Plan (Free Tier)

```bash
az appservice plan create \
  --name plan-tech-challenge \
  --resource-group rg-tech-challenge-fase4 \
  --sku F1 \
  --is-linux
```

### 4. Criar Web App

```bash
az webapp create \
  --name tech-challenge-api-grupo-27 \
  --plan plan-tech-challenge \
  --resource-group rg-tech-challenge-fase4 \
  --deployment-container-image-name ghcr.io/vagnerbarbosa/tech-challenge-fase4:latest
```

### 5. Configurar Variáveis de Ambiente

```bash
# Azure Keys
az webapp config appsettings set \
  --name tech-challenge-api-grupo-27 \
  --resource-group rg-tech-challenge-fase4 \
  --settings AZURE_TEXT_KEY="sua-key-aqui"

az webapp config appsettings set \
  --name tech-challenge-api-grupo-27 \
  --resource-group rg-tech-challenge-fase4 \
  --settings AZURE_SPEECH_KEY="sua-key-aqui"

az webapp config appsettings set \
  --name tech-challenge-api-grupo-27 \
  --resource-group rg-tech-challenge-fase4 \
  --settings AZURE_VISION_KEY="sua-key-aqui"

# Security Keys
az webapp config appsettings set \
  --name tech-challenge-api-grupo-27 \
  --resource-group rg-tech-challenge-fase4 \
  --settings SECURITY_API_KEY="sua-api-key-segura"

az webapp config appsettings set \
  --name tech-challenge-api-grupo-27 \
  --resource-group rg-tech-challenge-fase4 \
  --settings SECURITY_ADMIN_KEY="sua-admin-key-segura"

# Configurações
az webapp config appsettings set \
  --name tech-challenge-api-grupo-27 \
  --resource-group rg-tech-challenge-fase4 \
  --settings ENVIRONMENT="production" LOG_LEVEL="INFO"
```

### 6. Configurar Porta e Startup

```bash
az webapp config set \
  --name tech-challenge-api-grupo-27 \
  --resource-group rg-tech-challenge-fase4 \
  --startup-file "uvicorn src.api.main:app --host 0.0.0.0 --port 8000"

az webapp config appsettings set \
  --name tech-challenge-api-grupo-27 \
  --resource-group rg-tech-challenge-fase4 \
  --settings WEBSITES_PORT=8000
```

### 7. Configurar Azure Files (SQLite)

```bash
az webapp config appsettings set \
  --name tech-challenge-api-grupo-27 \
  --resource-group rg-tech-challenge-fase4 \
  --settings DATABASE_URL="sqlite:///home/site/data/app.db"
```

### 8. Habilitar HTTPS

```bash
az webapp update \
  --name tech-challenge-api-grupo-27 \
  --resource-group rg-tech-challenge-fase4 \
  --https-only true
```

### 9. Configurar GitHub Secrets (para CI/CD)

No GitHub, vá em Settings > Secrets and variables > Actions, e adicione:

```
AZURE_CREDENTIALS={
  "clientId": "...",
  "clientSecret": "...",
  "subscriptionId": "...",
  "tenantId": "..."
}
```

Para obter as credenciais:

```bash
az ad sp create-for-rbac \
  --name "github-actions-tech-challenge" \
  --role contributor \
  --scopes /subscriptions/{subscription-id}/resourceGroups/rg-tech-challenge-fase4 \
  --sdk-auth
```

## Deploy Automático (CI/CD)

Após o setup inicial, cada push na branch `main` dispara deploy automático:

```bash
git add .
git commit -m "feat: minha nova feature"
git push origin main
```

O workflow faz:
1. Roda testes (pytest)
2. Build e push da imagem Docker para ghcr.io
3. Deploy para Azure App Service
4. Health check
5. Rollback automático se falhar

## Deploy Manual

Se precisar fazer deploy manualmente:

```bash
# Usar o script
./scripts/deploy-azure.sh

# Ou com tag específica
./scripts/deploy-azure.sh v1.0.0
```

## Verificar Deploy

```bash
# Health check
curl https://tech-challenge-api-grupo-27.azurewebsites.net/health

# Swagger
curl https://tech-challenge-api-grupo-27.azurewebsites.net/docs
```

## Logs

```bash
# Ver logs em tempo real
az webapp log tail \
  --name tech-challenge-api-grupo-27 \
  --resource-group rg-tech-challenge-fase4

# Ou no portal Azure: App Service > Monitoring > Log stream
```

## Troubleshooting

### App não inicia
```bash
az webapp log tail --name tech-challenge-api-grupo-27 --resource-group rg-tech-challenge-fase4
```

### Health check falha
```bash
# Verificar variáveis de ambiente
az webapp config appsettings list \
  --name tech-challenge-api-grupo-27 \
  --resource-group rg-tech-challenge-fase4
```

### Reiniciar app
```bash
az webapp restart --name tech-challenge-api-grupo-27 --resource-group rg-tech-challenge-fase4
```

## Limpar Recursos (Se necessário)

```bash
# Deletar App Service
az webapp delete --name tech-challenge-api-grupo-27 --resource-group rg-tech-challenge-fase4 --yes

# Deletar App Service Plan
az appservice plan delete --name plan-tech-challenge --resource-group rg-tech-challenge-fase4 --yes

# Deletar Resource Group (CUIDADO: apaga tudo!)
az group delete --name rg-tech-challenge-fase4 --yes --no-wait
```

## Recursos

- [Azure CLI Reference](https://docs.microsoft.com/cli/azure/)
- [App Service Documentation](https://docs.microsoft.com/azure/app-service/)
- [GitHub Actions Azure](https://docs.github.com/actions/deployment/deploying-to-azure)
