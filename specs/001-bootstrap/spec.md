# Feature Specification: Bootstrap do Projeto

**Feature Branch**: `[001-bootstrap]`
**Created**: 2026-04-11
**Status**: ✅ Concluído
**Input**: Setup inicial do projeto Tech Challenge Fase 4

---

## User Scenarios & Testing

### User Story 1 - Estrutura do Projeto (Priority: P1)

Como desenvolvedor, quero uma estrutura de projeto organizada para facilitar o desenvolvimento e manutenção.

**Why this priority**: Base fundamental para todo o desenvolvimento. Sem estrutura adequada, o código se torna difícil de manter.

**Independent Test**: Verificar se a estrutura de pastas existe conforme documentação.

**Acceptance Scenarios**:

1. **Given** o repositório clonado, **When** listo as pastas, **Then** vejo estrutura src/, tests/, docs/
2. **Given** a estrutura criada, **When** executo comandos de build, **Then** funcionam sem erros de path

### User Story 2 - Configuração Poetry (Priority: P1)

Como desenvolvedor, quero dependências gerenciadas pelo Poetry para controle preciso de versões.

**Why this priority**: Gerenciamento de dependências é crítico para reprodutibilidade.

**Independent Test**: `poetry install` executa com sucesso.

**Acceptance Scenarios**:

1. **Given** o arquivo pyproject.toml, **When** executo `poetry install`, **Then** todas dependências são instaladas
2. **Given** ambiente Poetry ativo, **When** importo FastAPI, **Then** funciona sem erro

### User Story 3 - Docker Setup (Priority: P1)

Como desenvolvedor, quero containers Docker configurados para ambiente consistente.

**Why this priority**: Containerização é requisito obrigatório de avaliação (20% da nota).

**Independent Test**: `docker-compose up --build` inicia aplicação.

**Acceptance Scenarios**:

1. **Given** Dockerfile configurado, **When** executo `docker build`, **Then** imagem é criada sem erros
2. **Given** docker-compose.yml, **When** executo `docker-compose up`, **Then** aplicação inicia na porta 8000

---

## Requirements

### Functional Requirements

- **FR-001**: Estrutura de pastas conforme CLAUDE.md
- **FR-002**: Poetry configurado com FastAPI, Uvicorn, Pydantic
- **FR-003**: Dockerfile multi-stage funcional
- **FR-004**: docker-compose.yml com serviço API
- **FR-005**: Arquivo .env.example com variáveis documentadas
- **FR-006**: README inicial com instruções de setup

### Key Entities

- **Projeto**: Estrutura Python com Poetry
- **Container**: Imagem Docker otimizada
- **Config**: Variáveis de ambiente documentadas

---

## Success Criteria

- **SC-001**: `poetry install` completa em menos de 2 minutos
- **SC-002**: `docker-compose up --build` inicia sem erros
- **SC-003**: Estrutura de pastas segue padrões Python
- **SC-004**: README permite setup em menos de 5 minutos

---

## Assumptions

- Python 3.11+ disponível no sistema
- Docker e Docker Compose instalados
- Poetry instalado (`pip install poetry`)
- Azure CLI não é necessário para bootstrap

---

## Edge Cases

### EC-001: Poetry já existe no sistema
**Cenário**: Projeto já foi inicializado anteriormente
**Comportamento**: Sobrescreve pyproject.toml se --force usado, senão mantém existente

### EC-002: Docker não está rodando
**Cenário**: Usuário tenta `docker-compose up` sem Docker daemon
**Comportamento**: Retorna erro claro: "Docker daemon não está disponível"

### EC-003: Porta 8000 ocupada
**Cenário**: Outro serviço usa porta 8000
**Comportamento**: Docker Compose reporta conflito, sugere mudar porta no .env

---

## Technical Notes

### Estrutura Final Esperada
```
tech-challenge-fase-4/
├── src/
│   ├── api/
│   │   ├── main.py
│   │   └── routes/
│   ├── core/
│   ├── models/
│   ├── services/
│   └── infrastructure/
├── tests/
│   ├── unit/
│   └── integration/
├── pyproject.toml
├── Dockerfile
├── docker-compose.yml
├── .env.example
└── README.md
```

### Dependências Obrigatórias (pyproject.toml)
```toml
[tool.poetry.dependencies]
python = "^3.11"
fastapi = "^0.104.0"
uvicorn = {extras = ["standard"], version = "^0.24.0"}
pydantic = {extras = ["settings"], version = "^2.5.0"}
pydantic-settings = "^2.1.0"
python-multipart = "^0.0.6"

[tool.poetry.group.dev.dependencies]
pytest = "^7.4.0"
pytest-asyncio = "^0.21.0"
ruff = "^0.1.6"
mypy = "^1.7.0"
```

### Dockerfile Multi-Stage
```dockerfile
FROM python:3.11-slim as builder
WORKDIR /app
RUN pip install poetry
COPY pyproject.toml poetry.lock ./
RUN poetry export -f requirements.txt --output requirements.txt --without-hashes

FROM python:3.11-slim
WORKDIR /app
RUN useradd -m -u 1000 appuser
COPY --from=builder /app/requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt
COPY src/ ./src/
USER appuser
EXPOSE 8000
CMD ["uvicorn", "src.api.main:app", "--host", "0.0.0.0", "--port", "8000"]
```
