# CLAUDE.md

Guidance for Claude Code when working with this repository.

## WHAT: Project

**Tech Challenge Fase 4** - FIAP/Alura AI para Devs

Multimodal health analysis API for women's health:
- **Text**: Azure AI Language (sentiment analysis)
- **Audio**: Azure AI Speech (transcription + prosody)
- **Video**: YOLOv8 local detection (instruments, bleeding, posture)
- **Multimodal**: Fusion endpoint (pending)

## Stack

- **Runtime**: Python 3.11+, FastAPI, Pydantic v2
- **AI**: Azure AI Services (Text, Speech, Vision)
- **ML**: YOLOv8 (Ultralytics), OpenCV
- **Infra**: Docker, Docker Compose, Redis (optional)
- **Dev**: Poetry, Ruff (line 88), mypy (strict), pytest

## Project Structure

```
src/
├── api/routes/        # FastAPI endpoints
├── services/          # Business logic
├── core/              # Config, logging, rate limiting
├── infrastructure/    # Azure clients
└── utils/             # Video validation, etc.

tests/
├── unit/              # Service tests
├── integration/       # API endpoint tests
└── load/              # Locust tests
```

## HOW: Essential Commands

### Run
```bash
# Development
poetry run uvicorn src.api.main:app --reload

# Docker
docker-compose up --build -d

# Tests
poetry run pytest -v
poetry run pytest --cov=src --cov-report=html

# Quality
poetry run ruff check . && poetry run mypy src/
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
- Context7 best practices: `docs/technical/context7-best-practices.md`
- GitHub tools strategy: `memory/github_tools_strategy.md`
- Security audit: `docs/technical/security-audit.md`
