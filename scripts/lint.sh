#!/bin/bash
# ===========================================
# Script para Rodar Linter
# ===========================================

set -e

echo "🔍 Verificando código..."

# Verificar se está no virtualenv
if [ -z "$VIRTUAL_ENV" ]; then
    echo "🔄 Ativando ambiente Poetry..."
    source $(poetry env info --path)/bin/activate 2>/dev/null || source $(poetry env info --path)/Scripts/activate
fi

echo ""
echo "📝 Rodando Ruff..."
ruff check .

echo ""
echo "🎨 Formatando código..."
ruff format --check .

echo ""
echo "🔬 Rodando mypy..."
mypy src/

echo ""
echo "✅ Verificação completa!"
