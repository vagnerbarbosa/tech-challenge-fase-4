# Documentação de Testes

> **Última Atualização**: 2026-05-03

Este documento descreve a estratégia de testes do projeto Multimodal Health Analysis API, incluindo testes unitários, de integração e E2E (End-to-End).

---

## Visão Geral

A suite de testes está organizada em camadas que garantem qualidade em diferentes níveis:

| Tipo | Diretório | Propósito | Cobertura |
|------|-----------|-----------|-----------|
| **Unitários** | `tests/unit/` | Testar funções e classes isoladamente | ~85% |
| **Integração** | `tests/integration/` | Testar interação entre componentes | Endpoints principais |
| **E2E** | `tests/e2e/` | Testar fluxos completos com Docker | 10 fluxos |
| **Segurança** | `tests/security/` | Testes específicos de segurança | 87 tarefas |
| **Carga** | `tests/load/` | Testes de performance (Locust) | Opcional |

---

## Executando os Testes

### Scripts Disponíveis

O projeto inclui scripts automatizados para facilitar a execução de testes:

| Script | Descrição | Quando usar |
|--------|-----------|-------------|
| `./scripts/test.sh` | Testes unitários locais com Poetry | Desenvolvimento rápido |
| `./scripts/test-docker.sh` | Testes em Docker (reutiliza imagem) | Isolamento completo |
| `./scripts/run-e2e.sh` | Testes E2E com Docker | Fluxos end-to-end |
| `./scripts/run-mock.sh` | Inicia ambiente com mocks | Desenvolvimento |

### Testes Unitários e Integração

```bash
# Todos os testes (exceto E2E)
poetry run pytest tests/ --ignore=tests/e2e/ -v

# Com cobertura
poetry run pytest tests/ --ignore=tests/e2e/ --cov=src --cov-report=html

# Apenas testes unitários
poetry run pytest tests/unit/ -v

# Apenas testes de integração
poetry run pytest tests/integration/ -v

# Testes de segurança
poetry run pytest tests/security/ -v
```

### Testes E2E

Os testes E2E requerem Docker pois testam a aplicação completa em um ambiente isolado:

```bash
# Via script (recomendado) - gerencia todo o ciclo de vida
./scripts/run-e2e.sh

# Com opções adicionais
./scripts/run-e2e.sh --logs      # Mostra logs após execução
./scripts/run-e2e.sh --rebuild # Força rebuild da imagem
./scripts/run-e2e.sh --stop      # Para containers E2E

# Manualmente
cd tests/e2e/fixtures
docker compose -f docker-compose.e2e.yml up --build -d
poetry run pytest tests/e2e/ -v
docker compose -f docker-compose.e2e.yml down
```

---

## Estrutura dos Testes

### Testes Unitários (`tests/unit/`)

Testam componentes isolados com mocks para dependências externas.

```
tests/unit/
├── routes/              # Testes de rotas da API
│   ├── test_audio.py
│   ├── test_multimodal.py
│   ├── test_text.py
│   └── test_video.py
├── services/            # Testes de serviços de negócio
│   ├── test_audio_analysis.py
│   ├── test_multimodal_fusion.py
│   ├── test_text_analysis.py
│   └── test_video_analysis.py
└── utils/               # Testes de utilitários
    ├── test_audit_integrity.py
    └── test_file_validation.py
```

**Exemplo**:
```python
def test_analyze_text_success(mock_text_service):
    """Testa análise de texto com sucesso."""
    response = client.post("/analyze/text", json={
        "texto": "Estou me sentindo ansiosa",
        "tipo": "diario"
    })
    assert response.status_code == 200
    assert "risco_saude_mental" in response.json()
```

### Testes de Integração (`tests/integration/`)

Testam a API como um todo, mas com serviços Azure mockados.

```
tests/integration/
├── test_audio_endpoint.py
├── test_auth.py
├── test_health.py
├── test_multimodal_endpoint.py
└── test_text_endpoint.py
```

**Características**:
- Usam `TestClient` do FastAPI
- Mockam serviços Azure (não consomem quota)
- Testam serialização/deserialização
- Validam schemas Pydantic

### Testes E2E (`tests/e2e/`)

Testam fluxos completos em ambiente Dockerizado, simulando uso real.

```
tests/e2e/
├── conftest.py                    # Fixtures E2E
├── fixtures/
│   ├── docker-compose.e2e.yml   # Infraestrutura Docker
│   └── sample_files/              # Arquivos de teste
├── test_flow_audio_analysis.py    # E2E-004 a E2E-006
├── test_flow_multimodal_text_audio.py  # E2E-007
├── test_flow_security.py          # E2E-008 a E2E-010
└── test_flow_text_analysis.py     # E2E-001 a E2E-003
```

**Fluxos Testados**:

| ID | Fluxo | Descrição |
|----|-------|-----------|
| E2E-001 | Análise Completa de Texto | Valida sentimento, risco, content_safety |
| E2E-002 | Auto-detecção de Idioma | Espanhol detectado automaticamente |
| E2E-003 | Rate Limiting | 60+ requisições, valida 429 |
| E2E-004 | Transcrição de Áudio | WAV, valida prosódica |
| E2E-005 | Múltiplos Formatos | WAV, MP3, OGG aceitos |
| E2E-006 | Validação de Tamanho | Rejeição >50MB (413) |
| E2E-007 | Fusão Multimodal | Texto + áudio, valida confiança |
| E2E-008 | Autenticação | 401 sem API Key |
| E2E-009 | LGPD | Hash de patient_id em logs |
| E2E-010 | Rate Limit por API Key | Headers X-RateLimit-* |

---

## Configuração do Ambiente E2E

O ambiente E2E usa Docker Compose com uma imagem slim (~3GB) sem YOLO/PyTorch:

```yaml
# tests/e2e/fixtures/docker-compose.e2e.yml
services:
  api-e2e:
    build:
      dockerfile: tests/e2e/Dockerfile.e2e  # Imagem slim
    environment:
      - MOCK_MODE=true                      # Modo mock ativado
      - RATE_LIMIT_ENABLED=false            # Desabilitado para E2E
    ports:
      - "9000:8000"
```

**Dockerfile E2E** (`tests/e2e/Dockerfile.e2e`):
- Base: `python:3.11-slim`
- Sem YOLO/PyTorch (reduz de ~13GB para ~3GB)
- Inclui apenas dependências de áudio/texto
- Mock mode por padrão

---

## CI/CD e Automação

### GitHub Actions

| Workflow | Arquivo | Descrição |
|----------|---------|-----------|
| **Unit & Integration** | `.github/workflows/ci.yml` | Roda em todo PR |
| **E2E Tests** | `.github/workflows/e2e.yml` | Roda em PRs e push |

**Status**: Veja os badges no [README](../README.md).

### Estratégia de Execução

```
CI (Pull Request)
├── Unit Tests (pytest tests/unit/)
├── Integration Tests (pytest tests/integration/)
├── Security Tests (pytest tests/security/)
├── Lint (ruff)
└── Type Check (mypy)

E2E (Pull Request + Push)
├── Build Docker Image (slim)
├── Start Services (docker compose)
├── Run E2E Tests (pytest tests/e2e/)
└── Upload Logs (em caso de falha)
```

---

## Convenções de Teste

### Nomenclatura

```python
# Arquivos: test_<modulo>.py
test_audio_analysis.py
test_flow_text_analysis.py

# Classes: Test<Descritivo>
class TestAudioAnalysis:
class TestE2ETextAnalysis:

# Métodos: test_<condicao>[_<resultado>]
def test_analyze_text_success():
def test_invalid_audio_format_returns_400():
```

### Fixtures Compartilhadas

**Unit/Integration** (`tests/unit/routes/conftest.py`):
- `client`: TestClient do FastAPI
- `auth_headers`: Headers com API Key de teste
- `mock_azure_services`: Mock automático de Azure
- `sample_audio_file`: Arquivo WAV temporário

**E2E** (`tests/e2e/conftest.py`):
- `e2e_client`: Session do requests
- `api_url`: URL da API E2E (`http://localhost:9000`)
- `sample_audio_path`: Caminho para arquivo de teste
- `admin_headers`: Autenticação admin

### Asserções Comuns

```python
# Status codes
assert response.status_code == 200

# Schema validation
data = response.json()
assert "risco_violencia" in data
assert data["risco_violencia"] in ["baixo", "medio", "alto"]

# Performance
assert duration < 5.0  # segundos

# Headers
assert "X-RateLimit-Remaining" in response.headers
```

---

## Troubleshooting

### Testes falham com "Connection refused"

**Causa**: Serviços Docker não estão rodando.

**Solução**:
```bash
# Inicie os serviços E2E
cd tests/e2e/fixtures
docker compose -f docker-compose.e2e.yml up -d

# Verifique se está saudável
curl http://localhost:9000/health
```

### Cobertura abaixo de 70%

**Causa**: Código novo sem testes.

**Solução**:
```bash
# Veja o relatório de cobertura
poetry run pytest tests/ --cov=src --cov-report=html
open htmlcov/index.html
```

### E2E falha no CI mas passa local

**Possíveis causas**:
1. Variáveis de ambiente diferentes
2. Timing issues (adicionar `time.sleep()`)
3. Container não iniciou a tempo

**Debug no CI**:
- Logs são salvos como artifact em caso de falha
- Baixe em: Actions → E2E Tests → Artifacts → e2e-logs

---

## Referências

- [Architecture](architecture.md) - Arquitetura do sistema
- [Running](RUNNING.md) - Como executar localmente
- [Security Guide](technical/security-guide.md) - Testes de segurança
- [Spec 011](../specs/011-testing-strategy/spec.md) - Especificação completa

---

**Grupo 27 - FIAP/Alura AI para Devs**
