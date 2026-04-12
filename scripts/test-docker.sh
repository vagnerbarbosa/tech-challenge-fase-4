#!/bin/bash
#
# Script para executar testes via Docker
#
# Este script facilita a execução de testes usando Docker, garantindo
# um ambiente Linux consistente mesmo no Windows.
#
# Por que usar Docker para testes?
# - Librosa e python-magic têm dependências nativas complexas
# - Evita segmentation faults no Windows
# - Garante compatibilidade com FFmpeg
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
    echo "  build      - Apenas builda a imagem Docker"
    echo "  clean      - Remove imagens Docker de teste"
    echo "  help       - Mostra esta ajuda"
    echo ""
    echo "Exemplos:"
    echo "  $0                    # Testes unitários"
    echo "  $0 unit               # Testes unitários (explícito)"
    echo "  $0 coverage           # Testes com cobertura"
    echo "  $0 all                # Todos os checks"
}

# Variáveis
IMAGE_NAME="health-api-test"
DOCKERFILE="Dockerfile.test"

# Verifica se Docker está instalado
if ! command -v docker &> /dev/null; then
    echo -e "${RED}❌ Docker não encontrado!${NC}"
    echo "Por favor, instale o Docker: https://docs.docker.com/get-docker/"
    exit 1
fi

# Função para buildar a imagem
build_image() {
    echo -e "${YELLOW}🔨 Buildando imagem Docker...${NC}"
    docker build -f "$DOCKERFILE" -t "$IMAGE_NAME:latest" .
    echo -e "${GREEN}✅ Imagem buildada com sucesso!${NC}"
    echo ""
}

# Função para executar testes unitários
run_unit_tests() {
    echo -e "${YELLOW}🧪 Executando testes unitários...${NC}"
    docker run --rm "$IMAGE_NAME:latest" \
        poetry run pytest tests/unit/ -v
}

# Função para executar testes com cobertura
run_coverage() {
    echo -e "${YELLOW}📊 Executando testes com cobertura...${NC}"
    docker run --rm "$IMAGE_NAME:latest" \
        poetry run pytest tests/unit/ -v --cov=src --cov-report=term
}

# Função para executar testes de integração
run_integration_tests() {
    echo -e "${YELLOW}🔗 Executando testes de integração...${NC}"
    echo -e "${YELLOW}   Nota: Certifique-se de que a API está rodando${NC}"
    docker run --rm --network=host "$IMAGE_NAME:latest" \
        poetry run pytest tests/integration/ -v
}

# Função para executar linting
run_lint() {
    echo -e "${YELLOW}🔍 Executando linting (Ruff)...${NC}"
    docker run --rm "$IMAGE_NAME:latest" \
        poetry run ruff check src/
    echo -e "${GREEN}✅ Linting passou!${NC}"
}

# Função para executar type checking
run_typecheck() {
    echo -e "${YELLOW}🔍 Executando type checking (mypy)...${NC}"
    docker run --rm "$IMAGE_NAME:latest" \
        poetry run mypy src/services/audio_analysis.py
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

# Função para limpar imagens
clean() {
    echo -e "${YELLOW}🧹 Removendo imagens Docker de teste...${NC}"
    docker rmi -f "$IMAGE_NAME:latest" 2>/dev/null || true
    echo -e "${GREEN}✅ Limpo!${NC}"
}

# Main
case "${1:-unit}" in
    unit|test)
        build_image
        run_unit_tests
        ;;
    integration)
        run_integration_tests
        ;;
    coverage)
        build_image
        run_coverage
        ;;
    lint)
        build_image
        run_lint
        ;;
    typecheck)
        build_image
        run_typecheck
        ;;
    all)
        build_image
        run_all
        ;;
    build)
        build_image
        ;;
    clean)
        clean
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
