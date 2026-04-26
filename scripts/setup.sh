#!/bin/bash
# ===========================================
# Script de Setup Inicial
# ===========================================

set -e

echo "🚀 Configurando ambiente de desenvolvimento..."

# Verificar Python 3.11+
echo "📦 Verificando Python..."
python_version=$(python --version 2>&1 | grep -oP '\d+\.\d+')
required_version="3.11"

if [ "$(printf '%s\n' "$required_version" "$python_version" | sort -V | head -n1)" != "$required_version" ]; then
    echo "❌ Python 3.11+ é obrigatório. Versão encontrada: $python_version"
    exit 1
fi

echo "✅ Python $python_version encontrado"

# Verificar Poetry
echo "📦 Verificando Poetry..."
if ! command -v poetry &> /dev/null; then
    echo "📥 Instalando Poetry..."
    curl -sSL https://install.python-poetry.org | python -
    export PATH="$HOME/.local/bin:$PATH"
fi

poetry --version

# Instalar dependências
echo "📥 Instalando dependências..."
poetry install --with dev

# Criar .env se não existir
if [ ! -f .env ]; then
    echo "📝 Criando arquivo .env..."
    cp .env.example .env
    echo "⚠️  Por favor, edite o arquivo .env com suas credenciais Azure"
fi

# Criar diretórios de dados
mkdir -p data logs uploads

echo ""
echo "✅ Setup completo!"
echo ""
echo "Próximos passos:"
echo "  1. Edite o arquivo .env com suas credenciais"
echo "  2. Execute: poetry shell"
echo "  3. Execute: python -m uvicorn src.api.main:app --reload"
echo ""
