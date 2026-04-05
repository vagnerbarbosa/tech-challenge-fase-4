#!/bin/bash
# ===========================================
# Script para Verificar Conexão Azure
# ===========================================

set -e

# Cores para output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

echo "☁️  Verificando conexão com Azure AI Services..."
echo ""

# Verificar variáveis de ambiente
check_env_var() {
    local var_name=$1
    local var_value=$(eval echo \$$var_name)

    if [ -z "$var_value" ]; then
        echo -e "${RED}❌ $var_name: NÃO CONFIGURADA${NC}"
        return 1
    else
        echo -e "${GREEN}✅ $var_name: OK${NC}"
        return 0
    fi
}

# Verificar variáveis necessárias
echo "📋 Variáveis de ambiente:"
check_env_var "AZURE_TEXT_KEY"
check_env_var "AZURE_TEXT_ENDPOINT"
check_env_var "AZURE_SPEECH_KEY"
check_env_var "AZURE_SPEECH_REGION"
check_env_var "AZURE_VISION_KEY"
check_env_var "AZURE_VISION_ENDPOINT"

echo ""
echo "🧪 Testando conectividade (em breve)..."
echo -e "${YELLOW}⚠️  Testes de conectividade serão implementados na Task 003${NC}"

echo ""
echo "✅ Verificação de variáveis completada!"
