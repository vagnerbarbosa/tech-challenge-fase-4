# Task 009: Testes Unitários, Integração e Carga

## Objetivo

Implementar suite completa de testes automatizados com cobertura mínima de 70%, garantindo qualidade e confiabilidade antes do deploy em produção.

## Critérios de Aceite

### CA1: Testes Unitários
- [ ] Testes para todos os services (`src/services/`)
  - [ ] `text_analysis.py` - Testar integração Text Analytics
  - [ ] `audio_analysis.py` - Testar integração Speech Services
  - [ ] `image_analysis.py` - Testar integração Vision
  - [ ] `fusion.py` - Testar fusão multimodal
  - [ ] `video_frame_extractor.py` - Testar extração de frames
- [ ] Cobertura mínima 70% por módulo
- [ ] Mock de clientes Azure para testes unitários
- [ ] Fixtures reutilizáveis em `conftest.py`

### CA2: Testes de Integração
- [ ] Testes de API completa (`tests/integration/`)
  - [ ] `test_health.py` - Health check e métricas
  - [ ] `test_text_endpoint.py` - POST /analyze/text
  - [ ] `test_audio_endpoint.py` - POST /analyze/audio
  - [ ] `test_image_endpoint.py` - POST /analyze/image
  - [ ] `test_multimodal_endpoint.py` - POST /analyze/multimodal
- [ ] Testes com servidor FastAPI real (TestClient)
- [ ] Validação de schemas Pydantic
- [ ] Testes de erro (4xx, 5xx)

### CA3: Testes de Segurança
- [ ] Testes de autenticação (se Task 008 implementada)
- [ ] Testes de validação de arquivo
- [ ] Testes de rate limiting
- [ ] Testes de headers de segurança

### CA4: Testes de Carga (Locust)
- [ ] `tests/load/locustfile.py` configurado
- [ ] Cenários de teste:
  - [ ] Health check concorrente (100 usuários)
  - [ ] Análise de texto (50 usuários simultâneos)
  - [ ] Teste de stress (identificar gargalo)
- [ ] Métricas coletadas:
  - Response time (p95, p99)
  - Requests per second
  - Error rate
  - Azure quota consumption

### CA5: Cobertura de Código
- [ ] Cobertura global >= 70%
- [ ] Relatório HTML gerado (`htmlcov/index.html`)
- [ ] Exclusões configuradas (migrations, models)
- [ ] Falha de CI se cobertura < 70%

### CA6: Automação
- [ ] `pytest.ini` configurado
- [ ] Scripts de teste em `scripts/test.sh`
- [ ] GitHub Actions rodando testes em PR
- [ ] Makefile com comandos de teste

## Estrutura de Testes

```
tests/
├── __init__.py
├── conftest.py                    # Fixtures globais
├── unit/
│   ├── __init__.py
│   ├── services/
│   │   ├── test_text_analysis.py
│   │   ├── test_audio_analysis.py
│   │   ├── test_image_analysis.py
│   │   └── test_fusion.py
│   ├── utils/
│   │   └── test_file_validator.py
│   └── core/
│       ├── test_config.py
│       └── test_rate_limit.py
├── integration/
│   ├── __init__.py
│   ├── test_health.py
│   ├── test_text_endpoint.py
│   ├── test_audio_endpoint.py
│   ├── test_image_endpoint.py
│   ├── test_multimodal_endpoint.py
│   └── test_security.py
└── load/
    ├── __init__.py
    └── locustfile.py
```

## Configuração pytest.ini

```ini
[pytest]
testpaths = tests
python_files = test_*.py
python_classes = Test*
python_functions = test_*
asyncio_mode = auto
addopts =
    -v
    --strict-markers
    --tb=short
    --cov=src
    --cov-report=term-missing
    --cov-report=html:htmlcov
    --cov-report=xml:coverage.xml
    --cov-fail-under=70

markers =
    unit: Unit tests (mocked)
    integration: Integration tests (require API)
    slow: Slow tests (Azure calls)
    azure: Tests requiring Azure credentials
    security: Security tests
    load: Load tests (Locust)
```

## Scripts

### scripts/test.sh
```bash
#!/bin/bash
set -e

echo "=== Running Unit Tests ==="
poetry run pytest tests/unit -v -m "not slow"

echo "=== Running Integration Tests ==="
poetry run pytest tests/integration -v --cov-append

echo "=== Coverage Report ==="
poetry run pytest --cov=src --cov-report=html --cov-report=term
```

## Locustfile Template

```python
# tests/load/locustfile.py
from locust import HttpUser, task, between

class HealthUser(HttpUser):
    wait_time = between(1, 3)

    @task(3)
    def health_check(self):
        self.client.get("/health")

    @task(1)
    def analyze_text(self):
        self.client.post(
            "/analyze/text",
            json={"texto": "Texto de teste para carga"}
        )
```

## Dependências

- Task 001: Bootstrap (estrutura)
- Task 002-006: Endpoints funcionais
- Task 008: Security Hardening (para testes de segurança)

## Bloqueia

- Task 010: Deploy Azure (testes devem passar antes do deploy)

## Estimativa

**Pontuação**: 5 pontos
**Tempo estimado**: 4-6 horas
