#!/bin/bash

# Script de deploy manual para Azure App Service
# Uso: ./scripts/deploy-azure.sh [tag]

set -e

# Configurações
APP_NAME="tech-challenge-api-grupo-27"
RESOURCE_GROUP="rg-tech-challenge-fase4"
REGISTRY="ghcr.io"
IMAGE_NAME="vagnerbarbosa/tech-challenge-fase4"

# Verificar argumentos
TAG=${1:-latest}

echo "🚀 Iniciando deploy manual para Azure App Service"
echo "================================================"
echo "App: $APP_NAME"
echo "Resource Group: $RESOURCE_GROUP"
echo "Image: $REGISTRY/$IMAGE_NAME:$TAG"
echo ""

# Verificar Azure CLI
if ! command -v az &> /dev/null; then
    echo "❌ Azure CLI não encontrado. Instale: https://aka.ms/installazurecli"
    exit 1
fi

# Verificar login Azure
echo "🔑 Verificando login Azure..."
if ! az account show &> /dev/null; then
    echo "⚠️ Não autenticado no Azure. Executando az login..."
    az login
fi

SUBSCRIPTION=$(az account show --query name -o tsv)
echo "✅ Logado na subscription: $SUBSCRIPTION"

# Verificar se Resource Group existe
echo "📦 Verificando Resource Group..."
if ! az group show --name $RESOURCE_GROUP &> /dev/null; then
    echo "❌ Resource Group '$RESOURCE_GROUP' não existe!"
    echo "Crie com: az group create --name $RESOURCE_GROUP --location brazilsouth"
    exit 1
fi
echo "✅ Resource Group existe"

# Verificar se App Service existe
echo "🌐 Verificando App Service..."
if ! az webapp show --name $APP_NAME --resource-group $RESOURCE_GROUP &> /dev/null; then
    echo "❌ App Service '$APP_NAME' não existe!"
    echo "Crie com o script de setup"
    exit 1
fi
echo "✅ App Service existe"

# Configurar imagen Docker
echo "🐳 Configurando imagem Docker..."
FULL_IMAGE="$REGISTRY/$IMAGE_NAME:$TAG"
az webapp config container set \
    --name $APP_NAME \
    --resource-group $RESOURCE_GROUP \
    --container-image-name $FULL_IMAGE \
    --container-registry-url https://$REGISTRY

# Configurar startup command
echo "⚙️ Configurando startup command..."
az webapp config set \
    --name $APP_NAME \
    --resource-group $RESOURCE_GROUP \
    --startup-file "uvicorn src.api.main:app --host 0.0.0.0 --port 8000"

# Restart App Service
echo "🔄 Reiniciando App Service..."
az webapp restart --name $APP_NAME --resource-group $RESOURCE_GROUP

# Aguardar deploy
echo "⏳ Aguardando deploy (45s)..."
sleep 45

# Health check
echo "🏥 Executando health check..."
APP_URL="https://$APP_NAME.azurewebsites.net/health"
MAX_RETRIES=10
RETRY=0

while [ $RETRY -lt $MAX_RETRIES ]; do
    HTTP_CODE=$(curl -s -o /dev/null -w "%{http_code}" "$APP_URL" 2>/dev/null || echo "000")
    if [ "$HTTP_CODE" = "200" ]; then
        echo "✅ Health check passou!"
        echo ""
        echo "🎉 Deploy concluído com sucesso!"
        echo "🌐 URL: https://$APP_NAME.azurewebsites.net"
        echo "📖 Docs: https://$APP_NAME.azurewebsites.net/docs"
        exit 0
    fi
    echo "⏳ Tentativa $((RETRY + 1))/$MAX_RETRIES - Status: $HTTP_CODE"
    RETRY=$((RETRY + 1))
    sleep 10
done

echo "❌ Health check falhou após $MAX_RETRIES tentativas"
echo "🔍 Verifique logs: az webapp log tail --name $APP_NAME --resource-group $RESOURCE_GROUP"
exit 1
