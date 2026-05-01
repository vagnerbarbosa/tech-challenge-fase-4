#!/bin/bash
# Script para atualizar documentação com IP de deploy
#
# Descrição:
#   Atualiza automaticamente todos os arquivos de documentação do projeto
#   substituindo o placeholder <DEPLOY_URL> pelo IP real do deploy Azure.
#
# Uso:
#   ./scripts/update-deploy-docs.sh <IP_ADDRESS>
#   ./scripts/update-deploy-docs.sh                    # Usa variável DEPLOY_IP
#
# Arquivos atualizados:
#   - README.md
#   - docs/PROJECT_STATUS.md
#   - docs/RUNNING.md
#   - specs/*/ (todos os arquivos .md)
#
# Exemplo:
#   ./scripts/update-deploy-docs.sh 20.201.7.217
#
# Autor: Claude Code
# Data: 2026-05-01

set -e

IP="${1:-$DEPLOY_IP}"

if [ -z "$IP" ]; then
    echo "❌ IP não fornecido. Use: $0 <IP_ADDRESS> ou defina DEPLOY_IP"
    exit 1
fi

# Detectar diretório raiz do projeto (onde está o README.md)
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(cd "$SCRIPT_DIR/.." && pwd)"

echo "📝 Atualizando documentação com IP: http://${IP}:8000"
echo "📁 Diretório do projeto: $PROJECT_ROOT"

# Função para atualizar arquivo se existir
update_file() {
    local file="$1"
    local pattern="$2"
    local replacement="$3"

    if [ -f "$file" ]; then
        if grep -q "$pattern" "$file"; then
            sed -i "s|$pattern|$replacement|g" "$file"
            echo "✅ Atualizado: $file"
        else
            echo "ℹ️  Padrão não encontrado em: $file"
        fi
    else
        echo "⚠️  Arquivo não encontrado: $file"
    fi
}

# Atualizar README.md
update_file "$PROJECT_ROOT/README.md" "<DEPLOY_URL>" "http://${IP}:8000"

# Atualizar docs/PROJECT_STATUS.md
update_file "$PROJECT_ROOT/docs/PROJECT_STATUS.md" "<DEPLOY_URL>" "http://${IP}:8000"

# Atualizar docs/RUNNING.md
update_file "$PROJECT_ROOT/docs/RUNNING.md" "<DEPLOY_URL>" "http://${IP}:8000"

# Verificar se specs existem e atualizar
for spec_dir in "$PROJECT_ROOT/specs/"*/; do
    if [ -d "$spec_dir" ]; then
        for file in "$spec_dir"*.md; do
            if [ -f "$file" ]; then
                update_file "$file" "<DEPLOY_URL>" "http://${IP}:8000"
            fi
        done
    fi
done

# Verificar se houve alterações
if git -C "$PROJECT_ROOT" diff --quiet 2>/dev/null; then
    echo "ℹ️  Nenhuma alteração para commitar"
else
    echo "✅ Documentação atualizada com sucesso!"
    git -C "$PROJECT_ROOT" status --short
fi
