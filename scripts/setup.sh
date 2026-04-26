#!/bin/bash
# ===========================================
# Script de Setup Inicial - Multi-plataforma
# Tech Challenge Fase 4
# Funciona em: Linux (Ubuntu/Debian/Fedora/Arch), macOS, Windows (WSL)
# ===========================================

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
IS_WSL=false
[[ "$OS" == "linux-wsl" ]] && IS_WSL=true

# ============================================
# CONFIGURAÇÕES POR SO
# ============================================
setup_vars() {
    case "$OS" in
        linux|linux-wsl)
            USER_BIN="$HOME/.local/bin"
            POETRY_BIN="$HOME/.local/share/pypoetry/bin"
            SHELL_RC="$HOME/.bashrc"
            [[ -f "$HOME/.zshrc" ]] && SHELL_RC="$HOME/.zshrc"
            ;;
        macos)
            USER_BIN="$HOME/.local/bin"
            POETRY_BIN="$HOME/.local/share/pypoetry/bin"
            SHELL_RC="$HOME/.zshrc"
            [[ -f "$SHELL_RC" ]] || SHELL_RC="$HOME/.bashrc"
            ;;
        *)
            echo "Sistema operacional não suportado: $(uname -s)"
            exit 1
            ;;
    esac
}

# ============================================
# UTILITÁRIOS DE OUTPUT
# ============================================
setup_colors() {
    if [[ -t 1 ]]; then
        GREEN='\033[0;32m'
        YELLOW='\033[1;33m'
        RED='\033[0;31m'
        BLUE='\033[0;34m'
        NC='\033[0m'
    else
        GREEN='' YELLOW='' RED='' BLUE='' NC=''
    fi
}

log_info() { echo -e "${BLUE}ℹ️  $1${NC}"; }
log_success() { echo -e "${GREEN}✅ $1${NC}"; }
log_warn() { echo -e "${YELLOW}⚠️  $1${NC}"; }
log_error() { echo -e "${RED}❌ $1${NC}"; }
log_step() { echo -e "\n${BLUE}🚀 $1${NC}"; }

command_exists() { command -v "$1" &> /dev/null; }

# ============================================
# 1. CONFIGURAR PATH E DIRETÓRIOS
# ============================================
setup_path() {
    log_step "Configurando PATH..."

    mkdir -p "$USER_BIN"

    # Adicionar ao shell rc
    if [[ -f "$SHELL_RC" ]] && ! grep -q "$USER_BIN" "$SHELL_RC" 2>/dev/null; then
        echo "" >> "$SHELL_RC"
        echo '# Tech Challenge - PATH' >> "$SHELL_RC"
        echo "export PATH=\"$USER_BIN:\$PATH\"" >> "$SHELL_RC"
        log_success "$USER_BIN adicionado ao PATH"
    fi
}

# ============================================
# 2. VERIFICAR PYTHON 3.11+
# ============================================
check_python() {
    log_step "Verificando Python 3.11+..."

    if ! command_exists python3; then
        log_error "Python3 não encontrado. Por favor, instale Python 3.11+"
        exit 1
    fi

    python_version=$(python3 --version 2>&1 | grep -oP '\d+\.\d+' || echo "0.0")
    required_version="3.11"

    if [ "$(printf '%s\n' "$required_version" "$python_version" | sort -V | head -n1)" != "$required_version" ]; then
        log_error "Python 3.11+ é obrigatório. Versão encontrada: $python_version"
        exit 1
    fi

    log_success "Python $python_version encontrado"
}

# ============================================
# 3. INSTALAR POETRY
# ============================================
install_poetry() {
    log_step "Verificando Poetry..."

    if command_exists poetry; then
        log_success "Poetry já instalado: $(poetry --version)"
        return
    fi

    log_info "Instalando Poetry..."
    curl -sSL https://install.python-poetry.org | python3 -

    # Adicionar ao PATH no shell rc
    if [[ -f "$SHELL_RC" ]] && ! grep -q 'pypoetry' "$SHELL_RC" 2>/dev/null; then
        echo '' >> "$SHELL_RC"
        echo '# Poetry' >> "$SHELL_RC"
        echo "export PATH=\"$POETRY_BIN:\$PATH\"" >> "$SHELL_RC"
    fi

    # Exportar para sessão atual
    export PATH="$POETRY_BIN:$PATH"

    log_success "Poetry instalado: $(poetry --version)"
}

# ============================================
# 4. INSTALAR NODE.JS (para MCP servers)
# ============================================
install_nodejs() {
    log_step "Verificando Node.js..."

    if command_exists node; then
        log_success "Node.js já instalado: $(node --version)"
        return
    fi

    log_info "Instalando Node.js 20.x LTS..."

    case "$OS" in
        linux|linux-wsl)
            if command_exists apt; then
                # Ubuntu/Debian
                curl -fsSL https://deb.nodesource.com/setup_20.x | sudo bash -
                sudo apt-get install -y nodejs
            elif command_exists dnf; then
                sudo dnf install -y nodejs
            elif command_exists pacman; then
                sudo pacman -S nodejs npm
            else
                install_nvm_node
            fi
            ;;
        macos)
            if command_exists brew; then
                brew install node@20
            else
                log_info "Instalando Homebrew..."
                /bin/bash -c "$(curl -fsSL https://raw.githubusercontent.com/Homebrew/install/HEAD/install.sh)"
                brew install node@20
            fi
            ;;
    esac

    if command_exists node; then
        log_success "Node.js instalado: $(node --version)"
    else
        log_warn "Node.js não pôde ser instalado automaticamente"
    fi
}

install_nvm_node() {
    log_info "Usando NVM para instalar Node.js..."
    if [[ ! -d "$HOME/.nvm" ]]; then
        curl -o- https://raw.githubusercontent.com/nvm-sh/nvm/v0.39.7/install.sh | bash
        export NVM_DIR="$HOME/.nvm"
        [ -s "$NVM_DIR/nvm.sh" ] && \. "$NVM_DIR/nvm.sh"
    fi
    nvm install 20
    nvm use 20
}

# ============================================
# 5. CONFIGURAR RUST/CARGO
# ============================================
setup_rust() {
    log_step "Configurando Rust/Cargo..."

    if [[ -d "$HOME/.cargo" ]]; then
        if [[ -f "$SHELL_RC" ]] && ! grep -q '.cargo/env' "$SHELL_RC" 2>/dev/null; then
            echo '' >> "$SHELL_RC"
            echo '# Rust/Cargo' >> "$SHELL_RC"
            echo '[ -f "$HOME/.cargo/env" ] && source "$HOME/.cargo/env"' >> "$SHELL_RC"
            log_success "Cargo adicionado ao PATH"
        else
            log_success "Cargo já configurado"
        fi
    else
        log_info "Rust não encontrado. Instale via: https://rustup.rs/"
    fi
}

# ============================================
# 6. INSTALAR FERRAMENTAS PYTHON
# ============================================
install_python_tools() {
    log_step "Instalando ferramentas de desenvolvimento..."

    # Ferramentas essenciais do projeto
    local tools=("pre-commit" "bandit" "mkdocs")

    for tool in "${tools[@]}"; do
        if command_exists "$tool"; then
            log_success "$tool já instalado"
        else
            log_info "Instalando $tool..."
            python3 -m pip install "$tool" --user 2>/dev/null || \
                pip3 install "$tool" --user 2>/dev/null || \
                log_warn "Não foi possível instalar $tool"
        fi
    done
}

# ============================================
# 7. INSTALAR DEPENDÊNCIAS DO PROJETO
# ============================================
install_project_deps() {
    log_step "Instalando dependências do projeto..."

    # Garantir que Poetry está no PATH
    export PATH="$POETRY_BIN:$PATH"

    if command_exists poetry; then
        poetry install --with dev
        log_success "Dependências instaladas via Poetry"
    else
        log_error "Poetry não encontrado. Não foi possível instalar dependências."
        exit 1
    fi
}

# ============================================
# 8. CONFIGURAR AMBIENTE
# ============================================
setup_environment() {
    log_step "Configurando ambiente..."

    # Criar .env se não existir
    if [ ! -f .env ]; then
        if [ -f .env.example ]; then
            log_info "Criando arquivo .env a partir de .env.example..."
            cp .env.example .env
            log_warn "Por favor, edite o arquivo .env com suas credenciais Azure"
        else
            log_warn "Arquivo .env.example não encontrado. Crie o .env manualmente."
        fi
    else
        log_success "Arquivo .env já existe"
    fi

    # Criar diretórios de dados
    mkdir -p data logs uploads
    log_success "Diretórios de dados criados (data/, logs/, uploads/)"

    # Configurar Docker no shell rc
    if [[ -f "$SHELL_RC" ]] && ! grep -q 'DOCKER_TMPDIR' "$SHELL_RC" 2>/dev/null; then
        echo '' >> "$SHELL_RC"
        echo '# Docker Configuration' >> "$SHELL_RC"
        echo 'export DOCKER_TMPDIR=${DOCKER_TMPDIR:-/tmp/docker}' >> "$SHELL_RC"
        echo 'export BUILDX_CONFIG=${BUILDX_CONFIG:-~/.docker/buildx}' >> "$SHELL_RC"
    fi
}

# ============================================
# 9. RESUMO FINAL
# ============================================
show_summary() {
    echo ""
    echo "==============================================="
    log_success "Setup completo!"
    echo "==============================================="
    echo ""
    echo "Sistema: $OS"
    [[ "$IS_WSL" == true ]] && echo "Modo: WSL"
    echo ""

    # Status das ferramentas
    echo "Ferramentas instaladas:"
    command_exists python3 && echo "  • Python: $(python3 --version)"
    command_exists poetry && echo "  • Poetry: $(poetry --version 2>/dev/null | head -1)"
    command_exists node && echo "  • Node.js: $(node --version)"
    command_exists npm && echo "  • NPM: $(npm --version)"
    command_exists pre-commit && echo "  • Pre-commit: $(pre-commit --version 2>/dev/null | awk '{print $2}')"
    command_exists bandit && echo "  • Bandit: $(bandit --version 2>/dev/null | head -1)"

    echo ""
    echo "Próximos passos:"
    echo "  1. Aplique as mudanças de PATH:"
    echo -e "     ${YELLOW}source $SHELL_RC${NC}"
    echo ""
    echo "  2. Edite o arquivo .env com suas credenciais Azure"
    echo ""
    echo "  3. Ative o ambiente Poetry:"
    echo -e "     ${YELLOW}poetry shell${NC}"
    echo ""
    echo "  4. Execute a aplicação:"
    echo -e "     ${YELLOW}poetry run uvicorn src.api.main:app --reload${NC}"
    echo ""
    echo "  Ou use Docker:"
    echo -e "     ${YELLOW}docker-compose up --build${NC}"
    echo ""
}

# ============================================
# EXECUÇÃO PRINCIPAL
# ============================================
main() {
    echo "==============================================="
    echo "  Tech Challenge Fase 4 - Setup"
    echo "  Multi-plataforma: Linux | macOS | WSL"
    echo "==============================================="
    echo ""

    setup_vars
    setup_colors

    # Verificar root (não necessário)
    if [[ "$EUID" -eq 0 ]] && [[ "$IS_WSL" == false ]]; then
        log_warn "Este script não precisa ser executado como root"
    fi

    # Execução em sequência
    setup_path
    check_python
    install_poetry
    install_nodejs
    setup_rust
    install_python_tools
    install_project_deps
    setup_environment

    show_summary
}

# Executar
main
