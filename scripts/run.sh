#!/bin/bash
# ===========================================
# Script para Rodar Local
# ===========================================

set -e

# Verificar se está no virtualenv do Poetry
if [ -z "$VIRTUAL_ENV" ]; then
    echo "🔄 Ativando ambiente Poetry..."
    source $(poetry env info --path)/bin/activate 2>/dev/null || source $(poetry env info --path)/Scripts/activate
fi

echo "🚀 Iniciando servidor de desenvolvimento..."
echo "   URL: http://localhost:8000"
echo "   Docs: http://localhost:8000/docs"
echo ""

# Rodar uvicorn com reload
python -m uvicorn src.api.main:app \
    --host 0.0.0.0 \
    --port 8000 \
    --reload \
    --reload-dir src \
    --log-level debug
