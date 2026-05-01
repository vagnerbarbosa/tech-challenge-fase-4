# CLAUDE.md

Guidance for Claude Code when working with this repository.

## WHAT: Project

**Tech Challenge Fase 4** - FIAP/Alura AI para Devs

Multimodal health analysis API for women's health:
- **Text**: Azure AI Language (sentiment analysis)
- **Audio**: Azure AI Speech (transcription + prosody)
- **Video**: YOLOv8 local detection (instruments, bleeding, posture)
- **Multimodal**: Fusion endpoint (late fusion)
- **Security**: OWASP + LGPD compliance (API Key, rate limiting, audit)

### Specification Driven Development (SDD)

Este projeto segue a metodologia **Spec Kit** ([github/spec-kit](https://github.com/github/spec-kit)):

- **specs/**: Especificações detalhadas para cada feature
- **Fases**: Especificar → Planejar → Taskificar → Implementar → Validar
- **Rastreabilidade**: Cada feature tem ID (001-011) e spec documentada
- **Constitution**: Regras em `.specify/memory/constitution.md`

## Stack

- **Runtime**: Python 3.11+, FastAPI, Pydantic v2
- **AI**: Azure AI Services (Text, Speech, Vision)
- **ML**: YOLOv8 (Ultralytics), OpenCV
- **Infra**: Docker, Docker Compose, Redis (optional)
- **Dev**: Poetry, Ruff (line 88), mypy (strict), pytest

## Project Structure

```
src/
├── api/
│   ├── routes/        # FastAPI endpoints (text, audio, video, multimodal, auth, admin)
│   ├── middleware/    # Security middleware (CORS, headers, rate limit)
│   └── dependencies.py # FastAPI dependencies (auth, rate limit)
├── services/          # Business logic (analysis + fusion)
├── core/
│   ├── security/      # Auth, rate limiter, file validator, log sanitizer
│   ├── config.py      # Settings including SecurityConfig
│   ├── rate_limit.py  # QuotaManager for Azure Free Tier
│   └── logging_config.py # Structured logging with sanitization
├── infrastructure/    # Azure clients
└── utils/             # Audit logger, file validation

tests/
├── unit/              # Service tests
├── integration/       # API endpoint tests
├── security/          # Security-specific tests (Spec 007)
└── load/              # Locust tests
```

## HOW: Essential Commands

### Run
```bash
# Development
poetry run uvicorn src.api.main:app --reload

# Docker
docker-compose up --build -d

# Docker Mock Mode (Azure mocks local)
./scripts/run-mock.sh              # Padrão: sobe com build se necessário
./scripts/run-mock.sh --quick      # Rápido: recria containers, reusa imagem
./scripts/run-mock.sh --rebuild    # Lento: rebuilda imagem do zero

# Tests
poetry run pytest -v
poetry run pytest --cov=src --cov-report=html

# Quality
poetry run ruff check . && poetry run mypy src/
```

### Docker Mock Mode Options

O script `./scripts/run-mock.sh` gerencia containers Docker para desenvolvimento com mocks Azure:

| Opção | Quando usar | Tempo | O que faz |
|-------|-------------|-------|-----------|
| `--quick` | Atualizar env vars (Spec 007) | ~5s | Recria containers, aplica novas env vars, **reusa imagem existente** |
| `--rebuild` | Mudou Dockerfile/deps | ~5min | Remove e rebuilda imagem do zero |
| (sem flag) | Primeira vez | ~1min | Build se necessário, sobe containers |

**Por que `--quick` funciona:**
- O `docker-compose.mock.yml` monta código local via volume (`./src:/app/src`)
- Uvicorn roda com `--reload`, então código atualiza automaticamente
- `--quick` usa `--force-recreate` para aplicar novas env vars sem rebuild

**Exemplo de uso com Spec 007:**
```bash
# 1. Atualize o docker-compose.mock.yml com novas env vars de segurança
# 2. Aplique as mudanças rapidamente:
./scripts/run-mock.sh --quick

# 3. Verifique se as variáveis foram aplicadas:
docker compose -f docker-compose.mock.yml exec api env | grep SECURITY
```

## Critical Constraints

### MUST
- ✅ Fields in ALL responses: `risco_violencia`, `risco_saude_mental`
- ✅ Azure Free Tier quotas protected (hard stop when exceeded)
- ✅ LGPD: anonymize PII, consent required, temp files cleaned
- ✅ YOLOv8 local for video (no Azure quota consumption)

### MUST NOT
- ❌ Exceed Azure Free Tier (5K text/mo, 5hr audio/mo, 5K vision/mo)
- ❌ Commit secrets (use .env)
- ❌ Log media content

## MCP Servers

Configured in `.mcp.json`:
- **GitHub MCP**: `npx -y @modelcontextprotocol/server-github`
- **Context7 MCP**: `npx -y @upstash/context7-mcp@latest`

Requires: `export GITHUB_TOKEN=ghp_your_token`

## Conventions

- **Code**: English (variables, functions, classes)
- **Docstrings**: Portuguese (Brazilian context) - todas as docstrings de módulos, classes e funções devem estar em português
- **Docs**: Portuguese (Brazilian context)
- **Commits**: Conventional commits (`feat:`, `fix:`, `docs:`)
- **Types**: Mandatory type hints on public APIs
- **Testing**: Tests for all new code

## References

- Full architecture: `docs/architecture.md`
- API contracts: `docs/api-contracts.md`
- Project status: `docs/PROJECT_STATUS.md`
- Security guide: `docs/technical/security-guide.md`
- Context7 best practices: `docs/technical/context7-best-practices.md`
- GitHub tools strategy: `memory/github_tools_strategy.md`
