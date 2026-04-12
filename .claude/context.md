# Contexto do Projeto - Tech Challenge Fase 4

> Arquivo mantido pelo Claude Code para contexto entre sessões.
> Última atualização: 2026-04-12 (Deep Dive Completo - Hyper Contextualização)

## 📊 Estado Atual do Projeto

**Branch**: `main` (atualizada e sincronizada)
**Specs Concluídas**: 2/10
**Cobertura de Testes**: 81% (72 testes passando)
**Último Commit**: Revert "docs: Atualiza context.md com hyper-contextualização do projeto"

---

## 🎯 Objetivo Principal

**"Realizar a análise e fusão de diferentes tipos de dados médicos específicos da saúde da mulher — incluindo texto, áudio e vídeo."**

### Opções Selecionadas:
1. ✅ Detectar precocemente riscos em saúde materna e ginecológica
2. ✅ Identificar sinais de violência doméstica ou abuso
4. ✅ Utilizar serviços em nuvem (Azure Free Tier)

---

## 🏗️ Arquitetura Multimodal

### Modalidades Implementadas

| Modalidade | Status | Endpoint | Tecnologia | Versão |
|------------|--------|----------|------------|--------|
| 📝 **Texto** | ✅ Concluído | `POST /analyze/text` | Azure AI Language (Text Analytics) | 5.4.0 |
| 🎙️ **Áudio** | 📝 Draft | `POST /analyze/audio` | Azure AI Speech | 1.48.0 |
| 🖼️ **Imagem** | 📝 Draft | `POST /analyze/image` | Azure AI Vision | 1.0.x |
| 🎥 **Vídeo (YOLOv8)** | 📝 Draft | `POST /analyze/video` | **YOLOv8 Local** + Azure Vision (fallback) | 8.x |
| 🔀 **Multimodal** | 📝 Draft | `POST /analyze/multimodal` | Fusão das 3 modalidades | - |

### Status das Specs

| ID | Feature | Status | Prioridade | Dependências |
|----|---------|--------|------------|--------------|
| 001 | Bootstrap do Projeto | ✅ Concluído | P0 | - |
| 002 | Análise de Texto | ✅ Concluído | P1 | 001 |
| 003 | Análise de Áudio | 📝 Draft | P1 | 001 |
| **004a** | **Análise Vídeo YOLOv8** | 📝 **Draft** | **P1** | **001** |
| 004b | Análise Imagem Azure | 📝 Draft | P1 | 001 |
| 005 | Fusão Multimodal | 📝 Draft | P1 | 002, 003, 004a |
| 006 | Rate Limiting | 📝 Draft | P2 | 002-004 |
| 007 | Security Hardening | 📝 Draft | P1 | Todos |
| 008 | Testes Automatizados | 📝 Draft | P1 | 005 |
| 009 | Deploy Azure | 📝 Draft | P1 | Todos |
| 010 | Documentação Final | 📝 Draft | P1 | Todos |

---

## 💻 Implementação Detalhada (Spec 002)

### Core Components

#### 1. Cache em Memória (`src/core/cache.py`)
- **Classe**: `AnalysisCache`
- **TTL**: 60 minutos (configurável)
- **Key**: SHA256 do texto normalizado
- **Thread-safe**: Sim (para desenvolvimento)
- **Métodos**: `get()`, `set()`, `clear_expired()`, `clear_all()`, `get_stats()`
- **Estatísticas**: Exposição via endpoint `/analyze/text/cache/stats`

#### 2. Detecção de Risco (`src/services/risk_detector.py`)
- **Função Principal**: `calculate_risk(text, sentiment, confidence_scores)`
- **Lógica**: Score 0-100 baseado em palavras-chave + sentimento Azure
- **Thresholds**:
  - Baixo: < 30
  - Médio: 30-60
  - Alto: > 60

**RISK_KEYWORDS** (`src/core/config.py:301-418`):
```python
violencia: 58 palavras-chave
  ["violência", "agressão", "bater", "machucar", "ameaça", ...]

saude_mental: 62 palavras-chave
  ["ansiedade", "depressão", "suicídio", "pânico", "desespero", ...]
```

#### 3. Integração Azure (`src/infrastructure/azure_clients.py`)
- **Padrão**: Singleton com `@lru_cache`
- **Retry Policy**: 3 tentativas, backoff_factor=0.3
- **Exceções Customizadas**:
  - `QuotaExceededError` (HTTP 429)
  - `AuthenticationError` (HTTP 401/403)
  - `AzureConnectionError`
  - `AzureServiceError`
- **Wrapper**: `safe_azure_call()` para tratamento de erros

#### 4. Serviço de Análise (`src/services/text_analysis.py`)
- **Classe**: `TextAnalysisService`
- **Cache**: Verificado antes de chamar Azure
- **Sanitização**: Remove zero-width characters, control chars
- **Extração de Keywords**: Baseada em frequência (exclui stop words em português)
- **Score**: Calculado de -1.0 a 1.0 baseado no sentimento Azure

### Models Pydantic v2 (`src/models/schemas.py`)

**TextAnalysisRequest**:
```python
texto: str (min_length=10, max_length=5000)
tipo: str (pattern="^(diario|prontuario|relato|geral)$")
patient_id: str | None
```
- Validador: `validate_texto_not_empty` (mode="after")

**TextAnalysisResponse**:
```python
sentimento: str (pattern="^(positivo|negativo|neutro|misto)$")
score: float (ge=-1.0, le=1.0)
risco_violencia: str (obrigatório - pattern="^(baixo|medio|alto)$")
risco_saude_mental: str (obrigatório - pattern="^(baixo|medio|alto)$")
palavras_chave: list[str]
indicadores: list[str]
metadata: AnalysisMetadata
```

**AnalysisMetadata**:
```python
correlation_id: str
timestamp: datetime
tempo_processamento_ms: int
cache_hit: bool
azure_calls: int
```

### Endpoints (`src/api/routes/text.py`)

**POST /analyze/text**:
- Response Model: `TextAnalysisResponse`
- Responses documentadas: 200, 400, 429, 502, 503
- Injeção de dependência: `TextAnalysisServiceDep` (Annotated[Type, Depends()])
- Cache: Verificado automaticamente

**GET /analyze/text/cache/stats**:
- Retorna estatísticas do cache

**POST /analyze/text/cache/clear**:
- Limpa todas as entradas do cache

### Configuração (`src/core/config.py`)

**Settings** (Pydantic Settings v2):
- Carrega de `.env` com `SettingsConfigDict`
- Validação de endpoints Azure (http/https)
- Validação de secret_key em produção
- Propriedades computadas: `max_upload_size_bytes`, extension lists

**Rate Limiting (Azure Free Tier)**:
```python
MAX_TEXT_REQUESTS_PER_DAY = 160    # ~5000/mês
MAX_SPEECH_MINUTES_PER_DAY = 10    # ~300/mês
MAX_VISION_REQUESTS_PER_DAY = 160  # ~5000/mês
```

---

## 🧪 Testes e Qualidade

### Test Configuration (pyproject.toml)
```toml
[tool.pytest.ini_options]
asyncio_mode = "auto"
addopts = [
    "--cov=src",
    "--cov-fail-under=70",
    "--cov-report=html:htmlcov",
]
```

### Testes Implementados (72 passando, 81% coverage)

**Unit Tests**:
- `test_risk_detector.py`: Cálculo de risco com keywords
- `test_cache.py`: TTL, expiração, clear
- `test_cache_stress.py`: Concorrência

**Integration Tests**:
- `test_text_endpoint.py`: POST /analyze/text
- `test_azure_services.py`: Mock de serviços Azure
- `test_placeholder.py`: Placeholder para futuros testes

### CI/CD (`.github/workflows/`)

**tests.yml**:
- Ruff linting (line length 88)
- mypy strict mode
- pytest com coverage > 70%
- Python 3.11 matrix

**validate-commits.yml**:
- Conventional Commits em português
- Título da PR começa com maiúscula

---

## 🐳 Docker e Infraestrutura

### Docker Compose (`docker-compose.yml`)
- **API**: FastAPI na porta 8000
- **Redis**: Opcional (porta 6379)
- **Healthcheck**: `curl http://localhost:8000/health`
- **Volumes**: `./data`, `./logs`

### Dockerfile
- Multi-stage build
- Python 3.11-slim
- Poetry para gerenciamento de dependências
- Non-root user (appuser)

### Dependências Principais (pyproject.toml)

**Core**:
- fastapi >=0.104.0
- uvicorn >=0.24.0
- pydantic >=2.5.0, pydantic-settings >=2.1.0

**Azure AI Services**:
- azure-ai-textanalytics >=5.4.0
- azure-cognitiveservices-speech >=1.48.0
- azure-ai-vision-imageanalysis >=1.0.0
- azure-storage-blob >=12.0.0

**Processamento de Mídia**:
- opencv-python >=4.8.0
- pillow >=10.0.0
- numpy >=1.24.0

**Banco de Dados**:
- sqlalchemy >=2.0.0 (async)
- aiosqlite >=0.19.0

**Logging e Utilidades**:
- structlog >=23.2.0
- slowapi >=0.1.0
- httpx >=0.25.0

**Dev Dependencies**:
- pytest + pytest-asyncio + pytest-cov
- ruff >=0.1.0
- mypy >=1.7.0
- locust >=2.18.0 (load testing)

---

## 📋 Convenções do Projeto

### Código
- **Idioma**: Inglês (variáveis, funções, classes)
- **Documentação**: Português (comentários, docstrings)
- **Type Hints**: Obrigatórios (mypy strict mode)
- **Linting**: Ruff (line length 88)
- **Async/Await**: Todas as chamadas I/O

### Commits
- **Idioma**: Português
- **Formato**: Conventional Commits
- **Tipos**: feat, fix, docs, style, refactor, test, chore, ci, build, perf
- **Exemplo**: `feat: Adiciona análise de áudio com Azure Speech`

### Branches
- **Padrão**: `feature/XXX-nome-descritivo`
- **Exemplo**: `feature/003-audio-analysis`
- **Nunca commitar direto na main**

### Pull Requests
- **Idioma**: Português
- **Título**: Começa com letra maiúscula após o tipo
- **Exemplo**: `feat: Implementa endpoint de análise de áudio`
- **Nunca adicionar commits em PR já mergeada**

---

## ⚠️ Restrições CRÍTICAS

### MUST HAVE
- ✅ Campos obrigatórios em TODAS as respostas:
  - `risco_violencia`: baixo | medio | alto
  - `risco_saude_mental`: baixo | medio | alto
- ✅ Azure Free Tier (custo zero)
- ✅ **Deploy em produção Azure** (obrigatório)
- ✅ Docker funciona com `docker-compose up`
- ✅ Swagger em `/docs`
- ✅ LGPD compliance (anonimização, consentimento)
- ✅ Hard Stop: Sistema interrompe automaticamente quando quotas atingidas

### MUST NOT
- ❌ Exceder quotas do Azure Free Tier
- ❌ Armazenar dados pessoais identificáveis
- ❌ Processar sem consentimento explícito
- ❌ Expor secrets Azure no código
- ❌ Logar conteúdo de arquivos de mídia
- ❌ Commitar direto na main (sempre usar PR)

---

## 🚀 Próximos Passos

### Prioridade P1 (Obrigatórias para entrega)

1. **Spec 003: Análise de Áudio**
   - Azure Speech Services (Speech-to-Text)
   - Análise prosódica: pitch, energia, pausas
   - Detecção de voz tremida
   - Formatos: WAV, MP3, OGG (max 50MB)

2. **Spec 004a: Análise de Imagem (Azure Vision)**
   - Azure AI Vision (análise facial/emocional)
   - Imagens: JPEG, PNG (max 20MB)
   - Endpoint: `POST /analyze/image`

3. **Spec 004b: Análise de Vídeo (YOLOv8)**
   - YOLOv8 local para detecção de objetos
   - OpenCV para extração de frames
   - Vídeos: MP4 (max 30s)
   - Endpoint: `POST /analyze/video`

4. **Spec 005: Fusão Multimodal**
   - Late fusion com ponderação por confiança
   - `asyncio.gather()` para processamento paralelo
   - Alerta quando risco alto em 2+ modalidades
   - Fallback gracioso se uma modalidade falhar

5. **Spec 007: Security Hardening**
   - Validação de uploads (magic numbers)
   - Headers de segurança HTTP (CSP, HSTS, etc.)
   - API Key authentication
   - Sanitização de inputs

6. **Spec 009: Deploy Azure**
   - Azure App Service (Free Tier F1)
   - HTTPS obrigatório
   - Azure Key Vault para secrets
   - Health check configurado

### Prioridade P2

7. **Spec 006: Rate Limiting**
   - Hard stop automático quando quota atingida
   - Headers X-RateLimit-Limit, X-RateLimit-Remaining
   - Redis opcional para rate limiting distribuído

8. **Spec 008: Testes**
   - Testes de carga com Locust
   - Cobertura > 70%

9. **Spec 010: Documentação**
   - Vídeo demonstrativo YouTube (5-10 min)
   - README final completo

---

## 👥 Integrantes do Grupo 27

| Nome | GitHub |
|------|--------|
| Adriel Santos | [@AdrielCandido](https://github.com/AdrielCandido) |
| Leticia Nepomucena | [@LeticiaNepomucena](https://github.com/LeticiaNepomucena) |
| Lucas Silva | [@lucfsilva](https://github.com/lucfsilva) |
| Vagner Barbosa | [@vagnerbarbosa](https://github.com/vagnerbarbosa) |

**Curso**: FIAP/Alura - AI para Devs (IADT)
**Fase**: 4 (Análise Multimodal de Dados em Saúde da Mulher)
**Copyright**: MIT License - Copyright (c) 2026 Grupo 27 Tech Challenge

---

## 🔗 Links Importantes

- **Repositório**: https://github.com/vagnerbarbosa/tech-challenge-fase-4
- **Specs**: `specs/README.md`
- **Constitution**: `specs/constitution.md` (regras do projeto)
- **Melhores Práticas**: `docs/technical/context7-best-practices.md`
- **Azure Free Tier**: https://azure.microsoft.com/free
- **Context7 MCP**: Documentação atualizada das bibliotecas

---

## 📝 Notas de Desenvolvimento

### Padrões Aplicados (2026)
- Dependency Injection com `Annotated[Type, Depends()]` (Python 3.11+)
- Pydantic v2 com `mode="after"` validators
- Azure SDK com `@lru_cache` singleton
- Cache em memória com TTL (60 min)
- Type hints strict (mypy strict mode)
- Ruff para linting e formatação

### Decisões Arquiteturais
- **Late Fusion**: Escolhido para MVP (simpler que Early Fusion)
- **SQLite**: Para desenvolvimento (Azure SQL opcional em produção)
- **Redis**: Opcional (cache em memória suficiente para MVP)
- **Azure Blob Storage**: Para arquivos temporários de mídia

---

## 🎯 Critérios de Avaliação

| Critério | Peso | Status |
|----------|------|--------|
| Funcionalidade | 30% | 🔄 Em progresso (1/4 endpoints) |
| Código | 25% | ✅ Alto (Ruff, mypy, type hints) |
| Containerização | 20% | ✅ Docker + Compose funcionando |
| Testes | 15% | ✅ 81% cobertura (>70%) |
| Documentação | 10% | 🔄 Em progresso |

---

*Este documento foi gerado durante Deep Dive de hyper-contextualização em 2026-04-12*
*Para atualizar, edite este arquivo ou solicite um novo deep dive*
