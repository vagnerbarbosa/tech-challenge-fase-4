# Feature Specification: Estratégia de Testes Híbrida

**Feature Branch**: `[011-testing-strategy]`  
**Created**: 2026-05-03  
**Status**: ⏳ PLANNED  
**Input**: Análise de viabilidade de 90% cobertura + testes E2E

---

## Overview

Especificação para elevar cobertura de testes de **81.61% para 90%** através de estratégia híbrida:
- **Unit tests**: Cobertura de rotas críticas e edge cases
- **Integration tests**: Validação de endpoints com mocks
- **E2E tests**: Fluxos completos com infraestrutura real (Docker)

**Meta**: 90% cobertura + 6-8 testes E2E robustos em 3 semanas

---

## Current State Analysis

### Cobertura Atual (81.61%)

| Categoria | Arquivos | Cobertura | Prioridade |
|-----------|----------|-----------|------------|
| Services | audio_analysis, text_analysis, video_analysis | 95-100% | ✅ Mantém |
| Infrastructure | azure_clients, content_safety | 99-100% | ✅ Mantém |
| Models | schemas, audit_log | 84-96% | 🟡 Opcional |
| **Routes** | **multimodal, audio, video** | **19-28%** | **🔴 Crítico** |
| Utils | audit_logger, file_validation | 61-67% | 🟡 Importante |
| Security | rate_limiter | 69% | 🟡 Importante |

**Gap para 90%**: ~330 statements (de 3.757 totais)

---

## Phase 1: Unit Tests - Rotas Críticas (Semana 1)

### Objetivo
Elevar cobertura das rotas de 19-28% para 80%+

### Arquivos a Criar

```
tests/unit/routes/
├── __init__.py
├── test_multimodal.py              # 15 testes
├── test_multimodal_edge_cases.py   # 8 testes
├── test_audio_edge_cases.py        # 10 testes
├── test_video_edge_cases.py        # 8 testes
└── conftest.py                     # Fixtures específicas
```

### Test Cases: Multimodal

**T001**: POST /analyze/multimodal com texto apenas → 200
```python
def test_multimodal_text_only_success(client):
    """Texto simples retorna fusão válida."""
    response = client.post("/analyze/multimodal", data={
        "texto": "Estou ansiosa"
    })
    assert response.status_code == 200
    assert "fusao" in response.json()
    assert response.json()["fusao"]["risco_violencia"] in ["baixo", "medio", "alto"]
```

**T002**: POST sem nenhuma modalidade → 400
**T003**: POST com texto + áudio → 200 (ambos processados)
**T004**: POST com timeout simulado → 504
**T005**: Rate limit de texto → 429
**T006**: Rate limit de áudio → 429
**T007**: Cleanup de arquivos temp após erro
**T008**: Patient ID propagado para audit log

### Test Cases: Audio Edge Cases

**T009**: Arquivo WAV válido → 200
**T010**: Arquivo MP3 com metadados → 200
**T011**: Arquivo OGG → 200
**T012**: Azure Speech indisponível → 503
**T013**: Content Safety indisponível → usa keywords
**T014**: Auto-detecção de idioma (es-ES)
**T015**: Transcrição vazia → retorna warning
**T016**: Vídeo muito grande → 413

---

## Phase 2: Utils & Security (Semana 1-2)

### File Validation (61% → 85%)

```
tests/unit/utils/
├── test_file_validation_magic.py       # Com python-magic
└── test_file_validation_fallback.py     # Sem python-magic
```

**T017**: Magic numbers WAV válidos
**T018**: Magic numbers MP3 válidos (ÿû e ID3)
**T019**: Magic numbers OGG válidos
**T020**: Extensão/MIME mismatch → warning
**T021**: Streaming validation (chunks)
**T022**: Fallback sem python-magic (3 formatos)

### Audit Logger (67% → 85%)

```
tests/unit/utils/
├── test_audit_rotation.py
├── test_audit_checksum.py
└── test_audit_integrity.py
```

**T023**: Rotação por tamanho (10MB)
**T024**: Rotação por tempo (365 dias)
**T025**: Checksum SHA-256 válido
**T026**: Verificação de integridade detecta tampering
**T027**: Compactação gzip de logs antigos
**T028**: Thread-safe logging (concorrência)

### Rate Limiter (69% → 85%)

**T029**: Token bucket refill
**T030**: Quota diária excedida → bloqueio
**T031**: Quota mensal excedida → bloqueio
**T032**: Reset de quota após janela
**T033**: Persistência em SQLite

---

## Phase 3: Integration Tests (Semana 2)

### Melhorias nos Existentes

Arquivos existentes para expandir:
- `test_multimodal_endpoint.py` (adicionar 5 testes)
- `test_audio_endpoint.py` (adicionar 6 testes)
- `test_content_safety_integration.py` (adicionar 4 testes)

### Novos Test Cases de Integração

**T034**: Análise multimodal com timeout de 90s
```python
@pytest.mark.asyncio
async def test_multimodal_timeout_simulation(async_client):
    """Timeout global de 90s funciona."""
    with patch("asyncio.timeout", side_effect=TimeoutError):
        response = await async_client.post("/analyze/multimodal", data={"texto": "test"})
    assert response.status_code == 504
```

**T035**: Azure Speech auto-detect idioma
**T036**: Content Safety + Keywords combinados
**T037**: Cache de vídeo (stats/clear)
**T038**: Admin endpoints com RBAC

---

## Phase 4: E2E Tests (Semana 2-3)

### Arquitetura E2E - Slim (Opção A)

**Decisão**: Usar apenas E2E Slim (~3GB) sem vídeo devido ao tamanho da imagem completa (13GB).

**Justificativa:**
- Imagem full com YOLOv8/PyTorch: **~13GB** (demora 10-15min para build no CI)
- Imagem E2E slim (texto + áudio): **~3GB** (demora 3-5min para build no CI)
- Testes de vídeo são cobertos por testes de integração existentes
- E2E foca em testar fluxos completos de texto e áudio + segurança

**Escopo do E2E:**
- ✅ Análise de texto (Azure Text + Content Safety)
- ✅ Análise de áudio (Azure Speech + transcrição)
- ✅ Multimodal texto + áudio
- ✅ Segurança e LGPD
- ❌ Vídeo (coberto por testes de integração)

```
tests/e2e/
├── conftest.py                      # Setup/teardown containers
├── test_flow_text_analysis.py       # Fluxo texto (E2E-001 a E2E-003)
├── test_flow_audio_analysis.py      # Fluxo áudio (E2E-004 a E2E-006)
├── test_flow_multimodal_text_audio.py  # Multimodal sem vídeo (E2E-007)
├── test_flow_security.py            # Segurança + LGPD (E2E-008 a E2E-010)
├── fixtures/
│   ├── docker-compose.e2e.yml     # Configuração isolada
│   └── sample_files/
│       ├── text_samples.json
│       └── audio_sample.wav
└── Dockerfile.e2e                  # Imagem otimizada (~3GB)
```

### Configuração E2E

**docker-compose.e2e.yml** (Slim - Sem vídeo):
```yaml
version: '3.8'
services:
  api-e2e:
    build: 
      context: ../..
      dockerfile: tests/e2e/Dockerfile.e2e  # Usa Dockerfile slim
    environment:
      - ENVIRONMENT=testing
      - MOCK_MODE=true
      - LOG_LEVEL=INFO
      - SECURITY_API_KEY=test-api-key
      - SECURITY_ADMIN_KEY=test-admin-key
    ports:
      - "9000:8000"
    volumes:
      - ./fixtures:/fixtures:ro
      - e2e_logs:/app/logs
    healthcheck:
      test: ["CMD", "curl", "-f", "http://localhost:8000/health"]
      interval: 5s
      timeout: 5s
      retries: 10
      start_period: 10s

volumes:
  e2e_logs:
```

### Teste E2E: Text Analysis Flow

**E2E-001**: Fluxo completo texto → análise → audit
```python
# tests/e2e/test_flow_text_analysis.py
import requests
import pytest
import time


class TestTextAnalysisE2E:
    """E2E-001 a E2E-003: Fluxos de análise de texto."""
    
    def test_texto_detecta_risco_saude_mental(self, e2e_api_url, api_key):
        """E2E-001: Texto com ansiedade detecta risco."""
        # Arrange
        payload = {
            "texto": "Estou me sentindo muito ansiosa e com medo constante",
            "tipo": "diario",
            "patient_id": "e2e-patient-001"
        }
        headers = {"X-API-Key": api_key}
        
        # Act
        start_time = time.time()
        response = requests.post(
            f"{e2e_api_url}/analyze/text",
            json=payload,
            headers=headers,
            timeout=30
        )
        duration = time.time() - start_time
        
        # Assert Response
        assert response.status_code == 200
        data = response.json()
        
        # Verificações de negócio
        assert data["risco_saude_mental"] in ["medio", "alto"]
        assert data["sentimento"] == "negativo"
        assert data["score"] < 0  # Score negativo
        assert "content_safety" in data  # Content Safety presente
        
        # Verificações de performance
        assert duration < 5.0, f"Demorou {duration}s, esperado <5s"
        
        # Verificações de rastreabilidade (LGPD)
        assert "metadata" in data
        assert "correlation_id" in data["metadata"]
        correlation_id = data["metadata"]["correlation_id"]
        
        # Verifica audit log foi criado
        audit_response = requests.get(
            f"{e2e_api_url}/admin/audit/stats",
            headers={"X-API-Key": api_key}  # Admin key
        )
        assert audit_response.status_code == 200
```

### Dockerfile E2E Slim

Imagem otimizada sem vídeo (~3GB vs 13GB):

```dockerfile
# tests/e2e/Dockerfile.e2e
# Imagem E2E Slim: apenas texto + áudio (sem vídeo/YOLO)
FROM python:3.11-slim

# Variáveis de ambiente
ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    APP_HOME=/app \
    PORT=8000 \
    MOCK_MODE=true

# Instalar apenas dependências de texto + áudio (sem OpenCV/PyTorch)
RUN apt-get update \
    && apt-get install -y --no-install-recommends \
        libsndfile1 \
        ffmpeg \
        libmagic1 \
        curl \
    && rm -rf /var/lib/apt/lists/*

# Diretório de trabalho
WORKDIR $APP_HOME

# Instalar Poetry
RUN pip install --no-cache-dir poetry

# Copiar dependências
COPY pyproject.toml poetry.lock ./

# Instalar apenas deps de texto + áudio (sem [video] extra)
RUN poetry config virtualenvs.create false \
    && poetry install --no-root --without dev --extras "security" \
    && rm -rf /root/.cache/pypoetry

# Copiar código
COPY src/ ./src/
COPY scripts/download_yolo_model.py ./scripts/
COPY entrypoint.sh ./

# Criar diretórios
RUN mkdir -p /tmp/health-api /app/logs/audit \
    && chmod +x entrypoint.sh

# Health check
HEALTHCHECK --interval=5s --timeout=5s --start-period=10s --retries=5 \
    CMD curl -f http://localhost:8000/health || exit 1

EXPOSE $PORT

CMD ["uvicorn", "src.api.main:app", "--host", "0.0.0.0", "--port", "8000", "--log-level", "info"]
```

**Tamanho estimado**: ~3GB (vs 13GB da imagem full)
    
    def test_texto_idioma_espanhol(self, e2e_api_url, api_key):
        """E2E-002: Texto em espanhol detecta risco sem configuração."""
        payload = {
            "texto": "Tengo mucho miedo y estoy muy ansiosa",
            "tipo": "consulta"
        }
        headers = {"X-API-Key": api_key}
        
        response = requests.post(
            f"{e2e_api_url}/analyze/text",
            json=payload,
            headers=headers
        )
        
        assert response.status_code == 200
        data = response.json()
        # Deve funcionar sem especificar idioma (auto-detect)
        assert data["risco_saude_mental"] in ["baixo", "medio", "alto"]
    
    def test_rate_limiting_60_requests(self, e2e_api_url, api_key):
        """E2E-003: 60+ requisições acionam rate limit 429."""
        headers = {"X-API-Key": api_key}
        responses = []
        
        # Faz 65 requisições rápidas
        for i in range(65):
            response = requests.post(
                f"{e2e_api_url}/analyze/text",
                json={"texto": f"Texto {i}"},
                headers=headers
            )
            responses.append(response.status_code)
        
        # Pelo menos uma deve ser 429
        assert 429 in responses, "Rate limit não acionou"
        
        # Verifica headers de rate limit
        last_response = requests.post(
            f"{e2e_api_url}/analyze/text",
            json={"texto": "final"},
            headers=headers
        )
        assert "X-RateLimit-Limit" in last_response.headers
```

### Teste E2E: Audio Analysis Flow

**E2E-004 a E2E-006**: Fluxos de áudio
```python
# tests/e2e/test_flow_audio_analysis.py
class TestAudioAnalysisE2E:
    """E2E-004 a E2E-006: Análise de áudio end-to-end."""
    
    def test_audio_transcricao_e_risco(self, e2e_api_url, api_key, audio_fixture):
        """E2E-004: Áudio transcrito e analisado para risco."""
        headers = {"X-API-Key": api_key}
        
        with open(audio_fixture, "rb") as f:
            response = requests.post(
                f"{e2e_api_url}/analyze/audio",
                files={"audio": ("sample.wav", f, "audio/wav")},
                data={"patient_id": "e2e-audio-001"},
                headers=headers
            )
        
        assert response.status_code == 200
        data = response.json()
        
        # Verificações
        assert "transcricao" in data
        assert data["idioma_detectado"] in ["pt-BR", "en-US", "es-ES", "fr-FR"]
        assert data["risco_violencia"] in ["baixo", "medio", "alto"]
        assert data["risco_saude_mental"] in ["baixo", "medio", "alto"]
        assert "voz_tremida" in data
        assert "pausas_suspeitas" in data
        assert "metadata" in data
        assert data["metadata"]["tempo_processamento_ms"] > 0
    
    def test_audio_formatos_suportados(self, e2e_api_url, api_key):
        """E2E-005: WAV, MP3, OGG aceitos."""
        headers = {"X-API-Key": api_key}
        formats = [
            ("sample.wav", "audio/wav"),
            ("sample.mp3", "audio/mpeg"),
            ("sample.ogg", "audio/ogg"),
        ]
        
        for filename, content_type in formats:
            file_path = f"tests/e2e/fixtures/{filename}"
            with open(file_path, "rb") as f:
                response = requests.post(
                    f"{e2e_api_url}/analyze/audio",
                    files={"audio": (filename, f, content_type)},
                    headers=headers
                )
            assert response.status_code == 200, f"Formato {filename} falhou"
    
    def test_audio_arquivo_muito_grande(self, e2e_api_url, api_key):
        """E2E-006: Arquivo >50MB rejeitado com 413."""
        headers = {"X-API-Key": api_key}
        
        # Criar arquivo temporário grande
        import tempfile
        with tempfile.NamedTemporaryFile(suffix=".wav", delete=False) as f:
            f.write(b"RIFF" + b"\x00" * (51 * 1024 * 1024))  # 51MB
            temp_path = f.name
        
        with open(temp_path, "rb") as f:
            response = requests.post(
                f"{e2e_api_url}/analyze/audio",
                files={"audio": ("large.wav", f, "audio/wav")},
                headers=headers
            )
        
        assert response.status_code == 413
        assert "muito grande" in response.json()["detail"].lower()
```

### Teste E2E: Multimodal Flow

**E2E-007**: Fluxo completo com 3 modalidades
```python
# tests/e2e/test_flow_multimodal.py
class TestMultimodalE2E:
    """E2E-007: Fluxo multimodal completo."""
    
    def test_tres_modalidades_fusao(self, e2e_api_url, api_key, 
                                     audio_fixture, video_fixture):
        """E2E-007: Texto + Áudio + Vídeo → fusão ponderada."""
        headers = {"X-API-Key": api_key}
        
        with open(audio_fixture, "rb") as af, open(video_fixture, "rb") as vf:
            response = requests.post(
                f"{e2e_api_url}/analyze/multimodal",
                data={"texto": "Estou com medo e ansiosa", "patient_id": "mm-001"},
                files={
                    "audio": ("audio.wav", af, "audio/wav"),
                    "video": ("video.mp4", vf, "video/mp4")
                },
                headers=headers
            )
        
        assert response.status_code == 200
        data = response.json()
        
        # Estrutura completa
        assert "fusao" in data
        assert "texto" in data
        assert "audio" in data
        assert "video" in data
        assert "metadata" in data
        
        # Valida fusão
        fusion = data["fusao"]
        assert "risco_violencia" in fusion
        assert "risco_saude_mental" in fusion
        assert "confianca" in fusion
        assert "alerta" in fusion
        assert 0 <= fusion["confianca"] <= 1
        
        # Modalidades processadas
        modalities = data["metadata"]["modalidades_processadas"]
        assert set(modalities) == {"texto", "audio", "video"}
        
        # Tempo de processamento < 90s
        assert data["metadata"]["tempo_processamento_ms"] < 90000
```

### Teste E2E: Security & LGPD

**E2E-008 a E2E-010**: Segurança e conformidade
```python
# tests/e2e/test_flow_security.py
class TestSecurityE2E:
    """E2E-008 a E2E-010: Segurança e LGPD."""
    
    def test_api_key_invalida_rejeitada(self, e2e_api_url):
        """E2E-008: API Key inválida → 401."""
        response = requests.post(
            f"{e2e_api_url}/analyze/text",
            json={"texto": "test"},
            headers={"X-API-Key": "invalid-key"}
        )
        assert response.status_code == 401
    
    def test_patient_id_hash_no_log(self, e2e_api_url, api_key):
        """E2E-009: Patient ID hasheado em logs (LGPD)."""
        patient_id = "sensitive-patient-123"
        
        response = requests.post(
            f"{e2e_api_url}/analyze/text",
            json={"texto": "test", "patient_id": patient_id},
            headers={"X-API-Key": api_key}
        )
        
        assert response.status_code == 200
        correlation_id = response.json()["metadata"]["correlation_id"]
        
        # Verifica audit log - patient_id deve estar hasheado
        audit_response = requests.get(
            f"{e2e_api_url}/admin/audit/export",
            headers={"X-API-Key": api_key},
            params={"correlation_id": correlation_id}
        )
        
        # Patient ID original não deve aparecer
        assert patient_id not in audit_response.text
    
    def test_cors_production(self, e2e_api_url):
        """E2E-010: CORS restritivo em produção."""
        response = requests.options(
            f"{e2e_api_url}/analyze/text",
            headers={
                "Origin": "https://unauthorized-domain.com",
                "Access-Control-Request-Method": "POST"
            }
        )
        
        # CORS deve bloquear
        assert "Access-Control-Allow-Origin" not in response.headers or \
               response.headers.get("Access-Control-Allow-Origin") != "https://unauthorized-domain.com"
```

### Fixtures E2E

**conftest.py**:
```python
# tests/e2e/conftest.py
"""Fixtures para testes E2E com Docker."""

import subprocess
import time
import pytest
import requests


@pytest.fixture(scope="session")
def docker_compose_file(pytestconfig):
    """Retorna caminho do docker-compose E2E."""
    return pytestconfig.rootpath / "tests" / "e2e" / "fixtures" / "docker-compose.e2e.yml"


@pytest.fixture(scope="session")
def e2e_api_url(docker_compose_file):
    """Sobe containers E2E e retorna URL da API."""
    # Setup
    subprocess.run(
        ["docker-compose", "-f", str(docker_compose_file), "up", "-d", "--build"],
        check=True,
        capture_output=True
    )
    
    # Aguarda health check
    url = "http://localhost:9000"
    for _ in range(30):
        try:
            resp = requests.get(f"{url}/health", timeout=2)
            if resp.status_code == 200:
                break
        except requests.exceptions.ConnectionError:
            time.sleep(1)
    else:
        # Teardown em caso de falha
        subprocess.run(
            ["docker-compose", "-f", str(docker_compose_file), "down"],
            capture_output=True
        )
        pytest.fail("API E2E não iniciou")
    
    yield url
    
    # Teardown
    subprocess.run(
        ["docker-compose", "-f", str(docker_compose_file), "down", "-v"],
        capture_output=True
    )


@pytest.fixture(scope="session")
def api_key():
    """Retorna API key de teste."""
    return "test-api-key"  # Deve corresponder ao mock


@pytest.fixture(scope="session")
def audio_fixture():
    """Retorna caminho para arquivo de áudio de teste."""
    return "tests/e2e/fixtures/sample.wav"


@pytest.fixture(scope="session")
def video_fixture():
    """Retorna caminho para arquivo de vídeo de teste."""
    return "tests/e2e/fixtures/sample.mp4"
```

---

## Execução dos Testes

### Local

```bash
# Unit + Integration (rápido)
poetry run pytest tests/unit tests/integration -v

# E2E (requer Docker - builda imagem slim)
docker build -f tests/e2e/Dockerfile.e2e -t api:e2e .
docker run -d -p 9000:8000 api:e2e
poetry run pytest tests/e2e -v --timeout=300

# Todos com cobertura
poetry run pytest --cov=src --cov-report=html
```

### CI/CD

**.github/workflows/test.yml** - Unit + Integration (todo PR):
```yaml
name: Test Suite

on:
  push:
    branches: [main]
  pull_request:
    branches: [main]

jobs:
  unit-integration:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      - name: Setup Python
        uses: actions/setup-python@v4
        with:
          python-version: '3.11'
      - name: Install Poetry
        uses: snok/install-poetry@v1
      - name: Install dependencies
        run: poetry install
      - name: Run unit and integration tests
        run: poetry run pytest tests/unit tests/integration --cov=src --cov-report=xml
      - name: Upload coverage
        uses: codecov/codecov-action@v3
        with:
          file: ./coverage.xml
          fail_ci_if_error: true
```

**.github/workflows/e2e.yml** - E2E Slim (apenas quando necessário):
```yaml
name: E2E Tests

on:
  pull_request:
    branches: [main]
    paths:
      - 'src/api/routes/**'     # Mudou rotas
      - 'src/services/**'       # Mudou serviços
      - 'tests/e2e/**'          # Mudou testes E2E
  workflow_dispatch:            # Manual

jobs:
  e2e-slim:
    name: E2E Slim (Texto + Áudio)
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      
      - name: Setup Docker
        uses: docker/setup-buildx-action@v3
      
      - name: Cache Docker layers
        uses: actions/cache@v3
        with:
          path: /tmp/.buildx-cache
          key: ${{ runner.os }}-buildx-${{ hashFiles('tests/e2e/Dockerfile.e2e', 'pyproject.toml') }}
          restore-keys: |
            ${{ runner.os }}-buildx-
      
      - name: Build E2E slim image
        run: |
          docker build \
            -f tests/e2e/Dockerfile.e2e \
            -t api:e2e \
            --cache-from type=local,src=/tmp/.buildx-cache \
            --cache-to type=local,dest=/tmp/.buildx-cache-new,mode=max \
            .
          mv /tmp/.buildx-cache-new /tmp/.buildx-cache || true
      
      - name: Run API container
        run: |
          docker run -d \
            -p 9000:8000 \
            -e MOCK_MODE=true \
            -e SECURITY_API_KEY=test-api-key \
            -e SECURITY_ADMIN_KEY=test-admin-key \
            --name api-e2e \
            api:e2e
      
      - name: Wait for health check
        run: |
          for i in {1..30}; do
            curl -sf http://localhost:9000/health && echo "API ready" && exit 0
            sleep 2
          done
          echo "API failed to start"
          docker logs api-e2e
          exit 1
      
      - name: Install Python dependencies for tests
        run: |
          pip install pytest pytest-asyncio requests structlog
      
      - name: Run E2E tests
        env:
          E2E_API_URL: http://localhost:9000
          E2E_API_KEY: test-api-key
        run: |
          pytest tests/e2e/ -v --tb=short
      
      - name: Cleanup
        if: always()
        run: |
          docker stop api-e2e || true
          docker rm api-e2e || true
```

---

## Métricas de Sucesso

| Métrica | Atual | Meta | Como Medir |
|---------|-------|------|------------|
| Cobertura geral | 81.61% | 90% | `pytest --cov` |
| Cobertura rotas | 19-28% | 80% | `pytest --cov=src/api/routes` |
| Testes E2E | 0 | 6-8 | Contagem manual |
| Tempo CI (unit+int) | ~2min | <5min | GitHub Actions |
| Tempo CI (e2e) | N/A | <10min | GitHub Actions |
| Flaky tests | N/A | <5% | Monitoramento |

---

## Riscos e Mitigações

| Risco | Probabilidade | Mitigação |
|-------|---------------|-----------|
| E2E instáveis (Docker) | Alta | Mock mode + health checks robustos |
| Cobertura 90% difícil | Média | Focar em rotas, aceitar 88% se necessário |
| Tempo CI excessivo | Média | Rodar E2E apenas em PRs para main |
| Manutenção de mocks | Alta | Documentar contratos, revisar periodicamente |
| **Imagem muito pesada** | **Alta** | **Usar Dockerfile.e2e slim (~3GB vs 13GB)** |
| Vídeo não testado em E2E | Média | Testes de integração cobrem; nightly opcional (futuro) |

---

## Melhorias Futuras

### Nightly E2E Full (Opcional)

**Quando**: Após estabilização do E2E Slim

**Objetivo**: Testar ocasionalmente com imagem completa incluindo vídeo/YOLO

```yaml
# .github/workflows/e2e-nightly.yml (futuro)
name: E2E Nightly (Full)

on:
  schedule:
    - cron: '0 3 * * *'  # 3AM UTC

jobs:
  e2e-full:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      - name: Pull production image
        run: docker pull ghcr.io/vagnerbarbosa/tech-challenge-fase4:latest
      - name: Run full E2E with video
        run: |
          docker run -d -p 9000:8000 ghcr.io/vagnerbarbosa/tech-challenge-fase4:latest
          pytest tests/e2e/ tests/e2e-video/ -v
```

**Benefícios:**
- Valida vídeo/YOLO em ambiente próximo à produção
- Detecta regressões em dependências pesadas (PyTorch, OpenCV)
- Não bloqueia PRs (risco de instabilidade aceitável)

---

## Referências

- Spec 008: Testes existentes
- Spec 003: Audio Analysis (contexto)
- Spec 005: Multimodal Fusion (contexto)
- docs/technical/testing-guide.md (a criar)

---

**Próximos passos**: Implementar Phase 1 (Unit tests de rotas) → Validar cobertura → Implementar E2E

---

## Clarifications

### Session 2026-05-03

- **Q**: Qual a ordem de prioridade para implementação dos testes de rotas? → **A**: Rotas com menor cobertura primeiro (multimodal → audio → video)
- **Q**: Qual é o limite mínimo aceitável de cobertura se 90% não for atingível? → **A**: 88-90% é aceitável se rotas >80%
- **Q**: Em quais condições exatas o workflow E2E deve ser acionado no CI? → **A**: Apenas quando rotas/serviços/E2E mudem (otimização CI)
- **Q**: Qual estratégia de testes de fixtures (áudio/vídeo) para E2E? → **A**: Arquivos sintéticos pequenos (<1MB cada) para velocidade
- **Q**: Como tratar o gap de E2E para vídeo (não coberto no slim)? → **A**: Aceitar gap e confiar em testes de integração existentes
