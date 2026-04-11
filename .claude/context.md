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
  - [x] specs/README.md (índice de especificações)
  - [x] specs/001-bootstrap/ (bootstrap do projeto)
  - [x] specs/002-text-analysis/ (análise de texto)
  - [x] specs/003-audio-analysis/ (análise de áudio)
  - [x] specs/004-image-analysis/ (análise de imagem)
  - [x] specs/005-multimodal-fusion/ (fusão multimodal)
  - [x] specs/constitution.md (regras do projeto)
  - [x] docs/technical/context7-best-practices.md (melhores práticas)
  - [x] tasks/001-bootstrap.md (atualizado Azure)
  - [x] tasks/002-text-analysis.md (task concluída)
  - [x] CLAUDE.md atualizado
  - [x] .claude/context.md (este arquivo)
- [x] Bootstrap técnico (COMPLETED)
- [ ] Implementação de features (não iniciada)

---

## Restrições CRÍTICAS (Não-negociáveis)

### Modalidades Obrigatórias:
1. **Texto** (Azure AI Language / Text Analytics)
2. **Áudio** (Azure AI Speech)
3. **Imagem/Vídeo** (Azure AI Vision)
4. **Fusão multimodal** (combinação das 3)

> **⚠️ REBRANDING 2025**: Azure Cognitive Services → Azure AI Services → Azure AI Foundry. SDKs atualizados na seção de Tecnologias.

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
- [ ] **Deploy em produção Azure** (Free Tier - obrigatório)
- [ ] Docker + docker-compose
- [ ] Testes > 70% cobertura
- [ ] Vídeo YouTube 5-10 min

---

## Tecnologias Definidas

### Core:
- **Framework**: FastAPI (async, OpenAPI)
- **Python**: 3.11+
- **Package Manager**: Poetry

### Azure AI Services (Foundry Tools):
> **Nota**: Rebranding 2024-2025: Azure Cognitive Services → Azure AI Services → Azure AI Foundry

| Serviço | SDK Python | Versão | Propósito |
|---------|------------|--------|-----------|
| **Azure AI Language** (Text Analytics) | `azure-ai-textanalytics` | 5.4.0 | Sentiment analysis, NLP |
| **Azure AI Speech** | `azure-cognitiveservices-speech` | 1.48.x | Speech-to-text, análise de voz |
| **Azure AI Vision** | `azure-ai-vision-imageanalysis` | 1.0.x | Análise de imagem, expressões |
| **Azure Blob Storage** | `azure-storage-blob` | 12.x | Armazenamento temporário |

> **⚠️ IMPORTANTE**: O SDK antigo `azure-cognitiveservices-vision-computervision` foi **deprecated em novembro 2024**. Usar `azure-ai-vision-imageanalysis`.

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
├── src/                        # Código fonte
│   ├── api/                    # FastAPI routes
│   │   ├── main.py
│   │   └── routes/
│   │       ├── health.py
│   │       └── text.py         # Task 002 implementado
│   ├── core/                   # Config, logging, cache
│   │   ├── config.py
│   │   ├── logging_config.py
│   │   ├── exceptions.py
│   │   └── cache.py
│   ├── services/               # Lógica de negócio
│   │   ├── text_analysis.py    # Task 002 implementado
│   │   ├── risk_detector.py    # Task 002 implementado
│   │   ├── audio_analysis.py   # Task 003 (pendente)
│   │   ├── image_analysis.py   # Task 004 (pendente)
│   │   └── fusion.py           # Task 005 (pendente)
│   ├── models/                 # Pydantic schemas
│   │   └── schemas.py
│   ├── infrastructure/         # Azure clients
│   │   └── azure_clients.py
│   └── utils/                  # Helpers
├── tests/                      # Testes
│   ├── unit/
│   │   ├── services/
│   │   └── core/
│   ├── integration/
│   └── load/
│       └── locustfile.py
├── specs/                      # Especificações Spec Kit
│   ├── README.md
│   ├── constitution.md
│   ├── 001-bootstrap/
│   ├── 002-text-analysis/
│   ├── 003-audio-analysis/
│   ├── 004-image-analysis/
│   ├── 005-multimodal-fusion/
│   ├── 006-rate-limiting/
│   ├── 007-security-hardening/
│   ├── 008-tests/
│   └── 009-deploy-azure/
├── tasks/                      # Status das tasks
│   ├── 001-bootstrap.md
│   └── 002-text-analysis.md
├── docs/                       # Documentação técnica
│   └── technical/
│       └── context7-best-practices.md
├── scripts/                    # Scripts de dev
├── pyproject.toml
├── poetry.lock
├── Dockerfile
├── docker-compose.yml
├── docker-compose.mock.yml
├── .env.example
├── .gitignore
├── README.md
├── CLAUDE.md
└── .claude/                    # Configuração Claude Code
    ├── context.md
    ├── CLAUDE.md
    └── settings.local.json
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

## Próximos Passos (Specs)

### Spec 001: Bootstrap ✅ CONCLUÍDO
- [x] Poetry init + dependências (FastAPI + Azure SDKs)
- [x] Estrutura de diretórios completa
- [x] Configuração Ruff, mypy, pytest
- [x] Dockerfile multi-stage
- [x] docker-compose.yml
- [x] Scripts auxiliares
- [x] .env.example com variáveis Azure

### Spec 002: Text Analysis ✅ CONCLUÍDO
- [x] Integração Azure Text Analytics
- [x] POST /analyze/text
- [x] Cache em memória com TTL
- [x] Detecção de risco
- [x] Testes (72 passando, 81% coverage)

### Spec 003: Análise de Áudio 📝 DRAFT
- [ ] Integração Azure Speech Services
- [ ] POST /analyze/audio (upload)
- [ ] Transcrição + análise prosódica
- [ ] Testes

### Spec 004: Análise de Imagem 📝 DRAFT
- [ ] Integração Azure AI Vision
- [ ] POST /analyze/image (upload)
- [ ] Análise de expressões faciais
- [ ] Extração de frames de vídeo
- [ ] Testes

### Spec 005: Fusão Multimodal 📝 DRAFT
- [ ] Combinar 3 modalidades
- [ ] POST /analyze/multimodal
- [ ] Late fusion com ponderação
- [ ] Testes

### Spec 006: Rate Limiting 📝 DRAFT
- [ ] Proteção quotas Azure
- [ ] Hard stop automático
- [ ] Monitoramento de quotas

### Spec 007: Security Hardening 📝 DRAFT
- [ ] Correções de vulnerabilidades
- [ ] Headers de segurança
- [ ] Validação de uploads

### Spec 008: Testes 📝 DRAFT
- [ ] Testes unitários completos
- [ ] Testes de integração
- [ ] Testes de carga (Locust)

### Spec 009: Deploy Azure 📝 DRAFT - **OBRIGATÓRIO**
- [ ] App Service criado (Free Tier F1)
- [ ] API deployada e acessível publicamente
- [ ] Variáveis de ambiente configuradas
- [ ] URL de produção documentada

### Spec 010: Documentação 📝 DRAFT
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
`docs/technical/context7-best-practices.md` - Contém padrões atualizados de 2026

---

## Links Úteis

- Fase 1: https://github.com/vagnerbarbosa/tech-challenge-fase-1
- Fase 2: https://github.com/vagnerbarbosa/tech-challenge-fase-2
- Fase 3: https://github.com/vagnerbarbosa/tech-challenge-fase-3
- Documentação PDF: `POSTECH - IADT - Tech Challenge - Fase 4.pdf` (arquivo local)
- Azure Free Tier: https://azure.microsoft.com/free
- Azure Cognitive Services: https://azure.microsoft.com/services/cognitive-services/
- Melhores Práticas: `docs/technical/context7-best-practices.md`

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
