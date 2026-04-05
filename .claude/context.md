# Contexto do Projeto

> Arquivo mantido pelo Claude Code para contexto entre sessões.
> Atualizado em: 2026-04-05 (Deep Dive Completo + Correção Objetivo)

## Informações Gerais

- **Projeto**: Tech Challenge - Fase 4 (FIAP/Alura AI para Devs)
- **Repositório**: tech-challenge-fase-4
- **Objetivo Principal (CITADO DO PDF)**: "Realizar a análise e fusão de diferentes tipos de dados médicos específicos da saúde da mulher — incluindo texto, áudio e vídeo."
- **Escopo**: Sistema multimodal para identificação de violência doméstica e riscos à saúde mental feminina
- **Metodologia**: Specification-Driven Development (SDD)
- **Critérios de Avaliação**: Funcionalidade (30%), Código (25%), Containerização (20%), Testes (15%), Documentação (10%)

## Opções Selecionadas (3 de 5)

1. ✅ **Detectar precocemente riscos em saúde materna e ginecológica**
2. ✅ **Identificar sinais de violência doméstica ou abuso**
3. ❌ Monitorar bem-estar psicológico feminino
4. ✅ **Utilizar serviços em nuvem** (Azure Free Tier)
5. ❌ Aplicar técnicas de detecção de anomalias em tempo real

---

## Estado Atual

- [x] Deep dive na documentação PDF completo
- [x] Correção do objetivo (não é deploy do modelo Fase 2!)
- [x] Estrutura SDD criada com foco correto:
  - [x] README.md (atualizado - multimodal)
  - [x] docs/product-spec.md (multimodal)
  - [x] docs/user-stories.md (multimodal)
  - [x] docs/architecture.md (Azure Cognitive Services)
  - [x] docs/api-contracts.md (endpoints /analyze/*)
  - [x] docs/objectives.md (citação do PDF)
  - [x] docs/technical/cloud-free-tier-analysis.md (análise Azure)
  - [x] tasks/001-bootstrap.md (atualizado Azure)
  - [x] CLAUDE.md atualizado
  - [x] .claude/context.md (este arquivo)
- [ ] Bootstrap técnico (PENDING - aguardando aprovação)
- [ ] Implementação de features (não iniciada)

---

## Restrições CRÍTICAS (Não-negociáveis)

### Modalidades Obrigatórias:
1. **Texto** (Azure Text Analytics)
2. **Áudio** (Azure Speech Services)
3. **Imagem/Vídeo** (Azure Computer Vision)
4. **Fusão multimodal** (combinação das 3)

### Campos Obrigatórios em TODAS Respostas:
- ✅ `risco_violencia`: baixo | medio | alto
- ✅ `risco_saude_mental`: baixo | medio | alto

### Azure Free Tier - Limites:
- Text Analytics: 5,000 requests/mês
- Speech Services: 5 hours áudio/mês
- Computer Vision: 5,000 transactions/mês
- Blob Storage: 5GB

### Obrigatórios (Avaliação):
- [ ] API REST multimodal
- [ ] Integração Azure Cognitive Services
- [ ] Docker + docker-compose
- [ ] Testes > 70% cobertura
- [ ] Vídeo YouTube 5-10 min

---

## Tecnologias Definidas

### Core:
- **Framework**: FastAPI (async, OpenAPI)
- **Python**: 3.11+
- **Package Manager**: Poetry

### Azure Cognitive Services:
- **Azure AI Text Analytics**: Sentiment analysis, NLP
- **Azure Speech Services**: Speech-to-text, análise de voz
- **Azure Computer Vision**: Análise de imagem, expressões
- **Azure Blob Storage**: Armazenamento temporário

### Infrastructure:
- **Container**: Docker multi-stage
- **Database**: SQLite (dev) / Azure SQL (opcional)
- **Cache**: Redis (opcional)

### Dev Tools:
- **Lint**: Ruff (line length 88)
- **Type Check**: mypy strict
- **Tests**: pytest + httpx + locust

---

## Estrutura de Diretórios Esperada

```
tech-challenge-fase-4/
├── src/
│   ├── api/                    # FastAPI routes
│   │   ├── main.py
│   │   └── routes/
│   │       ├── health.py
│   │       ├── text.py
│   │       ├── audio.py
│   │       ├── image.py
│   │       └── multimodal.py
│   ├── core/                   # Config, logging, rate_limit
│   │   ├── config.py
│   │   ├── logging_config.py
│   │   ├── exceptions.py
│   │   └── rate_limit.py
│   ├── services/               # Lógica de negócio
│   │   ├── text_analysis.py
│   │   ├── audio_analysis.py
│   │   ├── image_analysis.py
│   │   └── fusion.py
│   ├── models/                 # Pydantic schemas
│   │   └── schemas.py
│   ├── infrastructure/         # Azure clients
│   │   └── azure_clients.py
│   └── utils/                  # Helpers
├── tests/
│   ├── unit/
│   ├── integration/
│   └── load/
│       └── locustfile.py
├── docs/                       # Documentação SDD
│   ├── product-spec.md
│   ├── user-stories.md
│   ├── architecture.md
│   ├── api-contracts.md
│   ├── objectives.md
│   └── technical/
│       └── cloud-free-tier-analysis.md
├── scripts/                    # Dev scripts
├── tasks/
│   └── 001-bootstrap.md
├── pyproject.toml
├── poetry.lock
├── Dockerfile
├── docker-compose.yml
├── .env.example
├── .gitignore
├── README.md
└── CLAUDE.md
```

---

## Requisitos de Qualidade

| Ferramenta | Config | Uso |
|------------|--------|-----|
| Ruff | Line 88, Python 3.11 | Lint + Format |
| mypy | strict mode | Type checking |
| pytest | cov=src, cov-report=html | Testes + Coverage |
| Docker | multi-stage, slim | Containerização |

---

## Comandos Frequentes

```bash
# Setup
poetry install
poetry shell

# Run dev
poetry run uvicorn src.api.main:app --reload --port 8000

# Test
poetry run pytest -v
poetry run pytest --cov=src --cov-report=html

# Quality
poetry run ruff check . --fix
poetry run ruff format .
poetry run mypy src/

# Docker
docker-compose up --build -d
docker-compose logs -f api
docker-compose down -v

# Test API manual
curl http://localhost:8000/health
curl -X POST http://localhost:8000/analyze/text \
  -H "Content-Type: application/json" \
  -d '{"texto":"Estou me sentindo ansiosa e com medo"}'
```

---

## Endpoints da API

| Endpoint | Método | Descrição |
|----------|--------|-----------|
| `/health` | GET | Health check + status Azure |
| `/analyze/text` | POST | Análise de texto (Azure Text Analytics) |
| `/analyze/audio` | POST | Análise de áudio (Azure Speech) |
| `/analyze/image` | POST | Análise de imagem (Azure Computer Vision) |
| `/analyze/multimodal` | POST | Fusão de 3 modalidades |
| `/docs` | GET | Swagger UI |

---

## Variáveis de Ambiente (Azure)

```bash
# Azure Text Analytics
AZURE_TEXT_KEY=...
AZURE_TEXT_ENDPOINT=https://<resource>.cognitiveservices.azure.com/

# Azure Speech Services
AZURE_SPEECH_KEY=...
AZURE_SPEECH_REGION=brazilsouth

# Azure Computer Vision
AZURE_VISION_KEY=...
AZURE_VISION_ENDPOINT=https://<resource>.cognitiveservices.azure.com/

# Azure Blob Storage (opcional)
AZURE_STORAGE_CONNECTION_STRING=...

# App
APP_NAME="Multimodal Health Analysis API"
APP_VERSION=1.0.0
ENVIRONMENT=development
DEBUG=true
LOG_LEVEL=DEBUG
```

---

## Próximos Passos (Tasks)

### Task 001: Bootstrap (8 pontos)
- [ ] Poetry init + dependências (FastAPI + Azure SDKs)
- [ ] Estrutura de diretórios completa
- [ ] Configuração Ruff, mypy, pytest
- [ ] Dockerfile multi-stage
- [ ] docker-compose.yml
- [ ] Scripts auxiliares
- [ ] .env.example com variáveis Azure
- [ ] Criar conta Azure e provisionar recursos

### Task 002: Health Endpoint (3 pontos)
- [ ] FastAPI app base
- [ ] GET /health com status Azure
- [ ] Testes

### Task 003: Text Analysis (8 pontos)
- [ ] Integração Azure Text Analytics
- [ ] POST /analyze/text
- [ ] Validação de entrada
- [ ] Testes

### Task 004: Audio Analysis (8 pontos)
- [ ] Integração Azure Speech Services
- [ ] POST /analyze/audio (upload)
- [ ] Transcrição + análise
- [ ] Testes

### Task 005: Image Analysis (8 pontos)
- [ ] Integração Azure Computer Vision
- [ ] POST /analyze/image (upload)
- [ ] Análise de expressões
- [ ] Testes

### Task 006: Multimodal Fusion (13 pontos)
- [ ] Combinar 3 modalidades
- [ ] POST /analyze/multimodal
- [ ] Late fusion
- [ ] Testes

### Task 007: Rate Limiting (3 pontos)
- [ ] Proteção quotas Azure
- [ ] Cache Redis (opcional)

### Task 008: Tests (8 pontos)
- [ ] Unit tests > 70%
- [ ] Integration tests
- [ ] Load tests (Locust)

### Task 009: Documentation (5 pontos)
- [ ] README final
- [ ] Vídeo YouTube 5-10 min

---

## Convenções

- **Código**: Inglês (PEP 8, type hints obrigatórios)
- **Docs**: Português (contexto brasileiro)
- **Commits**: Conventional commits (feat:, fix:, docs:, test:)
- **Branches**: main, feature/*, fix/*
- **PRs**: Small, focused, com testes
- **Security**: Nunca commitar secrets (.env no gitignore)

---

## Ferramentas de Qualidade (MCP Context7)

### Uso Obrigatório:
Toda implementação de código deve ser validada com MCP Context7 para:
- FastAPI best practices
- Azure SDK Python patterns
- Async/await patterns
- Error handling

### Buscar no Context7:
```
- "FastAPI best practices 2024"
- "Azure SDK Python async patterns"
- "FastAPI dependency injection patterns"
- "Azure Cognitive Services error handling"
- "Python type hints best practices"
```

### Documento de Referência:
`docs/technical/best-practices.md` - Contém padrões a serem seguidos

---

## Links Úteis

- Fase 1: https://github.com/vagnerbarbosa/tech-challenge-fase-1
- Fase 2: https://github.com/vagnerbarbosa/tech-challenge-fase-2
- Fase 3: https://github.com/vagnerbarbosa/tech-challenge-fase-3
- Documentação PDF: d:\OneDrive\vagner-desktop\Downloads\POSTECH - IADT - Tech Challenge - Fase 4.pdf
- Azure Free Tier: https://azure.microsoft.com/free
- Azure Cognitive Services: https://azure.microsoft.com/services/cognitive-services/
- Melhores Práticas: `docs/technical/best-practices.md`

---

## Preferências Globais de Memória (Obrigatórias)

### 1. MCP Preference (feedback_mcp_preference_global.md)
**Regra:** Sempre priorizar MCP quando custo for menor que alternativas (CLI, APIs diretas)

**Aplicação neste projeto:**
- ✅ Azure SDK via pip (Python nativo) - já é MCP-friendly
- ✅ FastAPI nativo - não precisa de MCP adicional
- ⚠️ Se usar GitHub Actions: preferir MCP GitHub sobre `gh` CLI
- ⚠️ Se usar banco de dados: preferir MCP BD sobre queries manuais

**How to apply:**
- Antes de cada operação, verificar se MCP server está disponível
- Comparar custo: número de chamadas, complexidade
- Usar MCP se igual ou melhor em custo

### 2. PR Status Check (feedback_pr_status_check.md)
**Regra:** Antes de atualizar uma PR, sempre verificar seu status. Se já foi mergeada, abrir uma nova PR.

**Aplicação neste projeto:**
- Antes de fazer alterações em branch existente:
  ```bash
  gh pr view <num> --json state
  ```
- Se state = "MERGED" → criar nova branch e nova PR
- Se state = "OPEN" → pode adicionar commits

**Como aplicar:**
1. Verificar estado da PR antes de push
2. Se mergeada → criar feature/<nova-funcionalidade>
3. Nunca adicionar commits em PR já mergeada

---

## Checklist Final de Entrega

- [ ] Repositório GitHub público
- [ ] README.md completo (descrição, como executar, exemplos)
- [ ] API REST funciona (`docker-compose up`)
- [ ] Endpoints `/analyze/text`, `/analyze/audio`, `/analyze/image`, `/analyze/multimodal`
- [ ] Endpoint `/health` funciona
- [ ] Swagger em `/docs`
- [ ] Dockerfile multi-stage
- [ ] docker-compose.yml completo
- [ ] Integração Azure funcionando
- [ ] Testes unitários + integração (pytest)
- [ ] Testes de carga (Locust)
- [ ] Cobertura de código > 70%
- [ ] Ruff/mypy passando
- [ ] Vídeo demonstrativo no YouTube (5-10 min)
- [ ] Código limpo, organizado, com type hints
- [ ] **Regras de memória aplicadas**: MCP preference + PR status check
