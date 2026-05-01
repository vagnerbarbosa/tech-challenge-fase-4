#!/bin/bash
# Script de deploy Azure v2 - com entrypoint shell
# Uso: ./scripts/deploy-azure-v2.sh

set -e

# Cores para output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Configurações
RESOURCE_GROUP="rg-tech-challenge-fase4"
LOCATION="brazilsouth"
CONTAINER_NAME="tech-challenge-api"
IMAGE_NAME="ghcr.io/vagnerbarbosa/tech-challenge-fase4:latest"

# Azure AI Services
TEXT_SERVICE="tech-challenge-text"
SPEECH_SERVICE="tech-challenge-speech"
VISION_SERVICE="tech-challenge-vision"

echo -e "${BLUE}========================================${NC}"
echo -e "${BLUE}  Deploy Azure - Tech Challenge v2${NC}"
echo -e "${BLUE}========================================${NC}"
echo ""

# Verificar login Azure
echo -e "${YELLOW}Verificando login Azure...${NC}"
az account show > /dev/null 2>&1 || {
    echo -e "${RED}Erro: Não está logado no Azure.${NC}"
    echo "Execute: az login"
    exit 1
}
SUBSCRIPTION=$(az account show --query name -o tsv)
echo -e "${GREEN}✓ Logado como: $SUBSCRIPTION${NC}"
echo ""

# Passo 1: Criar Resource Group
echo -e "${YELLOW}Passo 1: Criando Resource Group...${NC}"
az group create \
    --name $RESOURCE_GROUP \
    --location $LOCATION \
    --tags "project=tech-challenge" "environment=production" \
    2>/dev/null || echo -e "${GREEN}✓ Resource Group já existe${NC}"
echo -e "${GREEN}✓ Resource Group: $RESOURCE_GROUP${NC}"
echo ""

# Passo 2: Criar Azure AI Services
echo -e "${YELLOW}Passo 2: Criando Azure AI Services...${NC}"

# Text Analytics
echo -e "${BLUE}  - Criando Text Analytics...${NC}"
az cognitiveservices account create \
    --name $TEXT_SERVICE \
    --resource-group $RESOURCE_GROUP \
    --location $LOCATION \
    --kind TextAnalytics \
    --sku F0 \
    --tags "service=text" \
    2>/dev/null || echo -e "${GREEN}    ✓ Text Analytics já existe${NC}"

# Speech Service
echo -e "${BLUE}  - Criando Speech Service...${NC}"
az cognitiveservices account create \
    --name $SPEECH_SERVICE \
    --resource-group $RESOURCE_GROUP \
    --location $LOCATION \
    --kind SpeechServices \
    --sku F0 \
    --tags "service=speech" \
    2>/dev/null || echo -e "${GREEN}    ✓ Speech Service já existe${NC}"

# Vision Service
echo -e "${BLUE}  - Criando Vision Service...${NC}"
az cognitiveservices account create \
    --name $VISION_SERVICE \
    --resource-group $RESOURCE_GROUP \
    --location $LOCATION \
    --kind ComputerVision \
    --sku F0 \
    --tags "service=vision" \
    2>/dev/null || echo -e "${GREEN}    ✓ Vision Service já existe${NC}"

echo -e "${GREEN}✓ Azure AI Services criados${NC}"
echo ""

# Passo 3: Obter chaves e endpoints
echo -e "${YELLOW}Passo 3: Obtendo credenciais dos serviços...${NC}"

TEXT_KEY=$(az cognitiveservices account keys list \
    --name $TEXT_SERVICE \
    --resource-group $RESOURCE_GROUP \
    --query key1 -o tsv)
TEXT_ENDPOINT=$(az cognitiveservices account show \
    --name $TEXT_SERVICE \
    --resource-group $RESOURCE_GROUP \
    --query properties.endpoint -o tsv)

SPEECH_KEY=$(az cognitiveservices account keys list \
    --name $SPEECH_SERVICE \
    --resource-group $RESOURCE_GROUP \
    --query key1 -o tsv)

VISION_KEY=$(az cognitiveservices account keys list \
    --name $VISION_SERVICE \
    --resource-group $RESOURCE_GROUP \
    --query key1 -o tsv)
VISION_ENDPOINT=$(az cognitiveservices account show \
    --name $VISION_SERVICE \
    --resource-group $RESOURCE_GROUP \
    --query properties.endpoint -o tsv)

echo -e "${GREEN}✓ Credenciais obtidas${NC}"
echo ""

# Passo 4: Criar Container Instance
echo -e "${YELLOW}Passo 4: Criando Container Instance...${NC}"
echo -e "${BLUE}  Isso pode levar alguns minutos...${NC}"

# Deletar container existente se houver
az container delete \
    --resource-group $RESOURCE_GROUP \
    --name $CONTAINER_NAME \
    --yes 2>/dev/null || true

# Criar novo container com entrypoint shell
az container create \
    --resource-group $RESOURCE_GROUP \
    --name $CONTAINER_NAME \
    --image $IMAGE_NAME \
    --cpu 1 \
    --memory 2 \
    --ports 8000 \
    --ip-address public \
    --os-type Linux \
    --location $LOCATION \
    --environment-variables \
        ENVIRONMENT=production \
        LOG_LEVEL=INFO \
        AZURE_TEXT_ENDPOINT="$TEXT_ENDPOINT" \
        AZURE_TEXT_KEY="$TEXT_KEY" \
        AZURE_SPEECH_KEY="$SPEECH_KEY" \
        AZURE_SPEECH_REGION="$LOCATION" \
        AZURE_VISION_ENDPOINT="$VISION_ENDPOINT" \
        AZURE_VISION_KEY="$VISION_KEY" \
        DATABASE_URL="sqlite:///tmp/app.db" \
        REDIS_ENABLED=false \
        SECURITY_API_KEY="demo-api-key" \
        SECURITY_ADMIN_KEY="demo-admin-key" \
    --restart-policy OnFailure \
    --query '{ip: ipAddress.ip, state: provisioningState}' \
    --output table

echo -e "${GREEN}✓ Container criado${NC}"
echo ""

# Passo 5: Aguardar e verificar status
echo -e "${YELLOW}Passo 5: Aguardando inicialização (60s)...${NC}"
sleep 60

echo -e "${YELLOW}Verificando status do container...${NC}"
CONTAINER_IP=$(az container show \
    --resource-group $RESOURCE_GROUP \
    --name $CONTAINER_NAME \
    --query ipAddress.ip \
    --output tsv 2>/dev/null || echo "")

if [ -n "$CONTAINER_IP" ]; then
    echo -e "${GREEN}✓ Container IP: $CONTAINER_IP:8000${NC}"
    echo ""
    echo -e "${YELLOW}Testando health endpoint...${NC}"
    sleep 10

    HEALTH_STATUS=$(curl -s -o /dev/null -w "%{http_code}" "http://$CONTAINER_IP:8000/health" 2>/dev/null || echo "000")

    if [ "$HEALTH_STATUS" = "200" ]; then
        echo -e "${GREEN}✓ Health check passou! (HTTP 200)${NC}"
        echo ""
        echo -e "${GREEN}========================================${NC}"
        echo -e "${GREEN}  Deploy concluído com sucesso!${NC}"
        echo -e "${GREEN}========================================${NC}"
        echo ""
        echo -e "URL da API: http://$CONTAINER_IP:8000"
        echo -e "Health Check: http://$CONTAINER_IP:8000/health"
        echo -e "Docs: http://$CONTAINER_IP:8000/docs"
        echo ""
        echo "API Key: demo-api-key"
        echo "Admin Key: demo-admin-key"
    else
        echo -e "${YELLOW}⚠ Health check retornou HTTP $HEALTH_STATUS${NC}"
        echo -e "${YELLOW}Verificando logs...${NC}"
        az container logs \
            --resource-group $RESOURCE_GROUP \
            --name $CONTAINER_NAME \
            --lines 50 2>/dev/null || echo "Não foi possível obter logs"
    fi
else
    echo -e "${RED}✗ Não foi possível obter IP do container${NC}"
fi

echo ""
echo -e "${BLUE}Comandos úteis:${NC}"
echo "  Ver logs: az container logs --resource-group $RESOURCE_GROUP --name $CONTAINER_NAME"
echo "  Status: az container show --resource-group $RESOURCE_GROUP --name $CONTAINER_NAME"
echo "  Delete: az container delete --resource-group $RESOURCE_GROUP --name $CONTAINER_NAME --yes"
echo ""
