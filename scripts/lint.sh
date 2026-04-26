#!/bin/bash
# ===========================================
# Script para Rodar Linter - Multi-plataforma
# ===========================================
# Suporte: Linux, macOS, Windows (WSL/Git Bash)

set -e

# ============================================
# DETECÇÃO DO SISTEMA OPERACIONAL
# ============================================
detect_os() {
    case "$(uname -s)" in
        Linux*)
            if [[ -n "${WSL_DISTRO_NAME:-}" ]] || [[ "$(uname -r)" == *"microsoft"* ]] || [[ "$(uname -r)" == *"WSL"* ]]; then
                echo "linux-wsl"
            else
                echo "linux"
            fi
            ;;
        Darwin*)
            echo "macos"
            ;;
        CYGWIN*|MINGW*|MSYS*)
            echo "windows"
            ;;
        *)
            echo "unknown"
            ;;
    esac
}

OS=$(detect_os)

# ============================================
# ATIVAÇÃO DO POETRY POR SO
# ============================================
activate_poetry_env() {
    if [ -n "$VIRTUAL_ENV" ]; then
        return 0
    fi

    echo "🔄 Ativando ambiente Poetry..."

    local poetry_env_path
    poetry_env_path=$(poetry env info --path 2>/dev/null) || {
        echo "❌ Poetry não está configurado. Execute: poetry install"
        exit 1
    }

    case "$OS" in
        linux*|macos)
            if [ -f "$poetry_env_path/bin/activate" ]; then
                # shellcheck source=/dev/null
                source "$poetry_env_path/bin/activate"
            else
                echo "❌ Ambiente Poetry não encontrado em: $poetry_env_path/bin/activate"
                exit 1
            fi
            ;;
        windows)
            if [ -f "$poetry_env_path/Scripts/activate" ]; then
                # shellcheck source=/dev/null
                source "$poetry_env_path/Scripts/activate"
            else
                echo "❌ Ambiente Poetry não encontrado em: $poetry_env_path/Scripts/activate"
                exit 1
            fi
            ;;
        *)
            echo "⚠️  SO não reconhecido. Tentando ativação padrão..."
            # shellcheck source=/dev/null
            source "$poetry_env_path/bin/activate" 2>/dev/null || source "$poetry_env_path/Scripts/activate"
            ;;
    esac
}

# Verificar dependências
if ! command -v poetry &> /dev/null; then
    echo "❌ Poetry não encontrado!"
    echo "   Instale: https://python-poetry.org/docs/#installation"
    exit 1
fi

echo "🔍 Verificando código..."
echo "   SO detectado: $OS"
echo ""

# Ativar ambiente
activate_poetry_env

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
