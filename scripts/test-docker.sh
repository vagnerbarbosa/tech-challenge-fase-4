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
    echo "  all        - Executa lint + typecheck + unit tests (instala deps uma vez)"
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
    echo "  $0 all                # Todos os checks (deps instaladas uma vez)"
    echo "  $0 rebuild            # Força rebuild (útil após novos testes)"
}

# Variáveis - Reutiliza imagem existente
IMAGE_NAME="tech-challenge-fase-4-api"

# Array para armazenar resultados
declare -A RESULTS

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

# Função para filtrar warnings do poetry
filter_poetry_warnings() {
    grep -v "^WARNING: This output is designed for human readability" | \
    grep -v "^Skipping virtualenv creation" | \
    grep -v "^Package operations:" | \
    grep -v "^- Installing" | \
    cat
}

# Função para executar testes unitários
run_unit_tests() {
    check_image
    echo -e "${YELLOW}🧪 Executando testes unitários...${NC}"
    docker run --rm \
        -v "$(pwd)/src:/app/src:ro" \
        -v "$(pwd)/tests:/app/tests:ro" \
        -v "$(pwd)/pyproject.toml:/app/pyproject.toml:ro" \
        -w /app \
        "$IMAGE_NAME:latest" \
        bash -c "poetry install --with dev --no-interaction --no-root 2>/dev/null && poetry run pytest tests/unit/ -v" 2>&1 | filter_poetry_warnings
}

# Função para executar testes com cobertura
run_coverage() {
    check_image
    echo -e "${YELLOW}📊 Executando testes com cobertura...${NC}"
    docker run --rm \
        -v "$(pwd)/src:/app/src:ro" \
        -v "$(pwd)/tests:/app/tests:ro" \
        -v "$(pwd)/pyproject.toml:/app/pyproject.toml:ro" \
        -w /app \
        "$IMAGE_NAME:latest" \
        bash -c "poetry install --with dev --no-interaction --no-root 2>/dev/null && poetry run pytest tests/unit/ -v --cov=src --cov-report=term" 2>&1 | filter_poetry_warnings
}

# Função para executar testes de integração
run_integration_tests() {
    check_image
    echo -e "${YELLOW}🔗 Executando testes de integração...${NC}"
    echo -e "${YELLOW}   Nota: Certifique-se de que a API está rodando${NC}"
    docker run --rm --network=host \
        -v "$(pwd)/src:/app/src:ro" \
        -v "$(pwd)/tests:/app/tests:ro" \
        -v "$(pwd)/pyproject.toml:/app/pyproject.toml:ro" \
        -w /app \
        "$IMAGE_NAME:latest" \
        bash -c "poetry install --with dev --no-interaction --no-root 2>/dev/null && poetry run pytest tests/integration/ -v" 2>&1 | filter_poetry_warnings
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
        bash -c "poetry install --with dev --no-interaction --no-root 2>/dev/null && poetry run ruff check src/" 2>&1 | filter_poetry_warnings
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
        bash -c "poetry install --with dev --no-interaction --no-root 2>/dev/null && poetry run mypy src/" 2>&1 | filter_poetry_warnings
    echo -e "${GREEN}✅ Type checking passou!${NC}"
}

# Função para executar tudo em um único container (deps instaladas uma vez)
run_all_optimized() {
    check_image
    echo -e "${BLUE}🚀 Executando todos os checks (modo otimizado)...${NC}"
    echo -e "${BLUE}   Dependências serão instaladas uma única vez${NC}"
    echo ""

    # Cria script temporário que executa todos os checks
    TEMP_SCRIPT=$(mktemp)
    cat > "$TEMP_SCRIPT" << 'CHECKS_SCRIPT'
#!/bin/bash
set -e

echo "📦 Instalando dependências (apenas uma vez)..."
poetry install --with dev --no-interaction --no-root > /dev/null 2>&1
echo "✅ Dependências instaladas!"
echo ""

# Array para resultados
declare -A RESULTS

# Lint
echo "🔍 Executando lint (Ruff)..."
poetry run ruff check src/ > /tmp/lint-output.txt 2>&1
LINT_EXIT=$?
grep -v "^WARNING:" /tmp/lint-output.txt | grep -v "^Skipping" || true
if [ $LINT_EXIT -eq 0 ]; then
    RESULTS["Lint"]="✅ PASS"
    echo "✅ Lint passou!"
else
    RESULTS["Lint"]="❌ FAIL"
    echo "❌ Lint falhou!"
fi
echo ""

# Typecheck
echo "🔍 Executando type check (mypy)..."
poetry run mypy src/ > /tmp/mypy-output.txt 2>&1
MYPY_EXIT=$?
grep -v "^WARNING:" /tmp/mypy-output.txt | grep -v "^Skipping" || true
if [ $MYPY_EXIT -eq 0 ]; then
    RESULTS["Typecheck"]="✅ PASS"
    echo "✅ Type check passou!"
else
    RESULTS["Typecheck"]="❌ FAIL"
    echo "❌ Type check falhou!"
fi
echo ""

# Tests with coverage
echo "🧪 Executando testes com cobertura..."
poetry run pytest tests/unit/ -v --cov=src --cov-report=term > /tmp/pytest-output.txt 2>&1
PYTEST_EXIT=$?
cat /tmp/pytest-output.txt | grep -v "^WARNING:" | grep -v "^Skipping" || true
if [ $PYTEST_EXIT -eq 0 ]; then
    RESULTS["Coverage"]="✅ PASS"
    echo "✅ Testes passaram!"
else
    RESULTS["Coverage"]="❌ FAIL"
    echo "❌ Testes falharam (coverage ou testes)!"
fi
echo ""

# Relatório final
echo "========================================"
echo "           RELATÓRIO FINAL            "
echo "========================================"
echo ""
echo "🔍 Lint (Ruff): ${RESULTS["Lint"]}"
echo "🔍 Type Check (mypy): ${RESULTS["Typecheck"]}"
echo "📊 Tests with Coverage: ${RESULTS["Coverage"]}"
echo ""

# Verifica se todos passaram
if [ "${RESULTS["Lint"]}" = "✅ PASS" ] && [ "${RESULTS["Typecheck"]}" = "✅ PASS" ] && [ "${RESULTS["Coverage"]}" = "✅ PASS" ]; then
    echo "✅ Todos os checks passaram! (3/3)"
    exit 0
else
    echo "❌ Alguns checks falharam!"
    exit 1
fi
CHECKS_SCRIPT

    # Executa script no container
    docker run --rm \
        -v "$(pwd)/src:/app/src:ro" \
        -v "$(pwd)/tests:/app/tests:ro" \
        -v "$(pwd)/pyproject.toml:/app/pyproject.toml:ro" \
        -v "$TEMP_SCRIPT:/tmp/run-checks.sh:ro" \
        -w /app \
        "$IMAGE_NAME:latest" \
        bash /tmp/run-checks.sh

    RESULT=$?
    rm -f "$TEMP_SCRIPT"
    return $RESULT
}

# Função para executar tudo (modo antigo - individual)
run_all_individual() {
    echo -e "${BLUE}🚀 Executando todos os checks (modo individual)...${NC}"
    echo ""

    local exit_code=0

    run_lint || exit_code=1
    echo ""

    run_typecheck || exit_code=1
    echo ""

    run_coverage || exit_code=1

    return $exit_code
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
        run_all_optimized
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
