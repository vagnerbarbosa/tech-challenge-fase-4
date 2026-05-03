#!/bin/bash
#
# Script para executar testes E2E (End-to-End)
#
# Este script automatiza a execução dos testes E2E, gerenciando
# o ciclo de vida dos containers Docker necessários.
#
# Uso: ./scripts/run-e2e.sh [opções]
#

set -e

# Cores para output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Diretório base
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(dirname "$SCRIPT_DIR")"
E2E_DIR="$PROJECT_ROOT/tests/e2e"
COMPOSE_FILE="$E2E_DIR/fixtures/docker-compose.e2e.yml"

# Função de ajuda
show_help() {
    echo "Uso: $0 [opção]"
    echo ""
    echo "Opções disponíveis:"
    echo "  (sem opção)  - Executa os testes E2E completos"
    echo "  --logs       - Mostra logs dos containers após execução"
    echo "  --stop       - Para os containers E2E (útil para limpeza)"
    echo "  --rebuild    - Força rebuild da imagem E2E"
    echo "  --help       - Mostra esta ajuda"
    echo ""
    echo "Exemplos:"
    echo "  $0                    # Executa testes E2E"
    echo "  $0 --logs             # Executa e mostra logs"
    echo "  $0 --stop             # Para containers E2E"
    echo "  $0 --rebuild          # Rebuild e executa"
    echo ""
    echo "Pré-requisitos:"
    echo "  - Docker e Docker Compose instalados"
    echo "  - Poetry instalado (para executar pytest)"
}

# Verifica dependências
check_dependencies() {
    if ! command -v docker &> /dev/null; then
        echo -e "${RED}❌ Docker não encontrado!${NC}"
        echo "Instale o Docker: https://docs.docker.com/get-docker/"
        exit 1
    fi

    if ! command -v poetry &> /dev/null; then
        echo -e "${RED}❌ Poetry não encontrado!${NC}"
        echo "Instale o Poetry: curl -sSL https://install.python-poetry.org | python3 -"
        exit 1
    fi
}

# Para containers E2E
stop_e2e() {
    echo -e "${BLUE}🛑 Parando containers E2E...${NC}"
    cd "$E2E_DIR/fixtures"
    docker compose -f docker-compose.e2e.yml down -v 2>/dev/null || true
    echo -e "${GREEN}✅ Containers E2E parados${NC}"
}

# Aguarda API ficar pronta
wait_for_api() {
    local max_attempts=30
    local attempt=1

    echo -e "${BLUE}⏳ Aguardando API E2E ficar pronta...${NC}"

    while [ $attempt -le $max_attempts ]; do
        if curl -s -f http://localhost:9000/health > /dev/null 2>&1; then
            echo -e "${GREEN}✅ API E2E pronta!${NC}"
            return 0
        fi

        echo -e "${YELLOW}   Tentativa $attempt/$max_attempts...${NC}"
        sleep 2
        attempt=$((attempt + 1))
    done

    echo -e "${RED}❌ API E2E não respondeu após $max_attempts tentativas${NC}"
    return 1
}

# Executa testes E2E
run_tests() {
    echo -e "${BLUE}🧪 Executando testes E2E...${NC}"
    echo ""

    cd "$PROJECT_ROOT"
    poetry run pytest tests/e2e/ -v --tb=short

    return $?
}

# Mostra logs
show_logs() {
    echo ""
    echo -e "${BLUE}📋 Logs do container API E2E:${NC}"
    cd "$E2E_DIR/fixtures"
    docker compose -f docker-compose.e2e.yml logs api-e2e --tail 50 || true
}

# Main execution
main() {
    echo -e "${BLUE}========================================${NC}"
    echo -e "${BLUE}  Testes E2E - Multimodal Health API  ${NC}"
    echo -e "${BLUE}========================================${NC}"
    echo ""

    case "${1:-}" in
        --help|-h)
            show_help
            exit 0
            ;;
        --stop)
            stop_e2e
            exit 0
            ;;
        --logs)
            SHOW_LOGS=true
            ;;
        --rebuild)
            REBUILD=true
            ;;
        "")
            # Continue with default execution
            ;;
        *)
            echo -e "${RED}❌ Opção desconhecida: $1${NC}"
            show_help
            exit 1
            ;;
    esac

    # Verifica dependências
    check_dependencies

    # Para containers anteriores se existirem
    stop_e2e

    # Inicia containers E2E
    echo -e "${BLUE}🚀 Iniciando ambiente E2E...${NC}"
    cd "$E2E_DIR/fixtures"

    if [ "${REBUILD:-false}" = true ]; then
        docker compose -f docker-compose.e2e.yml up --build -d
    else
        docker compose -f docker-compose.e2e.yml up -d
    fi

    # Aguarda API
    if ! wait_for_api; then
        echo -e "${RED}❌ Falha ao iniciar API E2E${NC}"
        show_logs
        stop_e2e
        exit 1
    fi

    # Executa testes
    TEST_EXIT_CODE=0
    if ! run_tests; then
        TEST_EXIT_CODE=1
    fi

    # Mostra logs se solicitado ou se falhou
    if [ "${SHOW_LOGS:-false}" = true ] || [ $TEST_EXIT_CODE -ne 0 ]; then
        show_logs
    fi

    # Limpa containers
    echo ""
    echo -e "${BLUE}🧹 Limpando containers...${NC}"
    stop_e2e

    # Resultado final
    echo ""
    if [ $TEST_EXIT_CODE -eq 0 ]; then
        echo -e "${GREEN}========================================${NC}"
        echo -e "${GREEN}  ✅ Testes E2E passaram!            ${NC}"
        echo -e "${GREEN}========================================${NC}"
    else
        echo -e "${RED}========================================${NC}"
        echo -e "${RED}  ❌ Testes E2E falharam            ${NC}"
        echo -e "${RED}========================================${NC}"
    fi

    exit $TEST_EXIT_CODE
}

# Executa main
main "$@"
