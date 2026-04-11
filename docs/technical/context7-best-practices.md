# Melhores Práticas - Context7 Reference

**Documento de referência com as melhores práticas atualizadas (2024)**

Este documento consolida as melhores práticas das tecnologias utilizadas no projeto, baseado na documentação oficial e guidelines mais recentes.

---

## Índice

1. [FastAPI](#fastapi)
2. [Pydantic v2](#pydantic-v2)
3. [Azure SDK Python](#azure-sdk-python)
4. [pytest](#pytest)
5. [Poetry](#poetry)

---

## Atualizações 2026

### Azure AI Text Analytics 5.4.0 (Fevereiro/Março 2026)

**⚠️ Breaking Changes - Continuation Tokens:**

A versão 5.4.0 introduziu mudanças no formato dos continuation tokens para operações de análise assíncrona:

- **Novo formato**: Tokens agora usam codificação Base64URL em vez de Base64 padrão
- **Compatibilidade**: Tokens antigos ainda são suportados para backward compatibility
- **Recomendação**: Não armazene tokens em banco de dados - são temporários por design

```python
# ✅ Correto - Não armazene continuation tokens
def analyze_text_async(texts: list[str]):
    client = get_text_analytics_client()
    poller = client.begin_analyze_healthcare_entities(texts)
    # Aguarde ou use callbacks, mas não persista o token
    return poller.result()

# ❌ Evite - Armazenar tokens
# db.save_token(poller.continuation_token())  # Não faça isso
```

**Novo método `analyze_text_with_ner`:**

```python
from azure.ai.textanalytics import TextAnalysisClient

# Reconhecimento de entidades nomeadas (NER) aprimorado
client = get_text_analytics_client()
documents = ["O Dr. João trabalha no Hospital Albert Einstein em São Paulo"]

response = client.recognize_entities(documents)
# Novas categorias em 2025: DATE_RESOLUTION, EVENT_REFERENCE
```

### FastAPI 2026 - Melhores Práticas Atualizadas

#### UV como Package Manager (2026)

```bash
# UV é o mais rápido para Python 2026
uv venv
uv pip install fastapi uvicorn[standard]
uv pip compile pyproject.toml -o requirements.txt

# Docker com UV
FROM ghcr.io/astral-sh/uv:python3.11-bookworm-slim
```

#### Dual Session Pattern (FastAPI + Celery)

```python
from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine
from sqlalchemy.orm import sessionmaker

# Engine separado para Celery workers
celery_engine = create_async_engine(
    DATABASE_URL,
    poolclass=NullPool,  # Sem pool para workers
)

# Engine para FastAPI com pool
api_engine = create_async_engine(
    DATABASE_URL,
    pool_size=5,
    max_overflow=10,
)

# Sessions
AsyncSessionLocal = sessionmaker(api_engine, class_=AsyncSession)
CelerySessionLocal = sessionmaker(celery_engine, class_=AsyncSession)
```

#### Performance Hierarchy 2026

```python
# Ordem de performance para parsing JSON (do mais rápido):

# 1. MAIS RÁPIDO: Pydantic v2 model_validate_json
def parse_fast(data: bytes) -> User:
    return User.model_validate_json(data)

# 2. ORJSON + Pydantic
import orjson
def parse_orjson(data: bytes) -> User:
    return User.model_validate(orjson.loads(data))

# 3. Padrão json
import json
def parse_std(data: str) -> User:
    return User.model_validate(json.loads(data))

# 4. MENOS RÁPIDO: BaseModel direto
user = User(**json.loads(data))
```

### Pydantic v2 2026 - Novos Padrões

#### `computed_field` para Propriedades

```python
from pydantic import BaseModel, computed_field

class AnalysisResult(BaseModel):
    sentiment: str
    score: float

    @computed_field  # Nova em 2024, padrão em 2026
    @property
    def risk_level(self) -> str:
        if self.score < -0.7:
            return "alto"
        elif self.score < -0.3:
            return "medio"
        return "baixo"

# Incluído automaticamente em model_dump()
result.model_dump()  # {'sentiment': 'negativo', 'score': -0.8, 'risk_level': 'alto'}
```

#### TypeAdapter para Validação Direta

```python
from pydantic import TypeAdapter

# Reutilize adapters (não crie dentro de funções)
TextListAdapter = TypeAdapter(list[str])
ResultAdapter = TypeAdapter(AnalysisResult)

# Uso
validated_texts = TextListAdapter.validate_python(raw_data)
result = ResultAdapter.validate_json(json_bytes)

# Performance: ~50x mais rápido que Pydantic v1
```

#### `model_validate_json` - Otimização Crítica

```python
# ✅ CORRETO: Validação direta de bytes/json
user = User.model_validate_json(json_bytes)

# ❌ EVITE: json.loads() + model_validate()
user = User.model_validate(json.loads(json_str))  # 2x mais lento
```

---

## FastAPI

### Dependency Injection

**Princípio Fundamental**: Use `Depends()` para injeção de dependências, promovendo código testável e modular.

```python
from fastapi import Depends, FastAPI
from typing import Annotated

app = FastAPI()

# Dependency simples
def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

# Uso com Annotated (Python 3.9+)
DBDep = Annotated[Session, Depends(get_db)]

@app.get("/items/")
async def read_items(db: DBDep):
    return db.query(Item).all()
```

### Sub-dependências

Componha comportamentos em cadeia:

```python
async def get_token_header(x_token: str = Header()):
    if x_token != "fake-super-secret-token":
        raise HTTPException(status_code=400, detail="X-Token header invalid")
    return x_token

async def get_query_token(token: str = Depends(get_token_header)):
    # Recebe o resultado da dependência anterior
    return token

@app.get("/items/", dependencies=[Depends(get_query_token)])
async def read_items():
    return [{"item": "Foo"}]
```

### Sobrescrever Dependências para Testes

```python
# Em testes
from fastapi.testclient import TestClient

async def override_get_db():
    try:
        db = TestingSessionLocal()
        yield db
    finally:
        db.close()

app.dependency_overrides[get_db] = override_get_db

client = TestClient(app)
```

### Context Management com `starlette-context`

Para dados scoped por request (request ID, correlation ID):

```python
from starlette_context import context, middleware

@app.middleware("http")
async def add_request_id(request: Request, call_next):
    with context.set("request_id", str(uuid.uuid4())):
        response = await call_next(request)
        return response

# Acesso em qualquer lugar
@app.get("/")
async def root():
    request_id = context.get("request_id")
    return {"request_id": request_id}
```

---

## Pydantic v2

### Tipos de Validadores

| Modo | Quando Usar | Ordem de Execução |
|------|-------------|-------------------|
| `mode="after"` | Após coerção do Pydantic (padrão, mais seguro) | Esquerda → Direita |
| `mode="before"` | Antes do parsing, para modificar input raw | Direita → Esquerda |
| `mode="wrap"` | Controle completo (antes/depois) | Direita → Esquerda |
| `mode="plain"` | Skip validação interna do Pydantic | Imediato |

### Field Validators

```python
from pydantic import BaseModel, field_validator, ValidationInfo

class User(BaseModel):
    username: str
    password: str
    password_repeat: str

    @field_validator('username')
    @classmethod
    def validate_username(cls, v: str) -> str:
        if len(v) < 3:
            raise ValueError('Username must be at least 3 characters')
        return v.lower()

    @field_validator('password_repeat', mode='after')
    @classmethod
    def check_passwords_match(cls, v: str, info: ValidationInfo) -> str:
        if v != info.data['password']:
            raise ValueError('Passwords do not match')
        return v
```

### Validators Reutilizáveis com Annotated

```python
from typing import Annotated
from pydantic import AfterValidator, BeforeValidator
import re

def normalize_phone(value: str) -> str:
    digits = re.sub(r'\D', '', value)
    if len(digits) == 10:
        return f"+1{digits}"
    raise ValueError('Invalid phone number')

# Tipo reutilizável
PhoneNumber = Annotated[str, BeforeValidator(normalize_phone)]

class Customer(BaseModel):
    name: str
    phone: PhoneNumber  # Mesma validação

class Employee(BaseModel):
    name: str
    phone: PhoneNumber  # Reutilizado
```

### Model Validators

```python
from typing_extensions import Self

class Reservation(BaseModel):
    check_in: date
    check_out: date

    @model_validator(mode='after')
    def validate_dates(self) -> Self:
        if self.check_out <= self.check_in:
            raise ValueError('Check-out must be after check-in')
        return self
```

### Performance

1. **Use `model_validate_json()`** em vez de `model_validate(json.loads(...))`
2. **Reutilize `TypeAdapter`** - não crie dentro de funções
3. **Use tipos específicos**: `list` vs `Sequence`, `dict` vs `Mapping`
4. **Evite wrap validators** se performance for crítica

---

## Azure SDK Python

### Singleton Pattern (Obrigatório)

**Princípio**: Clientes Azure devem ser tratados como singletons

```python
from functools import lru_cache
from azure.ai.textanalytics import TextAnalyticsClient
from azure.core.credentials import AzureKeyCredential

@lru_cache()
def get_text_analytics_client() -> TextAnalyticsClient:
    """Singleton TextAnalyticsClient."""
    credential = AzureKeyCredential(key)
    return TextAnalyticsClient(
        endpoint=endpoint,
        credential=credential,
        retry_policy=RetryPolicy(
            retry_total=3,
            retry_connect=3,
            retry_read=3,
            retry_status=3,
            backoff_factor=0.3,
            status_forcelist=[500, 502, 503, 504],
        ),
    )
```

### Thread Safety

Todos os clientes Azure SDK são **thread-safe** e podem ser compartilhados:

```python
class TextAnalysisService:
    def __init__(self):
        self._client = get_text_analytics_client()
    
    async def analyze(self, text: str):
        # Seguro usar em múltiplas threads
        return self._client.analyze_sentiment([text])
```

### Autenticação Recomendada

**Use `DefaultAzureCredential`** (token-based) em vez de connection strings:

```python
from azure.identity import DefaultAzureCredential

# Para apps hospedados no Azure: Usa Managed Identity
# Para desenvolvimento local: Fallback para Azure CLI, VS Code, etc.
credential = DefaultAzureCredential()

client = TextAnalyticsClient(
    endpoint=endpoint,
    credential=credential
)
```

### Retry Policy

Configure sempre uma retry policy:

```python
from azure.core.pipeline.policies import RetryPolicy

retry_policy = RetryPolicy(
    retry_total=3,
    retry_connect=3,
    retry_read=3,
    retry_status=3,
    backoff_factor=0.3,
    status_forcelist=[500, 502, 503, 504],
)
```

### Async Clients

Use `async with` para gerenciamento de recursos:

```python
from azure.storage.blob.aio import BlobServiceClient

async def download_blob():
    async with BlobServiceClient(...) as client:
        blob_client = client.get_blob_client(container, blob)
        async with blob_client:
            return await blob_client.download_blob()
```

---

## pytest

### Configuração (pyproject.toml)

```toml
[tool.pytest.ini_options]
asyncio_mode = "auto"
asyncio_default_fixture_loop_scope = "function"
testpaths = ["tests"]
python_files = ["test_*.py"]
python_classes = ["Test*"]
python_functions = ["test_*"]
addopts = "-v --tb=short --strict-markers"
markers = [
    "slow: marks tests as slow (deselect with '-m \"not slow\"')",
    "integration: marks tests as integration tests",
    "unit: marks tests as unit tests",
]
```

### Async Fixtures

**Sempre use `@pytest_asyncio.fixture`**, nunca `@pytest.fixture`:

```python
import pytest_asyncio

# ❌ Errado
# @pytest.fixture()

# ✅ Correto
@pytest_asyncio.fixture()
async def async_resource():
    await setup()
    yield resource
    await teardown()
```

### Session-Scoped Fixtures

```python
@pytest_asyncio.fixture(scope="session")
async def db_engine():
    """Criado uma vez para todos os testes."""
    engine = create_async_engine("postgresql+asyncpg://...")
    yield engine
    await engine.dispose()

@pytest_asyncio.fixture
async def db_connection(db_engine):
    """Criado para cada teste."""
    async with db_engine.connect() as conn:
        yield conn
```

### Mocking Async

```python
from unittest.mock import AsyncMock, patch

@pytest.mark.asyncio
async def test_external_api():
    with patch('module.client.get', AsyncMock(return_value={"data": "test"})):
        result = await fetch_data()
        assert result == {"data": "test"}
```

### Database Testing Pattern

```python
@pytest_asyncio.fixture
async def db_transaction(db_engine):
    """Rollback automático após cada teste."""
    async with db_engine.connect() as conn:
        async with conn.begin() as trans:
            yield conn
            await trans.rollback()  # Cleanup
```

---

## Poetry

### Comandos Essenciais

```bash
# Instalar dependências
poetry install

# Adicionar dependência
poetry add fastapi

# Adicionar dev dependency
poetry add --group dev pytest

# Atualizar
poetry update

# Shell interativo
poetry shell

# Executar comando
poetry run python script.py
poetry run pytest

# Exportar requirements.txt
poetry export -f requirements.txt --output requirements.txt
```

### Estrutura do pyproject.toml

```toml
[tool.poetry]
name = "multimodal-health-analysis"
version = "1.0.0"
description = "API multimodal para análise de saúde da mulher"
authors = ["Equipe Tech Challenge"]
readme = "README.md"

[tool.poetry.dependencies]
python = "^3.11"
fastapi = "^0.104.0"
uvicorn = {extras = ["standard"], version = "^0.24.0"}
pydantic = "^2.5.0"
pydantic-settings = "^2.1.0"
azure-ai-textanalytics = "^5.4.0"

[tool.poetry.group.dev.dependencies]
pytest = "^7.4.0"
pytest-asyncio = "^0.21.0"
httpx = "^0.25.0"
ruff = "^0.1.0"
mypy = "^1.7.0"

[build-system]
requires = ["poetry-core"]
build-backend = "poetry.core.masonry.api"
```

---

## Checklist de Implementação

### Antes de implementar qualquer funcionalidade:

- [ ] Consultou documentação oficial via Context7?
- [ ] Seguiu padrão singleton para clientes Azure?
- [ ] Usou `Annotated` para tipos reutilizáveis no Pydantic?
- [ ] Criou fixtures async com `@pytest_asyncio.fixture`?
- [ ] Validou tipos com mypy?
- [ ] Passou em todos os testes?
- [ ] Seguiu o linter (Ruff)?

---

## Fontes e Referências

- [FastAPI Dependency Injection](https://fastapi.tiangolo.com/tutorial/dependencies/)
- [Pydantic v2 Validators](https://docs.pydantic.dev/dev-v2/concepts/validators/)
- [Azure SDK Python Guidelines](https://learn.microsoft.com/en-us/azure/developer/python/sdk/fundamentals/language-design-guidelines)
- [pytest-asyncio Documentation](https://pytest-asyncio.readthedocs.io/)
- [Poetry Documentation](https://python-poetry.org/docs/)

---

**Última atualização**: 2026-04-11
**Próxima revisão**: Mensal ou após major releases das dependências

### Changelog 2026

- **2026-04-11**: Adicionadas práticas 2026 para Azure Text Analytics 5.4.0, FastAPI UV/dual-session, Pydantic v2 computed_field/TypeAdapter
