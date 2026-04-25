#!/bin/bash
#
# Script para executar testes via Docker
#
# Este script reutiliza a imagem Docker existente (tech-challenge-fase-4-api)
# para executar testes, economizando espaço e tempo de build.
#
# Por que reutilizar a imagem existente?
# - Evita build duplicado (economia de ~20GB)
# - Reutiliza todas as dependências já instaladas
# - Mais rápido: sem instalação de PyTorch/CUDA novamente
#

set -e

# Cores para output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

echo -e "${BLUE}========================================${NC}"
echo -e "${BLUE}  Test Runner - Docker Mode          ${NC}"
echo -e "${BLUE}  (Reutilizando imagem existente)     ${NC}"
echo -e "${BLUE}========================================${NC}"
echo ""

# Função de ajuda
show_help() {
    echo "Uso: $0 [comando]"
    echo ""
    echo "Comandos disponíveis:"
    echo "  unit       - Executa testes unitários (padrão)"
    echo "  integration - Executa testes de integração"
    echo "  coverage   - Executa testes com relatório de cobertura"
    echo "  lint       - Executa linting (Ruff)"
    echo "  typecheck  - Executa type checking (mypy)"
    echo "  all        - Executa lint + typecheck + unit tests"
    echo "  rebuild    - Força rebuild da imagem (quando há novos testes/deps)"
    echo "  help       - Mostra esta ajuda"
    echo ""
    echo "Nota: Este script reutiliza a imagem 'tech-challenge-fase-4-api'"
    echo "      para economizar espaço (~20GB). Se a imagem não existir,"
    echo "      ela será buildada automaticamente via run-mock.sh."
    echo ""
    echo "Exemplos:"
    echo "  $0                    # Testes unitários"
    echo "  $0 unit               # Testes unitários (explícito)"
    echo "  $0 coverage           # Testes com cobertura"
    echo "  $0 all                # Todos os checks"
    echo "  $0 rebuild            # Força rebuild (útil após novos testes)"
}

# Variáveis - Reutiliza imagem existente
IMAGE_NAME="tech-challenge-fase-4-api"

# Verifica se Docker está instalado
if ! command -v docker &> /dev/null; then
    echo -e "${RED}❌ Docker não encontrado!${NC}"
    echo "Por favor, instale o Docker: https://docs.docker.com/get-docker/"
    exit 1
fi

# Função para verificar se imagem existe (build se necessário)
check_image() {
    if ! docker images "$IMAGE_NAME" | grep -q "$IMAGE_NAME"; then
        echo -e "${YELLOW}⚠️  Imagem '$IMAGE_NAME' não encontrada${NC}"
        echo ""
        echo -e "${BLUE}🔨 Building imagem via run-mock.sh...${NC}"
        echo ""
        if [ -f "./scripts/run-mock.sh" ]; then
            ./scripts/run-mock.sh --quick
        else
            echo -e "${RED}❌ Script run-mock.sh não encontrado!${NC}"
            exit 1
        fi
    fi

    # Verifica novamente após tentativa de build
    if ! docker images "$IMAGE_NAME" | grep -q "$IMAGE_NAME"; then
        echo -e "${RED}❌ Falha ao buildar imagem!${NC}"
        exit 1
    fi

    echo -e "${GREEN}✅ Usando imagem: $IMAGE_NAME${NC}"
}

# Função para forçar rebuild (quando há novos testes)
force_rebuild() {
    echo -e "${YELLOW}🔄 Forçando rebuild da imagem...${NC}"
    echo -e "${YELLOW}   (Use quando adicionar novos testes ou dependências)${NC}"
    echo ""
    if [ -f "./scripts/run-mock.sh" ]; then
        ./scripts/run-mock.sh --rebuild
    else
        echo -e "${RED}❌ Script run-mock.sh não encontrado!${NC}"
        exit 1
    fi
}

# Função para executar testes unitários
run_unit_tests() {
    check_image
    echo -e "${YELLOW}🧪 Executando testes unitários...${NC}"
    docker run --rm \
        -v "$(pwd)/src:/app/src:ro" \
        -v "$(pwd)/tests:/app/tests:ro" \
        -w /app \
        "$IMAGE_NAME:latest" \
        poetry run pytest tests/unit/ -v
}

# Função para executar testes com cobertura
run_coverage() {
    check_image
    echo -e "${YELLOW}📊 Executando testes com cobertura...${NC}"
    docker run --rm \
        -v "$(pwd)/src:/app/src:ro" \
        -v "$(pwd)/tests:/app/tests:ro" \
        -w /app \
        "$IMAGE_NAME:latest" \
        poetry run pytest tests/unit/ -v --cov=src --cov-report=term
}

# Função para executar testes de integração
run_integration_tests() {
    check_image
    echo -e "${YELLOW}🔗 Executando testes de integração...${NC}"
    echo -e "${YELLOW}   Nota: Certifique-se de que a API está rodando${NC}"
    docker run --rm --network=host \
        -v "$(pwd)/src:/app/src:ro" \
        -v "$(pwd)/tests:/app/tests:ro" \
        -w /app \
        "$IMAGE_NAME:latest" \
        poetry run pytest tests/integration/ -v
}

# Função para executar linting
run_lint() {
    check_image
    echo -e "${YELLOW}🔍 Executando linting (Ruff)...${NC}"
    docker run --rm \
        -v "$(pwd)/src:/app/src:ro" \
        -v "$(pwd)/pyproject.toml:/app/pyproject.toml:ro" \
        -w /app \
        "$IMAGE_NAME:latest" \
        poetry run ruff check src/
    echo -e "${GREEN}✅ Linting passou!${NC}"
}

# Função para executar type checking
run_typecheck() {
    check_image
    echo -e "${YELLOW}🔍 Executando type checking (mypy)...${NC}"
    docker run --rm \
        -v "$(pwd)/src:/app/src:ro" \
        -v "$(pwd)/pyproject.toml:/app/pyproject.toml:ro" \
        -w /app \
        "$IMAGE_NAME:latest" \
        poetry run mypy src/
    echo -e "${GREEN}✅ Type checking passou!${NC}"
}

# Função para executar tudo
run_all() {
    echo -e "${BLUE}🚀 Executando todos os checks...${NC}"
    echo ""
    run_lint
    echo ""
    run_typecheck
    echo ""
    run_coverage
}


# Main
case "${1:-unit}" in
    unit|test)
        run_unit_tests
        ;;
    integration)
        run_integration_tests
        ;;
    coverage)
        run_coverage
        ;;
    lint)
        run_lint
        ;;
    typecheck)
        run_typecheck
        ;;
    all)
        run_all
        ;;
    rebuild)
        force_rebuild
        ;;
    help|--help|-h)
        show_help
        exit 0
        ;;
    *)
        echo -e "${RED}❌ Comando desconhecido: $1${NC}"
        show_help
        exit 1
        ;;
esac

echo ""
echo -e "${GREEN}✅ Done!${NC}"
