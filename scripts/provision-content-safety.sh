#!/bin/bash
# ===========================================
# Script de Provisionamento Azure AI Content Safety
# ===========================================
# Provisiona o recurso Azure AI Content Safety e configura variáveis de ambiente
#
# Uso: ./scripts/provision-content-safety.sh [opções]
#
# Opções:
#   --resource-group, -g    Nome do Resource Group (padrão: rg-tech-challenge-fase4)
#   --name, -n              Nome do recurso Content Safety (padrão: tech-challenge-content-safety)
#   --location, -l          Região Azure (padrão: brazilsouth)
#   --sku, -s               SKU do serviço (padrão: F0 - Free Tier)
#   --env-file, -e          Arquivo .env para atualizar (padrão: .env)
#   --help, -h              Mostrar ajuda
#
# Exemplos:
#   ./scripts/provision-content-safety.sh
#   ./scripts/provision-content-safety.sh --resource-group my-rg --name my-cs
#   ./scripts/provision-content-safety.sh -g my-rg -n my-cs -l eastus

set -e

# ============================================
# CONFIGURAÇÕES PADRÃO
# ============================================
DEFAULT_RESOURCE_GROUP="rg-tech-challenge-fase4"
DEFAULT_NAME="tech-challenge-content-safety"
DEFAULT_LOCATION="brazilsouth"
DEFAULT_SKU="F0"
DEFAULT_ENV_FILE=".env"

# ============================================
# CORES PARA OUTPUT
# ============================================
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
CYAN='\033[0;36m'
NC='\033[0m'

# ============================================
# FUNÇÕES DE LOG
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

log_step() {
    echo -e "${CYAN}▶️  $1${NC}"
}

# ============================================
# FUNÇÃO DE AJUDA
# ============================================
show_help() {
    head -n 24 "$0" | tail -n 23
}

# ============================================
# PARSE DE ARGUMENTOS
# ============================================
RESOURCE_GROUP="$DEFAULT_RESOURCE_GROUP"
RESOURCE_NAME="$DEFAULT_NAME"
LOCATION="$DEFAULT_LOCATION"
SKU="$DEFAULT_SKU"
ENV_FILE="$DEFAULT_ENV_FILE"

while [[ $# -gt 0 ]]; do
    case $1 in
        --resource-group|-g)
            RESOURCE_GROUP="$2"
            shift 2
            ;;
        --name|-n)
            RESOURCE_NAME="$2"
            shift 2
            ;;
        --location|-l)
            LOCATION="$2"
            shift 2
            ;;
        --sku|-s)
            SKU="$2"
            shift 2
            ;;
        --env-file|-e)
            ENV_FILE="$2"
            shift 2
            ;;
        --help|-h)
            show_help
            exit 0
            ;;
        *)
            log_error "Opção desconhecida: $1"
            show_help
            exit 1
            ;;
    esac
done

# ============================================
# HEADER
# ============================================
echo -e "${CYAN}========================================${NC}"
echo -e "${CYAN}  Azure AI Content Safety Provisioner${NC}"
echo -e "${CYAN}========================================${NC}"
echo ""

# ============================================
# VERIFICAÇÕES INICIAIS
# ============================================

# Verificar Azure CLI
log_step "Verificando Azure CLI..."
if ! command -v az &> /dev/null; then
    log_error "Azure CLI não encontrado"
    echo ""
    echo "Instale em: https://aka.ms/installazure-cli"
    echo ""
    echo "Para Linux/WSL:"
    echo "  curl -sL https://aka.ms/InstallAzureCLIDeb | sudo bash"
    exit 1
fi
log_success "Azure CLI encontrado"

# Verificar login Azure
log_step "Verificando autenticação Azure..."
if ! az account show &> /dev/null; then
    log_warning "Não autenticado no Azure"
    log_info "Executando az login..."
    az login
fi

SUBSCRIPTION=$(az account show --query name -o tsv)
SUBSCRIPTION_ID=$(az account show --query id -o tsv)
log_success "Logado na subscription: $SUBSCRIPTION"
echo "   Subscription ID: $SUBSCRIPTION_ID"
echo ""

# ============================================
# CONFIGURAÇÕES
# ============================================
log_step "Configurações do provisionamento:"
echo "   Resource Group: $RESOURCE_GROUP"
echo "   Nome do recurso: $RESOURCE_NAME"
echo "   Região: $LOCATION"
echo "   SKU: $SKU"
echo "   Arquivo env: $ENV_FILE"
echo ""

# ============================================
# CRIAR RESOURCE GROUP (SE NÃO EXISTIR)
# ============================================
log_step "Verificando Resource Group..."
if az group show --name "$RESOURCE_GROUP" &> /dev/null; then
    log_success "Resource Group já existe: $RESOURCE_GROUP"
else
    log_info "Criando Resource Group: $RESOURCE_GROUP"
    az group create \
        --name "$RESOURCE_GROUP" \
        --location "$LOCATION" \
        --tags "project=tech-challenge" "environment=production" \
        --output none
    log_success "Resource Group criado: $RESOURCE_GROUP"
fi
echo ""

# ============================================
# CRIAR AZURE AI CONTENT SAFETY (IDEMPOTENTE)
# ============================================
log_step "Provisionando Azure AI Content Safety..."

if az cognitiveservices account show --name "$RESOURCE_NAME" --resource-group "$RESOURCE_GROUP" &> /dev/null; then
    log_warning "Recurso já existe: $RESOURCE_NAME"
    log_info "Pulando criação, obtendo credenciais existentes..."
else
    log_info "Criando Azure AI Content Safety: $RESOURCE_NAME"
    log_info "Isso pode levar alguns segundos..."

    # Criar recurso Content Safety
    az cognitiveservices account create \
        --name "$RESOURCE_NAME" \
        --resource-group "$RESOURCE_GROUP" \
        --location "$LOCATION" \
        --kind ContentSafety \
        --sku "$SKU" \
        --tags "project=tech-challenge" "component=content-safety" \
        --output none

    log_success "Azure AI Content Safety criado com sucesso"
fi
echo ""

# ============================================
# OBTER CREDENCIAIS
# ============================================
log_step "Obtendo credenciais do serviço..."

# Obter endpoint
ENDPOINT=$(az cognitiveservices account show \
    --name "$RESOURCE_NAME" \
    --resource-group "$RESOURCE_GROUP" \
    --query properties.endpoint \
    --output tsv 2>/dev/null || echo "")

# Obter key
API_KEY=$(az cognitiveservices account keys list \
    --name "$RESOURCE_NAME" \
    --resource-group "$RESOURCE_GROUP" \
    --query key1 \
    --output tsv 2>/dev/null || echo "")

if [[ -z "$ENDPOINT" ]] || [[ -z "$API_KEY" ]]; then
    log_error "Não foi possível obter credenciais do serviço"
    exit 1
fi

log_success "Credenciais obtidas com sucesso"
echo ""

# ============================================
# MOSTRAR INFORMAÇÕES
# ============================================
echo -e "${CYAN}========================================${NC}"
echo -e "${CYAN}  Credenciais do Content Safety${NC}"
echo -e "${CYAN}========================================${NC}"
echo ""
echo -e "${YELLOW}⚠️  ATENÇÃO: Estas são credenciais sensíveis!${NC}"
echo ""
echo "   Endpoint: $ENDPOINT"
echo "   Key: ${API_KEY:0:8}...${API_KEY: -4}"
echo ""

# ============================================
# CONFIGURAR VARIÁVEIS DE AMBIENTE
# ============================================
log_step "Configurando variáveis de ambiente..."

# Backup do arquivo .env existente
if [[ -f "$ENV_FILE" ]]; then
    BACKUP_FILE="${ENV_FILE}.backup.$(date +%Y%m%d_%H%M%S)"
    cp "$ENV_FILE" "$BACKUP_FILE"
    log_info "Backup do $ENV_FILE criado: $BACKUP_FILE"
fi

# Função para atualizar ou adicionar variável no arquivo .env
update_env_var() {
    local file="$1"
    local key="$2"
    local value="$3"

    if [[ -f "$file" ]]; then
        # Verificar se a variável já existe no arquivo
        if grep -q "^${key}=" "$file" 2>/dev/null; then
            # Substituir valor existente
            sed -i "s|^${key}=.*|${key}=\${value}|" "$file"
        else
            # Adicionar nova variável
            echo "" >> "$file"
            echo "# Azure AI Content Safety" >> "$file"
            echo "${key}=${value}" >> "$file"
        fi
    else
        # Criar novo arquivo
        echo "# Azure AI Content Safety" > "$file"
        echo "${key}=${value}" >> "$file"
    fi
}

# Atualizar arquivo .env
update_env_var "$ENV_FILE" "AZURE_CONTENT_SAFETY_ENDPOINT" "$ENDPOINT"
update_env_var "$ENV_FILE" "AZURE_CONTENT_SAFETY_KEY" "$API_KEY"
update_env_var "$ENV_FILE" "CONTENT_SAFETY_ENABLED" "true"

log_success "Variáveis de ambiente atualizadas no arquivo: $ENV_FILE"
echo ""

# ============================================
# RESUMO
# ============================================
echo -e "${GREEN}========================================${NC}"
echo -e "${GREEN}  Provisionamento Concluído!${NC}"
echo -e "${GREEN}========================================${NC}"
echo ""
echo -e "${CYAN}📋 Resumo:${NC}"
echo "   Resource Group: $RESOURCE_GROUP"
echo "   Content Safety: $RESOURCE_NAME"
echo "   Região: $LOCATION"
echo "   SKU: $SKU"
echo ""
echo -e "${CYAN}🔑 Variáveis configuradas:${NC}"
echo "   AZURE_CONTENT_SAFETY_ENDPOINT=$ENDPOINT"
echo "   AZURE_CONTENT_SAFETY_KEY=${API_KEY:0:8}...${API_KEY: -4}"
echo "   CONTENT_SAFETY_ENABLED=true"
echo ""
echo -e "${CYAN}📝 Próximos passos:${NC}"
echo ""
echo "   1. As variáveis foram salvas no arquivo: $ENV_FILE"
echo ""
echo "   2. Para aplicar no container Azure:"
echo -e "      ${YELLOW}./scripts/check-azure.sh deploy${NC}"
echo ""
echo "   3. Para aplicar no Azure App Service:"
echo "      az webapp config appsettings set \\"
echo "        --name <app-name> \\"
echo "        --resource-group $RESOURCE_GROUP \\"
echo "        --settings \\"
echo "          AZURE_CONTENT_SAFETY_ENDPOINT=$ENDPOINT \\"
echo "          AZURE_CONTENT_SAFETY_KEY=$API_KEY \\"
echo "          CONTENT_SAFETY_ENABLED=true"
echo ""
echo "   4. Para testar a conexão:"
echo -e "      ${YELLOW}curl -X POST \"${ENDPOINT}contentsafety/text:analyze?api-version=2023-10-01\" \\${NC}"
echo -e "        ${YELLOW}-H \"Ocp-Apim-Subscription-Key: $API_KEY\" \\${NC}"
echo -e "        ${YELLOW}-H \"Content-Type: application/json\" \\${NC}"
echo -e "        ${YELLOW}-d '{\"text\": \"Teste de conteúdo\", \"categories\": [\"Hate\", \"Violence\"]}'${NC}"
echo ""
log_success "Script finalizado com sucesso!"
