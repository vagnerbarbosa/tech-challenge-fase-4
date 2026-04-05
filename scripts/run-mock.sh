#!/bin/bash
# ===========================================
# Script para rodar API com Mocks Azure
# ===========================================

set -e

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

# Subir serviços
$COMPOSE -f docker-compose.mock.yml up --build "$@"
