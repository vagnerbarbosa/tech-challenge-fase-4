#!/bin/bash
# ===========================================
# Script para Rodar Testes
# ===========================================

set -e

echo "🧪 Executando testes..."

# Verificar se está no virtualenv
if [ -z "$VIRTUAL_ENV" ]; then
    echo "🔄 Ativando ambiente Poetry..."
    source $(poetry env info --path)/bin/activate 2>/dev/null || source $(poetry env info --path)/Scripts/activate
fi

# Parse arguments
TEST_TYPE="${1:-all}"

if [ "$TEST_TYPE" = "unit" ]; then
    echo "   📦 Testes unitários apenas"
    pytest tests/unit -v -m "not slow"
elif [ "$TEST_TYPE" = "integration" ]; then
    echo "   🔗 Testes de integração"
    pytest tests/integration -v
elif [ "$TEST_TYPE" = "coverage" ]; then
    echo "   📊 Relatório de cobertura"
    pytest --cov=src --cov-report=html --cov-report=term-missing
else
    echo "   📦 Rodando todos os testes..."
    pytest -v --cov=src --cov-report=term-missing
fi

echo ""
echo "✅ Testes completos!"
