#!/bin/bash
# ===========================================
# Script para atualizar imagem Docker de mocks
# com as configurações da Spec 007 (Security Hardening)
# ===========================================

set -e

echo "🔄 Atualizando imagem Docker de mocks..."
echo ""

# Parar containers existentes
echo "🛑 Parando containers existentes..."
docker compose -f docker-compose.mock.yml down 2>/dev/null || \
    docker stop health-api-mock health-redis-mock mock-azure 2>/dev/null || true

# Remover containers antigos
echo "🗑️  Removendo containers antigos..."
docker rm health-api-mock health-redis-mock mock-azure 2>/dev/null || true

# Remover imagens antigas
echo "🧹 Removendo imagens antigas..."
docker rmi tech-challenge-fase-4-api tech-challenge-fase-4-mock-azure 2>/dev/null || true

# Rebuildar imagens
echo "🔨 Rebuildando imagens com Spec 007..."
docker compose -f docker-compose.mock.yml build --no-cache

echo ""
echo "✅ Imagens atualizadas com sucesso!"
echo ""
echo "🚀 Para iniciar os containers, execute:"
echo "   docker compose -f docker-compose.mock.yml up -d"
echo ""
echo "📋 Verifique os logs com:"
echo "   docker compose -f docker-compose.mock.yml logs -f api"
