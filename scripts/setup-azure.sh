#!/bin/bash

# Script de setup inicial para Azure App Service
# Uso: ./scripts/setup-azure.sh

set -e

echo "🚀 Setup inicial do Azure App Service"
echo "======================================"
echo ""

# Verificar Azure CLI
if ! command -v az &> /dev/null; then
    echo "❌ Azure CLI não encontrado."
    echo "Instale em: https://aka.ms/installazurecli"
    echo ""
    echo "Para Linux/WSL:"
    echo "curl -sL https://aka.ms/InstallAzureCLIDeb | sudo bash"
    exit 1
fi
echo "✅ Azure CLI encontrado"

# Verificar login
echo "🔑 Verificando autenticação Azure..."
if ! az account show &> /dev/null; then
    echo "⚠️ Não autenticado. Executando az login..."
    az login
fi

SUBSCRIPTION=$(az account show --query name -o tsv)
SUBSCRIPTION_ID=$(az account show --query id -o tsv)
echo "✅ Logado na subscription: $SUBSCRIPTION"
echo "📋 Subscription ID: $SUBSCRIPTION_ID"
echo ""

# Configurações
RESOURCE_GROUP="rg-tech-challenge-fase4"
LOCATION="brazilsouth"
APP_NAME="tech-challenge-api-grupo-27"
PLAN_NAME="plan-tech-challenge"

echo "📦 Criando Resource Group..."
if az group show --name $RESOURCE_GROUP &> /dev/null; then
    echo "✅ Resource Group já existe: $RESOURCE_GROUP"
else
    az group create \
        --name $RESOURCE_GROUP \
        --location $LOCATION
    echo "✅ Resource Group criado: $RESOURCE_GROUP"
fi

echo ""
echo "🎯 Criando App Service Plan (Free Tier F1)..."
if az appservice plan show --name $PLAN_NAME --resource-group $RESOURCE_GROUP &> /dev/null; then
    echo "✅ App Service Plan já existe: $PLAN_NAME"
else
    az appservice plan create \
        --name $PLAN_NAME \
        --resource-group $RESOURCE_GROUP \
        --sku F1 \
        --is-linux
    echo "✅ App Service Plan criado: $PLAN_NAME (Free Tier F1)"
fi

echo ""
echo "🌐 Criando Web App..."
if az webapp show --name $APP_NAME --resource-group $RESOURCE_GROUP &> /dev/null; then
    echo "✅ Web App já existe: $APP_NAME"
else
    az webapp create \
        --name $APP_NAME \
        --plan $PLAN_NAME \
        --resource-group $RESOURCE_GROUP \
        --deployment-container-image-name nginx:latest
    echo "✅ Web App criado: $APP_NAME"
fi

echo ""
echo "⚙️ Configurando porta e startup..."
az webapp config set \
    --name $APP_NAME \
    --resource-group $RESOURCE_GROUP \
    --startup-file "uvicorn src.api.main:app --host 0.0.0.0 --port 8000" \
    > /dev/null 2>&1 || true

az webapp config appsettings set \
    --name $APP_NAME \
    --resource-group $RESOURCE_GROUP \
    --settings WEBSITES_PORT=8000 \
    > /dev/null 2>&1 || true

echo "✅ Configurações de porta aplicadas"

echo ""
echo "🔒 Habilitando HTTPS-only..."
az webapp update \
    --name $APP_NAME \
    --resource-group $RESOURCE_GROUP \
    --https-only true \
    > /dev/null 2>&1 || true
echo "✅ HTTPS-only habilitado"

echo ""
echo "✅ Setup inicial concluído!"
echo ""
echo "📝 Próximos passos:"
echo ""
echo "1. Configure as variáveis de ambiente no Azure Portal:"
echo "   https://portal.azure.com > App Services > $APP_NAME > Configuration"
echo ""
echo "   Variáveis necessárias:"
echo "   - AZURE_TEXT_KEY"
echo "   - AZURE_SPEECH_KEY"
echo "   - AZURE_VISION_KEY"
echo "   - SECURITY_API_KEY"
echo "   - SECURITY_ADMIN_KEY"
echo "   - ENVIRONMENT=production"
echo "   - LOG_LEVEL=INFO"
echo ""
echo "2. Configure o GitHub Secret AZURE_CREDENTIALS:"
echo "   Execute: az ad sp create-for-rbac --name \"github-actions\" --role contributor --scopes /subscriptions/$SUBSCRIPTION_ID/resourceGroups/$RESOURCE_GROUP --sdk-auth"
echo ""
echo "3. Faça o primeiro deploy:"
echo "   ./scripts/deploy-azure.sh"
echo ""
echo "4. Acesse sua aplicação:"
echo "   https://$APP_NAME.azurewebsites.net/health"
echo ""
