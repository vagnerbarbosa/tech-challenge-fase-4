#!/bin/sh
# Entrypoint script para Azure Container Instances
# Garante que o ambiente está configurado corretamente

set -e

echo "========================================"
echo "Iniciando Tech Challenge API"
echo "========================================"
echo "Diretório atual: $(pwd)"
echo "Usuário: $(whoami)"
echo "Python: $(python --version)"
echo ""

# Verificar estrutura de diretórios
echo "Conteúdo do diretório /app:"
ls -la /app/ 2>/dev/null || echo "Não foi possível listar /app"

echo ""
echo "Verificando módulo src:"
if [ -d "/app/src" ]; then
    echo "✓ Diretório /app/src existe"
    ls -la /app/src/ | head -5
else
    echo "✗ Diretório /app/src não encontrado!"
fi

echo ""
echo "========================================"
echo "Iniciando Uvicorn..."
echo "========================================"

# Executar uvicorn com tratamento de erro
exec uvicorn src.api.main:app \
    --host 0.0.0.0 \
    --port 8000 \
    --log-level info \
    --proxy-headers \
    --forwarded-allow-ips '*'
