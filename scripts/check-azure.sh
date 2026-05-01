#!/bin/bash
# ===========================================
# Script de Diagnóstico e Deploy Azure Container Instances
# ===========================================
# Uso: ./scripts/check-azure.sh [check|deploy|logs|status]

set -e

# Cores para output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m'

# Configurações
RESOURCE_GROUP="rg-tech-challenge-fase4"
LOCATION="brazilsouth"
CONTAINER_NAME="tech-challenge-api"
IMAGE_NAME="ghcr.io/vagnerbarbosa/tech-challenge-fase4:latest"

# ============================================
# FUNÇÕES AUXILIARES
# ============================================

log_info() {
    echo -e "${BLUE}ℹ️  $1${NC}"
}

log_success() {
    echo -e "${GREEN}✅ $1${NC}"
}

log_warning() {
    echo -e "${YELLOW}⚠️  $1${NC}"
}

log_error() {
    echo -e "${RED}❌ $1${NC}"
}

# ============================================
# CHECK - Verificar status atual
# ============================================
cmd_check() {
    log_info "Verificando status da Azure..."
    echo ""

    # Verificar login
    log_info "Verificando login Azure..."
    if az account show > /dev/null 2>&1; then
        SUBSCRIPTION=$(az account show --query name -o tsv)
        log_success "Logado como: $SUBSCRIPTION"
    else
        log_error "Não está logado no Azure"
        echo "Execute: az login"
        exit 1
    fi
    echo ""

    # Verificar Resource Group
    log_info "Verificando Resource Group..."
    if az group show --name $RESOURCE_GROUP > /dev/null 2>&1; then
        log_success "Resource Group '$RESOURCE_GROUP' existe"
    else
        log_warning "Resource Group '$RESOURCE_GROUP' não existe"
    fi
    echo ""

    # Verificar AI Services
    log_info "Verificando Azure AI Services..."
    for service in tech-challenge-text tech-challenge-speech tech-challenge-vision tech-challenge-content-safety; do
        if az cognitiveservices account show --name $service --resource-group $RESOURCE_GROUP > /dev/null 2>&1; then
            log_success "✓ $service"
        else
            log_warning "✗ $service (não existe)"
        fi
    done
    echo ""

    # Verificar Container
    log_info "Verificando Container Instance..."
    if az container show --resource-group $RESOURCE_GROUP --name $CONTAINER_NAME > /dev/null 2>&1; then
        log_success "Container '$CONTAINER_NAME' existe"

        # Obter IP e status
        IP=$(az container show --resource-group $RESOURCE_GROUP --name $CONTAINER_NAME --query ipAddress.ip -o tsv 2>/dev/null || echo "")
        STATE=$(az container show --resource-group $RESOURCE_GROUP --name $CONTAINER_NAME --query containers[0].instanceView.currentState.state -o tsv 2>/dev/null || echo "Unknown")

        echo "   IP: $IP:8000"
        echo "   Estado: $STATE"

        if [ -n "$IP" ]; then
            echo ""
            log_info "Testando health endpoint..."
            HTTP_STATUS=$(curl -s -o /dev/null -w "%{http_code}" "http://$IP:8000/health" 2>/dev/null || echo "000")

            if [ "$HTTP_STATUS" = "200" ]; then
                log_success "API está respondendo (HTTP 200)"
                echo ""
                echo "   🌐 URL: http://$IP:8000"
                echo "   📚 Docs: http://$IP:8000/docs"
                echo "   💓 Health: http://$IP:8000/health"
            else
                log_error "API não está respondendo (HTTP $HTTP_STATUS)"
            fi
        fi
    else
        log_warning "Container '$CONTAINER_NAME' não existe"
    fi
}

# ============================================
# DEPLOY - Criar/recriar todos os recursos
# ============================================
cmd_deploy() {
    log_info "Iniciando deploy completo na Azure..."
    echo ""

    # Verificar login
    if ! az account show > /dev/null 2>&1; then
        log_error "Não está logado no Azure. Execute: az login"
        exit 1
    fi

    # Criar Resource Group
    log_info "Criando Resource Group..."
    az group create \
        --name $RESOURCE_GROUP \
        --location $LOCATION \
        --tags "project=tech-challenge" "environment=production" \
        > /dev/null 2>&1 || true
    log_success "Resource Group OK"

    # Criar AI Services
    log_info "Criando Azure AI Services..."

    # Text Analytics
    az cognitiveservices account create \
        --name tech-challenge-text \
        --resource-group $RESOURCE_GROUP \
        --location $LOCATION \
        --kind TextAnalytics \
        --sku F0 \
        > /dev/null 2>&1 || true
    log_success "Text Analytics OK"

    # Speech Service
    az cognitiveservices account create \
        --name tech-challenge-speech \
        --resource-group $RESOURCE_GROUP \
        --location $LOCATION \
        --kind SpeechServices \
        --sku F0 \
        > /dev/null 2>&1 || true
    log_success "Speech Service OK"

    # Vision Service
    az cognitiveservices account create \
        --name tech-challenge-vision \
        --resource-group $RESOURCE_GROUP \
        --location $LOCATION \
        --kind ComputerVision \
        --sku F0 \
        > /dev/null 2>&1 || true
    log_success "Vision Service OK"

    # Content Safety Service
    az cognitiveservices account create \
        --name tech-challenge-content-safety \
        --resource-group $RESOURCE_GROUP \
        --location $LOCATION \
        --kind ContentSafety \
        --sku F0 \
        > /dev/null 2>&1 || true
    log_success "Content Safety Service OK"

    # Obter credenciais
    log_info "Obtendo credenciais..."

    TEXT_ENDPOINT=$(az cognitiveservices account show --name tech-challenge-text --resource-group $RESOURCE_GROUP --query properties.endpoint -o tsv)
    TEXT_KEY=$(az cognitiveservices account keys list --name tech-challenge-text --resource-group $RESOURCE_GROUP --query key1 -o tsv)
    SPEECH_KEY=$(az cognitiveservices account keys list --name tech-challenge-speech --resource-group $RESOURCE_GROUP --query key1 -o tsv)
    VISION_ENDPOINT=$(az cognitiveservices account show --name tech-challenge-vision --resource-group $RESOURCE_GROUP --query properties.endpoint -o tsv)
    VISION_KEY=$(az cognitiveservices account keys list --name tech-challenge-vision --resource-group $RESOURCE_GROUP --query key1 -o tsv)
    CONTENT_SAFETY_ENDPOINT=$(az cognitiveservices account show --name tech-challenge-content-safety --resource-group $RESOURCE_GROUP --query properties.endpoint -o tsv)
    CONTENT_SAFETY_KEY=$(az cognitiveservices account keys list --name tech-challenge-content-safety --resource-group $RESOURCE_GROUP --query key1 -o tsv)

    log_success "Credenciais obtidas"

    # Deletar container existente
    log_info "Limpando container anterior..."
    az container delete \
        --resource-group $RESOURCE_GROUP \
        --name $CONTAINER_NAME \
        --yes \
        > /dev/null 2>&1 || true

    # Criar novo container
    log_info "Criando Container Instance (pode levar 2-3 minutos)..."
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
            AZURE_CONTENT_SAFETY_ENDPOINT="$CONTENT_SAFETY_ENDPOINT" \
            AZURE_CONTENT_SAFETY_KEY="$CONTENT_SAFETY_KEY" \
            CONTENT_SAFETY_ENABLED=true \
            DATABASE_URL="sqlite:///tmp/app.db" \
            REDIS_ENABLED=false \
            SECURITY_API_KEY="demo-api-key" \
            SECURITY_ADMIN_KEY="demo-admin-key" \
        --restart-policy OnFailure \
        > /dev/null

    # Obter IP
    IP=$(az container show --resource-group $RESOURCE_GROUP --name $CONTAINER_NAME --query ipAddress.ip -o tsv)
    log_success "Container criado em: $IP:8000"

    # Aguardar inicialização
    log_info "Aguardando inicialização (60s)..."
    sleep 60

    # Health check
    log_info "Verificando se a API está respondendo..."
    MAX_RETRIES=10
    RETRY=0

    while [ $RETRY -lt $MAX_RETRIES ]; do
        HTTP_STATUS=$(curl -s -o /dev/null -w "%{http_code}" "http://$IP:8000/health" 2>/dev/null || echo "000")

        if [ "$HTTP_STATUS" = "200" ]; then
            echo ""
            log_success "Deploy concluído com sucesso!"
            echo ""
            echo "========================================"
            echo "🌐 URL da API: http://$IP:8000"
            echo "📚 Swagger UI:  http://$IP:8000/docs"
            echo "💓 Health:      http://$IP:8000/health"
            echo "========================================"
            echo ""
            return 0
        fi

        RETRY=$((RETRY + 1))
        log_info "Tentativa $RETRY/$MAX_RETRIES - Status: $HTTP_STATUS"
        sleep 15
    done

    log_error "API não respondeu após $MAX_RETRIES tentativas"
    echo ""
    log_info "Verificando logs..."
    cmd_logs
    return 1
}

# ============================================
# LOGS - Ver logs do container
# ============================================
cmd_logs() {
    log_info "Obtendo logs do container..."
    echo ""
    az container logs \
        --resource-group $RESOURCE_GROUP \
        --name $CONTAINER_NAME \
        --follow 2>/dev/null || log_error "Não foi possível obter logs"
}

# ============================================
# STATUS - Status detalhado do container
# ============================================
cmd_status() {
    log_info "Status detalhado do container..."
    echo ""
    az container show \
        --resource-group $RESOURCE_GROUP \
        --name $CONTAINER_NAME \
        --query '{
            name: name,
            ip: ipAddress.ip,
            state: containers[0].instanceView.currentState,
            image: containers[0].image,
            restartCount: containers[0].instanceView.restartCount
        }' \
        -o json 2>/dev/null || log_error "Container não encontrado"
}

# ============================================
# DELETE - Remover todos os recursos
# ============================================
cmd_delete() {
    log_warning "ATENÇÃO: Isso vai deletar TODOS os recursos!"
    read -p "Tem certeza? (s/N): " confirm

    if [ "$confirm" = "s" ] || [ "$confirm" = "S" ]; then
        log_info "Deletando Resource Group..."
        az group delete --name $RESOURCE_GROUP --yes --no-wait
        log_success "Deleção iniciada. Pode levar alguns minutos."
    else
        log_info "Operação cancelada"
    fi
}

# ============================================
# HELP
# ============================================
cmd_help() {
    echo "Uso: ./scripts/check-azure.sh [comando]"
    echo ""
    echo "Comandos:"
    echo "  check   - Verificar status atual dos recursos (padrão)"
    echo "  deploy  - Criar/recriar todos os recursos e fazer deploy"
    echo "  logs    - Ver logs do container em tempo real"
    echo "  status  - Mostrar status detalhado do container"
    echo "  delete  - Remover todos os recursos (cuidado!)"
    echo "  help    - Mostrar esta ajuda"
    echo ""
    echo "Exemplos:"
    echo "  ./scripts/check-azure.sh check    # Verificar status"
    echo "  ./scripts/check-azure.sh deploy   # Fazer deploy"
    echo "  ./scripts/check-azure.sh logs     # Ver logs"
}

# ============================================
# MAIN
# ============================================

echo -e "${BLUE}========================================${NC}"
echo -e "${BLUE}  Tech Challenge - Azure Manager${NC}"
echo -e "${BLUE}========================================${NC}"
echo ""

# Verificar se AZ CLI está instalado
if ! command -v az &> /dev/null; then
    log_error "Azure CLI não encontrado"
    echo "Instale em: https://aka.ms/install-azure-cli"
    exit 1
fi

# Comando padrão é 'check'
COMMAND=${1:-check}

case $COMMAND in
    check)
        cmd_check
        ;;
    deploy)
        cmd_deploy
        ;;
    logs)
        cmd_logs
        ;;
    status)
        cmd_status
        ;;
    delete)
        cmd_delete
        ;;
    help|--help|-h)
        cmd_help
        ;;
    *)
        log_error "Comando desconhecido: $COMMAND"
        cmd_help
        exit 1
        ;;
esac
