# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview - CORRIGIDO

- **Name**: tech-challenge-fase-4
- **Full Name**: Tech Challenge Fase 4 - FIAP/Alura AI para Devs
- **Language**: Python 3.11+
- **Framework**: FastAPI
- **License**: MIT License (Copyright 2026 Equipe Tech Challenge)
- **Stage**: SDD Foundation Complete - Ready for Bootstrap

### Objective Principal (Do PDF Oficial)

**"Realizar a análise e fusão de diferentes tipos de dados médicos específicos da saúde da mulher — incluindo texto, áudio e vídeo."**

### Opções Selecionadas:
1. ✅ **Detectar precocemente riscos em saúde materna e ginecológica**
2. ✅ **Identificar sinais de violência doméstica ou abuso**
4. ✅ **Utilizar serviços em nuvem** (Azure Free Tier)

### Foco do Projeto:
Sistema **multimodal** para identificação de:
- Sinais de violência doméstica
- Riscos em saúde mental feminina
- Indicadores em gestantes

### Modalidades de Dados:
- 📝 **Texto**: Prontuários, diários, relatos
- 🎙️ **Áudio**: Consultas de telemedicina (voz)
- 🎥 **Imagem/Vídeo**: Expressões faciais, sinais visuais

---

## Critical Requirements (From Official Brief)

### Modalidades Obrigatórias:
- ✅ **Texto** (Azure Text Analytics)
- ✅ **Áudio** (Azure Speech Services)
- ✅ **Imagem/Vídeo** (Azure Computer Vision)
- ✅ **Fusão multimodal** (combinação das 3)

### Azure Free Tier Limits:
- Text Analytics: 5,000 requests/mês
- Speech Services: 5 hours áudio/mês
- Computer Vision: 5,000 transactions/mês
- Blob Storage: 5GB

### Required Deliverables:
1. API REST multimodal (`/analyze/text`, `/analyze/audio`, `/analyze/image`, `/analyze/multimodal`)
2. Integração com Azure Cognitive Services
3. Swagger/OpenAPI documentation em `/docs`
4. Dockerfile (multi-stage)
5. docker-compose.yml
6. Testes unitários + integração + carga (Locust)
7. Cobertura de testes > 70%
8. README completo com exemplos
9. Vídeo demonstrativo (YouTube)

---

## Technology Stack

### Core:
- **Framework**: FastAPI (async, OpenAPI auto)
- **Server**: Uvicorn
- **Validation**: Pydantic v2
- **Config**: Pydantic Settings

### Azure Cognitive Services:
- **Azure AI Text Analytics**: Análise de sentimento, NLP
- **Azure Speech Services**: Speech-to-text, análise de voz
- **Azure Computer Vision**: Análise de imagem, expressões faciais
- **Azure Blob Storage**: Armazenamento temporário de arquivos

### Infrastructure:
- **Container**: Docker + Docker Compose
- **Database**: Azure SQL (opcional) ou SQLite (dev)
- **Cache**: Redis (opcional, para rate limiting)

### Development:
- **Package Manager**: Poetry (pyproject.toml)
- **Linter**: Ruff (line length: 88)
- **Type Checker**: mypy (strict mode)
- **Test Framework**: pytest + httpx + pytest-asyncio
- **Load Testing**: Locust

---

## Project Structure

```
tech-challenge-fase-4/
├── docs/                       # SDD Documentation
│   ├── product-spec.md         # Requisitos funcionais
│   ├── user-stories.md         # Histórias (10 total)
│   ├── architecture.md         # Diagramas e fluxos
│   ├── api-contracts.md        # OpenAPI specs
│   ├── objectives.md            # Objetivo do projeto
│   └── technical/
│       └── cloud-free-tier-analysis.md  # Análise Azure
├── src/                        # Source code
│   ├── api/                    # FastAPI app, routes
│   │   ├── main.py
│   │   └── routes/
│   │       ├── health.py
│   │       ├── text.py
│   │       ├── audio.py
│   │       ├── image.py
│   │       └── multimodal.py
│   ├── core/                   # Config, logging, exceptions
│   │   ├── config.py
│   │   ├── logging_config.py
│   │   ├── exceptions.py
│   │   └── rate_limit.py      # Azure quota management
│   ├── services/               # Business logic
│   │   ├── text_analysis.py
│   │   ├── audio_analysis.py
│   │   ├── image_analysis.py
│   │   └── fusion.py           # Multimodal fusion
│   ├── models/                 # Pydantic schemas
│   │   └── schemas.py
│   ├── infrastructure/         # Azure clients
│   │   └── azure_clients.py
│   └── utils/                  # Helpers
├── tests/                      # Test suite
│   ├── unit/
│   ├── integration/
│   └── load/
│       └── locustfile.py
├── scripts/                    # Dev scripts
├── .claude/                    # Claude context
├── tasks/                      # SDD tasks
│   └── 001-bootstrap.md
├── pyproject.toml              # Poetry config
├── Dockerfile
├── docker-compose.yml
└── README.md                   # Main documentation
```

---

## Development Commands

### Setup:
```bash
# Install dependencies
poetry install

# Activate shell
poetry shell

# Configure Azure credentials
# Criar .env baseado em .env.example
```

### Run Application:
```bash
# Development (hot reload)
poetry run uvicorn src.api.main:app --reload

# Production
poetry run uvicorn src.api.main:app --host 0.0.0.0 --port 8000

# With Docker
docker-compose up --build -d
```

### Quality Checks:
```bash
# Linting
poetry run ruff check .
poetry run ruff check --fix .
poetry run ruff format .

# Type checking
poetry run mypy src/

# Tests
poetry run pytest -v
poetry run pytest --cov=src --cov-report=html

# All checks
poetry run ruff check . && poetry run mypy src/ && poetry run pytest -v
```

### Docker Commands:
```bash
# Build and run
docker-compose up --build -d

# View logs
docker-compose logs -f api

# Stop
docker-compose down -v

# Rebuild from scratch
docker-compose down -v
docker-compose build --no-cache
docker-compose up -d
```

### Test API:
```bash
# Health check
curl http://localhost:8000/health

# Análise de texto
curl -X POST http://localhost:8000/analyze/text \
  -H "Content-Type: application/json" \
  -d '{"texto":"Estou me sentindo ansiosa e com medo"}'

# Análise multimodal (com arquivo)
curl -X POST http://localhost:8000/analyze/multimodal \
  -F "texto=Texto aqui..." \
  -F "audio=@consulta.wav" \
  -F "imagem=@foto.jpg"

# Swagger UI
open http://localhost:8000/docs
```

---

## Evaluation Criteria (Weight)

1. **Funcionalidade (30%)**: API multimodal funciona, integração Azure, fusão de dados
2. **Código (25%)**: Organização, clean code, type hints, Ruff/mypy pass
3. **Containerização (20%)**: Dockerfile, docker-compose, multi-stage, non-root
4. **Testes (15%)**: Unit + integration + load tests, >70% coverage
5. **Documentação (10%)**: README completo, vídeo demonstrativo

---

## Critical Constraints

### MUST HAVE:
- ✅ Processar texto (Azure Text Analytics)
- ✅ Processar áudio (Azure Speech Services)
- ✅ Processar imagem (Azure Computer Vision)
- ✅ Fusão multimodal (combinação de 3)
- ✅ **Campos obrigatórios em TODAS respostas**: `risco_violencia` e `risco_saude_mental`
- ✅ Azure Free Tier (custo zero)
- ✅ Docker funciona com `docker-compose up`
- ✅ Swagger em `/docs`
- ✅ LGPD compliance (anonimização, consentimento)

### MUST NOT:
- ❌ Exceder quotas do Azure Free Tier
- ❌ Armazenar dados pessoais identificáveis
- ❌ Processar sem consentimento explícito
- ❌ Expor secrets Azure no código
- ❌ Logar conteúdo de arquivos de mídia

---

## Azure Free Tier - Gestão

### Limites e Proteção:
```python
RATE_LIMITS = {
    "text_analytics": {"daily": 160, "monthly": 5000},
    "speech": {"daily_minutes": 10, "monthly_minutes": 300},
    "computer_vision": {"daily": 160, "monthly": 5000}
}
```

### Monitoramento:
- Health check mostra quota restante
- Rate limiting por endpoint
- Cache para evitar reprocessamento

---

## Next Steps (Tasks)

1. **001-bootstrap**: Project structure, Poetry, Docker, Azure setup
2. **002-health-endpoint**: Health check com status Azure
3. **003-text-analysis**: Integração Azure Text Analytics
4. **004-audio-analysis**: Integração Azure Speech Services
5. **005-image-analysis**: Integração Azure Computer Vision
6. **006-multimodal-fusion**: Combinação de 3 modalidades
7. **007-rate-limiting**: Proteção de quotas Azure
8. **008-tests**: Unit + integration + load tests
9. **009-documentation**: Final README and video

---

## Conventions

- **Code**: English (variables, functions, classes)
- **Documentation**: Portuguese (Brazilian context)
- **Commits**: Conventional commits (`feat:`, `fix:`, `docs:`)
- **PRs**: Small, focused, with tests
- **Types**: Mandatory type hints on public APIs
- **Testing**: Tests for all new code
- **Security**: Never commit secrets, always use .env

---

## Melhores Práticas de Código (MCP Context7)

> **IMPORTANTE**: Todas as implementações de código devem seguir as melhores práticas documentadas em `docs/technical/best-practices.md`

### Validação com Context7:
Antes de implementar cada módulo, buscar no MCP Context7:
- "FastAPI best practices 2024"
- "Azure SDK Python async patterns"
- "FastAPI dependency injection"
- "Azure Cognitive Services error handling"
- "Multimodal ML architecture patterns"

### Padrões Críticos:
1. **Dependency Injection**: Usar `Depends()` para Azure clients
2. **Singleton Pattern**: Clientes Azure como singletons
3. **Async/Await**: Todas as chamadas I/O assíncronas
4. **Error Handling**: Exception handlers específicos para Azure
5. **Rate Limiting**: Proteção de quotas Azure
6. **LGPD**: Anonimização de dados sensíveis

---

## Links

- Fase 1: https://github.com/vagnerbarbosa/tech-challenge-fase-1
- Fase 2: https://github.com/vagnerbarbosa/tech-challenge-fase-2
- Fase 3: https://github.com/vagnerbarbosa/tech-challenge-fase-3
- Tech Challenge Brief: `d:\OneDrive\vagner-desktop\Downloads\POSTECH - IADT - Tech Challenge - Fase 4.pdf`
- Azure Free Tier: https://azure.microsoft.com/free
- Melhores Práticas: `docs/technical/best-practices.md`
