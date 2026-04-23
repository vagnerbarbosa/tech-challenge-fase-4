#!/bin/bash
# ===========================================
# Script para rodar API com Mocks Azure
# ===========================================
# Uso: ./scripts/run-mock.sh [flags]
#   --rebuild    Força rebuild das imagens sem cache
#

set -e

REBUILD=false

# Parse arguments
for arg in "$@"; do
    case $arg in
        --rebuild)
            REBUILD=true
            shift
            ;;
    esac
done

echo "🚀 Iniciando ambiente com mocks Azure..."
echo ""
echo "   API: http://localhost:8000"
echo "   Docs: http://localhost:8000/docs"
echo "   Mock Text: http://localhost:3001"
echo "   Mock Speech: http://localhost:3002"
echo "   Mock Vision: http://localhost:3003"
echo ""

# Verificar se docker-compose existe
if command -v docker-compose &> /dev/null; then
    COMPOSE="docker-compose"
elif command -v docker &> /dev/null && docker compose version &> /dev/null; then
    COMPOSE="docker compose"
else
    echo "❌ Docker Compose não encontrado!"
    exit 1
fi

# Se --rebuild, remover imagens antigas e rebuildar
if [ "$REBUILD" = true ]; then
    echo "🧹 Rebuild forçado - removendo imagens antigas..."
    $COMPOSE -f docker-compose.mock.yml down 2>/dev/null || true
    docker rmi tech-challenge-fase-4-api tech-challenge-fase-4-mock-azure 2>/dev/null || true
    echo "🔨 Rebuildando imagens..."
    $COMPOSE -f docker-compose.mock.yml build --no-cache
    echo ""
fi

# Subir serviços
$COMPOSE -f docker-compose.mock.yml up --build "$@"
