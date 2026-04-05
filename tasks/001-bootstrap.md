# Task 001: Bootstrap do Projeto Multimodal

## Objetivo

Estabelecer a fundação do projeto com estrutura de diretórios, dependências e configurações iniciais para desenvolvimento do sistema multimodal de análise de saúde da mulher.

## Critérios de Aceite

### CA1: Estrutura de Diretórios
- [ ] Diretórios criados conforme especificação:
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
- [ ] Arquivos `__init__.py` em todos os pacotes Python

### CA2: Gerenciamento de Dependências (Poetry)
- [ ] `pyproject.toml` configurado com Poetry
- [ ] Dependências principais:
  - fastapi (>=0.104.0)
  - uvicorn (>=0.24.0)
  - python-multipart (upload de arquivos)
  - azure-ai-textanalytics (Azure Text Analytics)
  - azure-cognitiveservices-speech (Azure Speech Services)
  - azure-cognitiveservices-vision-computervision (Azure Computer Vision)
  - azure-storage-blob (Azure Blob Storage)
  - opencv-python (extração de frames de vídeo)
  - sqlalchemy + aiosqlite (banco local/dev)
- [ ] Dependências dev:
  - pytest, pytest-asyncio, pytest-cov, httpx
  - ruff, mypy
  - python-dotenv
- [ ] `poetry.lock` gerado

### CA3: Configuração de Ambiente
- [ ] `.env.example` com todas as variáveis Azure:
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
- [ ] `.env` no `.gitignore`
- [ ] Configuração Pydantic Settings em `src/core/config.py`
- [ ] Validação de variáveis obrigatórias

### CA4: Dockerização
- [ ] `Dockerfile` multi-stage otimizado
- [ ] `docker-compose.yml` com:
  - Serviço API
  - Redis (opcional, para cache)
  - Variáveis de ambiente
  - Volumes para desenvolvimento
- [ ] `.dockerignore` configurado
- [ ] Non-root user no container

### CA5: Linting e Formatação
- [ ] `ruff.toml` ou configuração em `pyproject.toml`:
  - Line length: 88
  - Target Python: 3.11
  - Select: E, F, I, W
- [ ] `mypy.ini` ou configuração em `pyproject.toml`:
  - strict mode
  - ignore_missing_imports = True (para libs Azure)

### CA6: Testes
- [ ] `pytest.ini` configurado:
  ```ini
  [pytest]
  testpaths = tests
  python_files = test_*.py
  python_classes = Test*
  python_functions = test_*
  addopts = -v --cov=src --cov-report=term-missing
  ```
- [ ] `tests/conftest.py` com fixtures básicas
- [ ] Teste de exemplo passando

### CA7: Scripts de Desenvolvimento
- [ ] `scripts/setup.sh` - Instalação inicial
- [ ] `scripts/run.sh` - Rodar local
- [ ] `scripts/test.sh` - Rodar testes
- [ ] `scripts/lint.sh` - Rodar linter
- [ ] `scripts/check-azure.sh` - Verificar conexão Azure

### CA8: Documentação Inicial
- [ ] `README.md` atualizado (já feito)
- [ ] `CLAUDE.md` atualizado
- [ ] `.claude/context.md` atualizado

## Tarefas Técnicas

### Setup Inicial
1. [ ] Poetry init
2. [ ] Adicionar dependências principais
3. [ ] Adicionar dependências Azure
4. [ ] Criar estrutura de diretórios

### Configuração
5. [ ] Criar `src/core/config.py` com Pydantic Settings
6. [ ] Criar `src/core/logging_config.py` (JSON logging)
7. [ ] Criar `src/core/exceptions.py` (exceções customizadas)
8. [ ] Criar `src/core/rate_limit.py` (gestão quota Azure)

### Azure Integration Setup
9. [ ] Criar conta Azure (free trial)
10. [ ] Provisionar recursos:
    - Text Analytics
    - Speech Services
    - Computer Vision
    - Blob Storage (opcional)
11. [ ] Coletar chaves e endpoints
12. [ ] Configurar `.env`

### Docker
13. [ ] Escrever Dockerfile
14. [ ] Escrever docker-compose.yml
15. [ ] Testar build: `docker-compose build`
16. [ ] Testar execução: `docker-compose up -d`

### Qualidade
17. [ ] Configurar ruff
18. [ ] Configurar mypy
19. [ ] Configurar pytest
20. [ ] Criar teste de exemplo

### Scripts
21. [ ] Criar scripts/setup.sh (chmod +x)
22. [ ] Criar scripts/run.sh (chmod +x)
23. [ ] Criar scripts/test.sh (chmod +x)
24. [ ] Criar scripts/lint.sh (chmod +x)

## Estimativa
**Pontuação**: 8 pontos
**Tempo estimado**: 6-8 horas

## Dependências
- Nenhuma (primeira task)

## Bloqueia
- Task 002: Implementar análise de texto
- Task 003: Implementar análise de áudio
- Task 004: Implementar análise de imagem
- Task 005: Implementar fusão multimodal

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

### Estrutura de Diretórios Esperada

```
tech-challenge-fase-4/
├── src/
│   ├── __init__.py
│   ├── api/
│   │   ├── __init__.py
│   │   ├── main.py              # Entry point FastAPI
│   │   └── routes/
│   │       ├── __init__.py
│   │       ├── health.py
│   │       ├── text.py
│   │       ├── audio.py
│   │       ├── image.py
│   │       └── multimodal.py
│   ├── core/
│   │   ├── __init__.py
│   │   ├── config.py            # Pydantic Settings
│   │   ├── logging_config.py    # JSON logging
│   │   ├── exceptions.py        # Custom exceptions
│   │   └── rate_limit.py        # Azure quota management
│   ├── services/
│   │   ├── __init__.py
│   │   ├── text_analysis.py
│   │   ├── audio_analysis.py
│   │   ├── image_analysis.py
│   │   ├── video_frame_extractor.py  # Extração de frames
│   │   └── fusion.py
│   ├── models/
│   │   ├── __init__.py
│   │   └── schemas.py           # Pydantic models
│   ├── infrastructure/
│   │   ├── __init__.py
│   │   └── azure_clients.py     # Azure SDK clients
│   └── utils/
│       ├── __init__.py
│       └── helpers.py
├── tests/
│   ├── __init__.py
│   ├── conftest.py              # Pytest fixtures
│   ├── unit/
│   │   ├── __init__.py
│   │   └── test_placeholder.py
│   ├── integration/
│   │   ├── __init__.py
│   │   └── test_placeholder.py
│   └── load/
│       ├── __init__.py
│       └── locustfile.py
├── scripts/
│   ├── setup.sh
│   ├── run.sh
│   ├── test.sh
│   └── lint.sh
├── docs/                        # Documentação SDD (já existe)
├── .claude/
│   └── context.md
├── tasks/
│   └── 001-bootstrap.md
├── pyproject.toml
├── poetry.lock
├── Dockerfile
├── docker-compose.yml
├── .dockerignore
├── .env.example
├── .env                         # NÃO COMMITAR
├── .gitignore
├── README.md                    # Já atualizado
└── CLAUDE.md                    # Já atualizado
```

### Checklist de Review

- [ ] `poetry install` funciona
- [ ] `docker-compose up --build` funciona
- [ ] `poetry run pytest` passa
- [ ] `poetry run ruff check .` passa
- [ ] `poetry run mypy src/` passa
- [ ] Scripts são executáveis
- [ ] `.env.example` está completo
- [ ] Todas as variáveis Azure documentadas
