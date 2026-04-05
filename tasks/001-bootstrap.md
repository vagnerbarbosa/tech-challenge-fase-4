# Task 001: Bootstrap do Projeto Multimodal

## Objetivo

Estabelecer a fundação do projeto com estrutura de diretórios, dependências e configurações iniciais para desenvolvimento do sistema multimodal de análise de saúde da mulher.

## Status

**Status**: ✅ CONCLUÍDA  
**Data de Conclusão**: 2026-04-05  
**Branch**: `main` (mergeada via PR #7)

## Critérios de Aceite

### CA1: Estrutura de Diretórios ✅
- [x] Diretórios criados conforme especificação:
  ```
  src/
  ├── api/              # FastAPI routes
  ├── core/             # Configurações, logging
  ├── services/         # TextAnalysis, AudioAnalysis, ImageAnalysis, Fusion
  ├── models/           # Pydantic schemas
  ├── infrastructure/   # Azure clients
  └── utils/            # Helpers
  tests/
  ├── unit/
  ├── integration/
  └── load/
  ```
- [x] Arquivos `__init__.py` em todos os pacotes Python

### CA2: Gerenciamento de Dependências (Poetry) ✅
- [x] `pyproject.toml` configurado com Poetry
- [x] Dependências principais:
  - fastapi (>=0.104.0)
  - uvicorn (>=0.24.0)
  - python-multipart (upload de arquivos)
  - **azure-ai-textanalytics** >=5.4.0 (Azure AI Language - Text Analytics)
  - **azure-cognitiveservices-speech** >=1.48.0 (Azure AI Speech)
  - **azure-ai-vision-imageanalysis** >=1.0.0 (Azure AI Vision - **NOVO SDK**)
  - azure-storage-blob (>=12.0.0) (Azure Blob Storage)
  - opencv-python (>=4.8.0) (extração de frames de vídeo)
  - sqlalchemy + aiosqlite (banco local/dev)
- [x] Dependências dev:
  - pytest, pytest-asyncio, pytest-cov, httpx
  - ruff, mypy
  - python-dotenv
- [x] `poetry.lock` gerado

> **⚠️ IMPORTANTE - ATUALIZAÇÃO 2025**:
> O SDK `azure-cognitiveservices-vision-computervision` foi **deprecated em novembro 2024**.
> Usar `azure-ai-vision-imageanalysis` (novo SDK Azure AI Vision).
>
> **Azure AI Services Rebranding**: Azure Cognitive Services → Azure AI Services → Azure AI Foundry

### CA3: Configuração de Ambiente ✅
- [x] `.env.example` com todas as variáveis Azure:
  ```
  # Azure Text Analytics
  AZURE_TEXT_KEY=your_key_here
  AZURE_TEXT_ENDPOINT=https://...cognitiveservices.azure.com/

  # Azure Speech Services
  AZURE_SPEECH_KEY=your_key_here
  AZURE_SPEECH_REGION=brazilsouth

  # Azure Computer Vision
  AZURE_VISION_KEY=your_key_here
  AZURE_VISION_ENDPOINT=https://...cognitiveservices.azure.com/

  # Azure Blob Storage (opcional)
  AZURE_STORAGE_CONNECTION_STRING=...

  # App
  APP_NAME="Multimodal Health Analysis API"
  APP_VERSION=1.0.0
  DEBUG=false
  LOG_LEVEL=INFO
  ```
- [x] `.env` no `.gitignore`
- [x] Configuração Pydantic Settings em `src/core/config.py`
- [x] Validação de variáveis obrigatórias

### CA4: Dockerização ✅
- [x] `Dockerfile` multi-stage otimizado
- [x] `docker-compose.yml` com:
  - Serviço API
  - Redis (opcional, para cache)
  - Variáveis de ambiente
  - Volumes para desenvolvimento
- [x] `.dockerignore` configurado
- [x] Non-root user no container

### CA5: Linting e Formatação ✅
- [x] `ruff.toml` ou configuração em `pyproject.toml`:
  - Line length: 88
  - Target Python: 3.11
  - Select: E, F, I, W
- [x] `mypy.ini` ou configuração em `pyproject.toml`:
  - strict mode
  - ignore_missing_imports = True (para libs Azure)

**Resultado**: `poetry run ruff check .` - ✅ Todos os checks passaram!

### CA6: Testes ✅
- [x] `pytest.ini` configurado:
  ```ini
  [pytest]
  testpaths = tests
  python_files = test_*.py
  python_classes = Test*
  python_functions = test_*
  addopts = -v --cov=src --cov-report=term-missing
  ```
- [x] `tests/conftest.py` com fixtures básicas
- [x] Teste de exemplo passando

**Resultado**: `poetry run pytest -v` - ✅ 5 testes passando, cobertura 74%

### CA7: Scripts de Desenvolvimento ✅
- [x] `scripts/setup.sh` - Instalação inicial
- [x] `scripts/run.sh` - Rodar local
- [x] `scripts/test.sh` - Rodar testes
- [x] `scripts/lint.sh` - Rodar linter
- [x] `scripts/check-azure.sh` - Verificar conexão Azure
- [x] `scripts/run-mock.sh` - Rodar com mocks Azure

### CA8: Documentação Inicial ✅
- [x] `README.md` atualizado (já feito)
- [x] `CLAUDE.md` atualizado
- [x] `.claude/context.md` atualizado

## Tarefas Técnicas - Status

### Setup Inicial ✅
1. [x] Poetry init
2. [x] Adicionar dependências principais
3. [x] Adicionar dependências Azure
4. [x] Criar estrutura de diretórios

### Configuração ✅
5. [x] Criar `src/core/config.py` com Pydantic Settings
6. [x] Criar `src/core/logging_config.py` (JSON logging)
7. [x] Criar `src/core/exceptions.py` (exceções customizadas)
8. [x] Criar `src/core/rate_limit.py` (gestão quota Azure)

### Azure Integration Setup 🔄
9. [ ] Criar conta Azure (free trial) - **Pendente (próxima task)**
10. [ ] Provisionar recursos:
    - Text Analytics
    - Speech Services
    - Computer Vision
    - Blob Storage (opcional)
11. [ ] Coletar chaves e endpoints
12. [ ] Configurar `.env`

### Docker ✅
13. [x] Escrever Dockerfile
14. [x] Escrever docker-compose.yml
15. [x] Testar build: `docker-compose build` ✅
16. [x] Testar execução: `docker-compose up -d` ✅

### Qualidade ✅
17. [x] Configurar ruff
18. [x] Configurar mypy
19. [x] Configurar pytest
20. [x] Criar teste de exemplo

### Scripts ✅
21. [x] Criar scripts/setup.sh (chmod +x)
22. [x] Criar scripts/run.sh (chmod +x)
23. [x] Criar scripts/test.sh (chmod +x)
24. [x] Criar scripts/lint.sh (chmod +x)

## Validação Final

### Comandos Executados ✅
```bash
# ✅ poetry install - Funciona sem erros
# ✅ poetry run ruff check . - Todos os checks passaram
# ✅ poetry run mypy src/ - Nenhum erro encontrado (13 arquivos)
# ✅ poetry run pytest -v - 5 testes passando, cobertura 74%
# ✅ docker-compose build - Build realizado com sucesso
```

## Estimativa

**Pontuação**: 8 pontos  
**Tempo estimado**: 6-8 horas  
**Tempo real**: ~8 horas

## Dependências

- Nenhuma (primeira task)

## Bloqueia

- Task 002: Implementar análise de texto
- Task 003: Implementar análise de áudio
- Task 004: Implementar análise de imagem
- Task 005: Implementar fusão multimodal
- Task 007: Rate limiting
- Task 008: Security hardening
- Task 009: Testes
- Task 010: Deploy Azure

## Notas

### Variáveis de Ambiente Obrigatórias

```bash
# Azure Text Analytics (obrigatório)
AZURE_TEXT_KEY=...
AZURE_TEXT_ENDPOINT=https://<resource>.cognitiveservices.azure.com/

# Azure Speech Services (obrigatório)
AZURE_SPEECH_KEY=...
AZURE_SPEECH_REGION=brazilsouth  # ou sua região

# Azure Computer Vision (obrigatório)
AZURE_VISION_KEY=...
AZURE_VISION_ENDPOINT=https://<resource>.cognitiveservices.azure.com/

# Azure Blob Storage (opcional, para arquivos grandes)
AZURE_STORAGE_CONNECTION_STRING=...

# App
APP_NAME="Multimodal Health Analysis API"
APP_VERSION=1.0.0
ENVIRONMENT=development
DEBUG=true
LOG_LEVEL=DEBUG
```

### Estrutura de Diretórios Esperada ✅

```
tech-challenge-fase-4/
├── src/
│   ├── __init__.py
│   ├── api/
│   │   ├── __init__.py
│   │   ├── main.py              # Entry point FastAPI ✅
│   │   └── routes/
│   │       ├── __init__.py
│   │       ├── health.py         # ✅
│   │       ├── text.py           # (Task 002)
│   │       ├── audio.py          # (Task 003)
│   │       ├── image.py          # (Task 004)
│   │       └── multimodal.py     # (Task 006)
│   ├── core/
│   │   ├── __init__.py
│   │   ├── config.py            # Pydantic Settings ✅
│   │   ├── logging_config.py    # JSON logging ✅
│   │   ├── exceptions.py        # Custom exceptions ✅
│   │   └── rate_limit.py        # Azure quota management ✅
│   ├── services/
│   │   ├── __init__.py
│   │   ├── text_analysis.py     # (Task 003)
│   │   ├── audio_analysis.py    # (Task 004)
│   │   ├── image_analysis.py    # (Task 005)
│   │   ├── video_frame_extractor.py  # (Task 005)
│   │   └── fusion.py            # (Task 006)
│   ├── models/
│   │   ├── __init__.py
│   │   └── schemas.py           # (Task 002)
│   ├── infrastructure/
│   │   ├── __init__.py
│   │   └── azure_clients.py     # (Task 002)
│   └── utils/
│       ├── __init__.py
│       └── helpers.py
├── tests/
│   ├── __init__.py
│   ├── conftest.py              # Pytest fixtures ✅
│   ├── unit/
│   │   ├── __init__.py
│   │   └── test_placeholder.py  # ✅
│   ├── integration/
│   │   ├── __init__.py
│   │   └── test_placeholder.py  # ✅
│   └── load/
│       ├── __init__.py
│       └── locustfile.py        # (Task 008)
├── scripts/                     # ✅
│   ├── setup.sh
│   ├── run.sh
│   ├── test.sh
│   └── lint.sh
├── docs/                        # Documentação SDD (já existe) ✅
├── .claude/
│   └── context.md               # ✅
├── tasks/
│   └── 001-bootstrap.md         # ✅
├── pyproject.toml               # ✅
├── poetry.lock                  # ✅
├── Dockerfile                   # ✅
├── docker-compose.yml           # ✅
├── .dockerignore                # ✅
├── .env.example                 # ✅
├── .env                         # ✅ (NÃO COMMITAR)
├── .gitignore                   # ✅
├── README.md                    # ✅
└── CLAUDE.md                    # ✅
```

### Checklist de Review ✅

- [x] `poetry install` funciona
- [x] `docker-compose up --build` funciona
- [x] `poetry run pytest` passa
- [x] `poetry run ruff check .` passa
- [x] `poetry run mypy src/` passa
- [x] Scripts são executáveis
- [x] `.env.example` está completo
- [x] Todas as variáveis Azure documentadas

## Próxima Task

**Task 002**: Health Endpoint - Implementar endpoint `/health` com status dos serviços Azure
