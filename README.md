# 🏥💜 Tech Challenge Fase 4 - Sistema multimodal de análise de saúde da mulher usando Azure AI Services

> **📅 Última Atualização**: 2026-04-12
> **✅ Status**: 2/4 Módulos Core Implementados (Texto + Áudio)

## Objetivo

**Realizar a análise e fusão de diferentes tipos de dados médicos específicos da saúde da mulher** — incluindo **texto, áudio e vídeo**.

### Opções Selecionadas:
1. ✅ **Detectar precocemente riscos em saúde materna e ginecológica**
2. ✅ **Identificar sinais de violência doméstica ou abuso**
3. ✅ **Utilizar serviços em nuvem** (Azure Free Tier)

### Foco do Projeto: Saúde Mental Feminina

Sistema multimodal para identificação de sinais de **violência doméstica** e **riscos à saúde materna** através da análise de:
- 📝 **Texto**: Prontuários, diários, relatórios
- 🎙️ **Áudio**: Consultas de telemedicina (voz)
- 🎥 **Vídeo/Imagem**: Análise de expressões faciais, linguagem corporal

---

## Visão Geral

Este projeto integra processamento de **texto, áudio e vídeo** para identificar precocemente:
- Sinais de violência doméstica em consultas médicas
- Riscos emocionais/psicológicos em gestantes
- Indicadores de estresse e ansiedade

### Tecnologias Multimodais:

| Tipo | Tecnologia | SDK Python | Uso |
|------|------------|------------|-----|
| **Texto** | Azure AI Language (Text Analytics) | `azure-ai-textanalytics` | Análise de sentimento, NLP |
| **Áudio** | Azure AI Speech | `azure-cognitiveservices-speech` | Transcrição + análise de voz |
| **Vídeo** | **YOLOv8** (local) | `ultralytics` + `opencv-python` | Detecção instrumentos, sangramento, postura |

> **Nota YOLOv8**: YOLOv8 roda **localmente no container** (custo zero), atendendo requisito obrigatório do PDF de "YOLOv8 customizado para instrumentos cirúrgicos, áreas críticas e sangramento anômalo". Aceita vídeos MP4 e imagens (processadas como vídeo de 1 frame).

> **Nota**: Azure Cognitive Services foi renomeado para **Azure AI Services** (2024) e agora faz parte do **Azure AI Foundry** (2025). O SDK `azure-cognitiveservices-vision-computervision` foi deprecated; usar `azure-ai-vision-imageanalysis`.

---

## Tecnologias

- **Framework**: FastAPI (Python 3.11+)
- **Cloud**: Azure AI Services (Free Tier) - **Deploy em produção obrigatório**
  - Azure App Service: Hospedagem API
  - Azure AI Speech: Transcrição (5h/mês free)
  - Azure AI Language: NLP (5k requests/mês free)
  - Azure SQL Database: Metadados (250GB free)
- **SDKs Azure**:
  - `azure-ai-textanalytics` 5.4.0 (Texto)
  - `azure-cognitiveservices-speech` 1.48.x (Áudio)
- **ML**: scikit-learn, transformers, **YOLOv8** (detecção objetos em vídeo)
- **Vídeo**: FFmpeg/OpenCV (extração de frames), **ultralytics** (YOLOv8 local)
- **Container**: Docker + Docker Compose
- **Testes**: pytest

> **ℹ️ Sobre o Rebranding**: Os serviços anteriormente chamados "Azure Cognitive Services" foram renomeados para **Azure AI Services** em 2024 e agora fazem parte do **Azure AI Foundry**. Os SDKs Python foram atualizados conforme lista acima.

---

## Como Executar

### Pré-requisitos

- **Python 3.11+** (se rodando localmente)
- **Poetry** (gerenciamento de dependências, se rodando localmente)
- **Docker e Docker Compose** (⚠️ **Recomendado** para desenvolvimento e **Obrigatório** para testes - veja [Executando Testes](#executando-testes))
- **Git**

> 💡 **Dica**: Mesmo que você escolha rodar a API localmente, **recomendamos fortemente** usar Docker para executar os testes devido a dependências nativas complexas (librosa, python-magic).

---

## Opção 1: Usando Docker com Mocks (Recomendado para Desenvolvimento)

Esta opção usa containers Docker que simulam os serviços Azure, permitindo desenvolver sem precisar de uma conta Azure.

> **Nota:** Com Docker não é necessário rodar `setup.sh` nem instalar Poetry/Python localmente. O Docker cuida de todas as dependências.

### Passo 1: Iniciar os Containers

```bash
# Usando o script (recomendado)
./scripts/run-mock.sh

# Ou comando Docker direto
docker-compose -f docker-compose.mock.yml up -d
```

### Passo 2: Verificar se está funcionando

```bash
# Health check
curl http://localhost:8000/health

# Deve retornar: {"status": "ok", "version": "0.3.0"}
```

### Passo 3: Testar o Endpoint de Análise de Texto

```bash
# Via curl
curl -X POST http://localhost:8000/analyze/text \
  -H "Content-Type: application/json" \
  -d '{"texto": "Estou me sentindo muito ansiosa e com medo quando ele chega em casa", "tipo": "diario"}'

# Ou use a interface Swagger
# Abra no navegador: http://localhost:8000/docs

# Ou importe as collections do Postman
# Arquivos: docs/collection.json e docs/environment.json
```

> **⚠️ Nota sobre o Mock:** O modo mock retorna valores **fixos** para testes, independente do texto enviado:
> ```json
> {
>   "sentimento": "neutro",
>   "score": 0.0,
>   "risco_violencia": "medio",
>   "risco_saude_mental": "baixo"
> }
> ```
> Para análise real com Azure, configure as credenciais no arquivo `.env` (veja seção de Configuração Azure abaixo).

**Serviços disponíveis:**
- API: http://localhost:8000
- Swagger UI: http://localhost:8000/docs
- Mock Azure Text: http://localhost:3001
- Mock Azure Speech: http://localhost:3002
- Redis: http://localhost:6379

### Passo 4: Parar os Containers

```bash
docker-compose -f docker-compose.mock.yml down
```

---

## Opção 2: Executar Localmente (com Poetry)

Esta opção requer configurar variáveis de ambiente com credenciais Azure reais ou usar o modo mock local.

> **Nota:** Na primeira vez, é necessário rodar `setup.sh` para instalar Poetry e as dependências Python.

### Passo 1: Configurar o Ambiente

```bash
# Clone o repositório
git clone https://github.com/vagnerbarbosa/tech-challenge-fase-4.git
cd tech-challenge-fase-4

# Execute o script de setup (instala Poetry e dependências na primeira vez)
./scripts/setup.sh

# Ou faça manualmente:
# poetry install
# cp .env.example .env
```

### Passo 2: Configurar Variáveis de Ambiente

```bash
# Criar arquivo .env
cp .env.example .env

# Edite o arquivo .env com suas credenciais Azure (opcional para testes locais)
# AZURE_TEXT_KEY=sua_chave_aqui
# AZURE_TEXT_ENDPOINT=https://<seu-resource>.cognitiveservices.azure.com/
```

### Passo 3: Iniciar o Servidor

```bash
# Usando o script (recomendado)
./scripts/run.sh

# Ou comando Poetry direto
poetry run uvicorn src.api.main:app --reload --port 8000
```

### Passo 4: Testar

```bash
# Health check
curl http://localhost:8000/health

# Análise de texto
curl -X POST http://localhost:8000/analyze/text \
  -H "Content-Type: application/json" \
  -d '{"texto": "Estou me sentindo muito ansiosa e com medo"}'

# Ou use a interface Swagger
# Abra no navegador: http://localhost:8000/docs

# Ou importe as collections do Postman
# Arquivos: docs/collection.json e docs/environment.json
```

---

## Scripts Disponíveis

A pasta `/scripts` contém utilitários para facilitar o desenvolvimento:

| Script | Descrição | Uso |
|--------|-----------|-----|
| `setup.sh` | Configuração inicial do projeto | `./scripts/setup.sh` |
| `run-mock.sh` | Inicia com Docker + Mocks | `./scripts/run-mock.sh` |
| `run.sh` | Inicia localmente com Poetry | `./scripts/run.sh` |
| `test.sh` | Executa testes localmente | `./scripts/test.sh [unit\|integration\|coverage]` |
| `test-docker.sh` | Executa testes via Docker (recomendado) | `./scripts/test-docker.sh [unit\|coverage\|lint\|all]` |
| `lint.sh` | Verifica código (Ruff + mypy) | `./scripts/lint.sh` |
| `check-azure.sh` | Verifica credenciais Azure | `./scripts/check-azure.sh` |

**Nota para Windows:** Execute os scripts via Git Bash, WSL ou use `bash ./scripts/nome-do-script.sh`.

> 💡 **Dica**: Use sempre `./scripts/test-docker.sh` para testes! Ele garante um ambiente Linux consistente e evita problemas com dependências nativas no Windows.

---

## Testando a API

### Endpoint: POST /analyze/text

Analisa texto em português e retorna sentimento, níveis de risco e palavras-chave.

**Exemplo de Request:**
```bash
curl -X POST http://localhost:8000/analyze/text \
  -H "Content-Type: application/json" \
  -d '{
    "texto": "Estou me sentindo muito ansiosa e com medo quando ele chega em casa",
    "tipo": "diario",
    "patient_id": "uuid-anonimo-123"
  }'
```

**Exemplo de Response:**
```json
{
  "sentimento": "negativo",
  "score": -0.85,
  "risco_violencia": "alto",
  "risco_saude_mental": "alto",
  "palavras_chave": ["ansiosa", "medo", "casa"],
  "indicadores": ["ansiedade", "medo"],
  "metadata": {
    "correlation_id": "abc-123-xyz",
    "timestamp": "2026-04-11T14:30:00Z",
    "tempo_processamento_ms": 450,
    "cache_hit": false,
    "azure_calls": 1
  }
}
```

### Parâmetros do Request

| Campo | Tipo | Obrigatório | Descrição |
|-------|------|-------------|-----------|
| `texto` | string | Sim | Texto para análise (10-5000 caracteres) |
| `tipo` | string | Não | Origem do texto: `diario`, `prontuario`, `relato` ou `geral` (padrão) |
| `patient_id` | string | Não | ID anônimo do paciente (UUID recomendado) |

#### Tipos de Texto (`tipo`)

O campo `tipo` indica a origem/contexto do texto para classificação:

| Tipo | Quando Usar |
|------|-------------|
| `diario` | Entradas pessoais, diários da paciente |
| `prontuario` | Registros médicos formais |
| `relato` | Narrações de consultas ou entrevistas |
| `geral` | Textos genéricos (padrão se não informado) |

### Outros Endpoints

| Endpoint | Método | Descrição |
|----------|--------|-----------|
| `/health` | GET | Verifica status da API |
| `/` | GET | Informações da API |
| `/docs` | GET | Swagger UI (documentação interativa) |
| `/analyze/text` | POST | Análise de texto |

---

## Executando Testes

> 🔗 **Rápido**: [Por que Docker?](#-por-que-usar-docker-para-testes) | [Testes Unitários](#passo-2-executar-testes-unitários) | [Linting](#passo-3-executar-linting-e-type-check) | [Testes Locais](#-opção-alternativa-testes-locais-sem-docker)

### ⚠️ Por que usar Docker para testes?

Os testes deste projeto **dependem de bibliotecas nativas complexas** (especialmente `librosa` e `python-magic`) que podem apresentar problemas no Windows:

- **Librosa**: Requer FFmpeg para processamento de áudio
- **python-magic**: Depende da biblioteca system `libmagic` (Linux/Mac)
- **Segmentation faults**: Ocorrências comuns no Windows devido a incompatibilidades de bibliotecas C

**A solução**: Executar testes via Docker garante um ambiente Linux consistente e funcional.

---

### 🐳 Opção Recomendada: Testes via Docker

> 💡 **Opção mais fácil**: Use o script `./scripts/test-docker.sh` que automatiza todo o processo:
> ```bash
> # Testes unitários
> ./scripts/test-docker.sh unit
>
> # Todos os checks (lint + typecheck + testes)
> ./scripts/test-docker.sh all
>
> # Ver todas as opções
> ./scripts/test-docker.sh help
> ```

#### Passo 1: Build da Imagem de Teste

```bash
# Build da imagem Docker específica para testes
docker build -f Dockerfile.test -t health-api-test:latest .

# Ou use o script que faz build automaticamente:
# ./scripts/test-docker.sh build
```

#### Passo 2: Executar Testes Unitários

```bash
# Executar todos os testes unitários
docker run --rm health-api-test:latest \
  poetry run pytest tests/unit/ -v

# Executar testes específicos do módulo de áudio
docker run --rm health-api-test:latest \
  poetry run pytest tests/unit/services/test_audio_analysis.py -v

# Executar testes com cobertura
docker run --rm health-api-test:latest \
  poetry run pytest tests/unit/ -v --cov=src --cov-report=term
```

#### Passo 3: Executar Linting e Type Check

```bash
# Ruff linting
docker run --rm health-api-test:latest \
  poetry run ruff check src/

# mypy type checking
docker run --rm health-api-test:latest \
  poetry run mypy src/services/audio_analysis.py
```

#### Passo 4: Testes de Integração (requer API rodando)

```bash
# Iniciar a API em um container
docker-compose up -d api

# Executar testes de integração
docker run --rm --network=host health-api-test:latest \
  poetry run pytest tests/integration/ -v

# Parar a API
docker-compose down
```

---

### 💻 Opção Alternativa: Testes Locais (sem Docker)

> ⚠️ **Nota**: Esta opção pode apresentar erros no Windows devido a dependências nativas.

```bash
# Todos os testes
./scripts/test.sh

# Apenas testes unitários
./scripts/test.sh unit

# Testes de integração
./scripts/test.sh integration

# Com relatório de cobertura
./scripts/test.sh coverage
```

Ou diretamente com Poetry:
```bash
poetry run pytest tests/ -v --cov=src
```

---

## Verificação de Qualidade de Código

```bash
# Usando o script
./scripts/lint.sh

# Ou comandos individuais
poetry run ruff check src/ tests/
poetry run ruff format src/ tests/
poetry run mypy src/
```

---

## Endpoints

| Endpoint | Método | Status | Descrição | Tecnologia | Modalidade |
|----------|--------|--------|-----------|------------|------------|
| `/health` | GET | ✅ Implementado | Health check com quotas Azure | - | - |
| `/analyze/text` | POST | ✅ Implementado | Análise de sentimento e riscos | Azure AI Language | 📝 Texto |
| `/analyze/audio` | POST | ✅ Implementado | Transcrição + análise prosódica | Azure AI Speech + librosa | 🎙️ Áudio |
| `/analyze/audio/formats` | GET | ✅ Implementado | Lista formatos suportados | - | 🎙️ Áudio |
| `/analyze/video` | POST | ⏳ Pendente | Análise com YOLOv8 | YOLOv8 Local | 🎥 Vídeo |
| `/analyze/multimodal` | POST | ⏳ Pendente | Fusão de 3 modalidades | Combinação | 📝🎙️🎥 |
| `/docs` | GET | ✅ Implementado | Documentação Swagger interativa | - | - |

**Legenda:**
- ✅ Implementado e testado
- 🔄 Parcialmente implementado
- ⏳ Pendente

---

## Exemplo de Uso

### Análise de Texto

```bash
curl -X POST "http://localhost:8000/analyze/text" \
  -H "Content-Type: application/json" \
  -d '{
    "texto": "Estou me sentindo muito ansiosa e tenho medo de falar sobre o que acontece em casa...",
    "tipo": "diario"
  }'
```

**Resposta:**
```json
{
  "sentimento": "negativo",
  "score": -0.85,
  "risco_violencia": "alto",
  "risco_saude_mental": "alto",
  "palavras_chave": ["ansiosa", "medo", "casa"],
  "indicadores": ["sinalizacao_isolamento", "expressao_medo"]
}
```

### Análise de Áudio

Analisa arquivos de áudio (WAV, MP3, OGG) extraindo transcrição e features prosódicas.

**Exemplo de Request:**
```bash
curl -X POST "http://localhost:8000/analyze/audio" \
  -H "Content-Type: multipart/form-data" \
  -F "file=@consulta.wav" \
  -F "patient_id=550e8400-e29b-41d4-a716-446655440000"
```

**Exemplo de Response:**
```json
{
  "transcricao": "Doutor, eu estou muito ansiosa e com medo quando ele chega em casa",
  "idioma_detectado": "pt-BR",
  "sentimento": "negativo",
  "entonação": "hesitante",
  "voz_tremida": true,
  "pausas_suspeitas": 3,
  "duracao_segundos": 32.5,
  "risco_violencia": "alto",
  "risco_saude_mental": "alto",
  "metadata": {
    "correlation_id": "audio-1234567890",
    "timestamp": "2026-04-12T14:30:00Z",
    "tempo_processamento_ms": 8200,
    "cache_hit": false,
    "azure_calls": 1
  }
}
```

**Parâmetros:**
| Campo | Tipo | Obrigatório | Descrição |
|-------|------|-------------|-----------|
| `file` | file | Sim | Arquivo de áudio (WAV, MP3, OGG) - máx 50MB |
| `patient_id` | string | Não | ID anônimo do paciente (UUID recomendado) |

**Features Extraídas:**
- ✅ Transcrição via Azure Speech Services
- ✅ Pitch analysis (detecção de voz tremida)
- ✅ Energy analysis (classificação: calmo/hesitante/agitado)
- ✅ Detecção de pausas suspeitas
- ✅ Análise de risco combinando texto + prosódia

### Análise de Vídeo (YOLOv8 Local) ⏳ PENDENTE

> **Status**: Especificação criada em `specs/004-video-analysis/`, aguardando implementação.

> **Nota**: YOLOv8 rodará localmente no container (custo zero), detectando instrumentos cirúrgicos, sangramento e linguagem corporal.

**Especificação planejada:**
```bash
curl -X POST "http://localhost:8000/analyze/video" \
  -H "Content-Type: multipart/form-data" \
  -F "file=@cirurgia.mp4" \
  -F "patient_id=uuid-aqui"
```

**Response esperado:**
```json
{
  "frames_analisados": 150,
  "deteccoes": [
    {"classe": "instrumento_cirurgico", "confianca": 0.95},
    {"classe": "sangramento", "confianca": 0.82}
  ],
  "risco_violencia": "baixo",
  "risco_saude_mental": "medio"
}
```

### Análise Multimodal ⏳ PENDENTE

> **Status**: Depende da implementação do endpoint `/analyze/video` (Spec 004).

> **Especificação planejada**: Combinação das análises de texto, áudio e vídeo com algoritmo de fusão.

**Request planejado:**
```bash
curl -X POST "http://localhost:8000/analyze/multimodal" \
  -H "Content-Type: multipart/form-data" \
  -F "texto=@relatorio.txt" \
  -F "audio=@consulta.wav" \
  -F "video=@cirurgia.mp4"
```

**Response esperado:**
```json
{
  "fusao": {
    "risco_violencia": "alto",
    "confiança": 0.92,
    "alerta": true
  },
  "texto": { "risco_violencia": "medio", ... },
  "audio": { "risco_violencia": "alto", ... },
  "video": { "risco_violencia": "medio", ... },
  "recomendacao": "Encaminhar para equipe multidisciplinar"
}
```

---

## Modalidades de Dados

### 📝 Texto (Azure Text Analytics)

**Processamento:**
- Análise de sentimento
- Extração de entidades médicas
- Detecção de idioma
- Identificação de padrões de violência

**Exemplos de entrada:**
- Prontuários médicos
- Diários pessoais
- Relatos de consultas
- Questionários

### 🎙️ Áudio (Azure Speech Services)

**Processamento:**
- Speech-to-text (transcrição)
- Análise de entonação
- Detecção de pausas suspeitas
- Identificação de voz tremida

**Exemplos de entrada:**
- Gravações de consultas (com consentimento)
- Telemedicina
- Depoimentos

### 🎥 Vídeo/Imagem (YOLOv8 Local + OpenCV)

**Processamento:**
- **Vídeos**: Extração automática de frames (1 a cada 5s) + análise YOLOv8
- **Imagens**: Processadas como vídeo de 1 frame via YOLOv8
- Detecção de instrumentos cirúrgicos
- Detecção de sangramento anômalo
- Análise de linguagem corporal

**Exemplos de entrada:**
- Vídeos curtos de atendimento (MP4, max 30s)
- Fotos de consulta (JPEG, PNG)

---

## Azure Free Tier - Limites

| Serviço | Limite Free | Estimativa de Uso |
|---------|-------------|-------------------|
| Speech Services | 5h áudio/mês | ~300 consultas |
| Text Analytics | 5k requests/mês | Suficiente para MVP |
| SQL Database | 250GB | Metadados + logs |
| App Service | 60min CPU/dia | API contínua |
| Blob Storage | 5GB | Áudios + vídeos |

**Custo total: $0** (dentro do free tier)

> **💡 Nota sobre YOLOv8**: A análise de vídeo/imagem usa YOLOv8 local (dentro do container), consumindo **zero** da quota Azure AI Vision.

### 🔒 Proteção Contra Custos (Hard Stop)

O sistema implementa uma **estratégia de hard stop** que garante **zero custos**:

- **Contadores internos** por serviço (Texto, Áudio)
- **Interrupção automática** quando quotas forem atingidas
- **Retorno HTTP 503** com informação de retry
- **Reset automático** às 00:00 UTC

> Ver detalhes em: [`specs/006-rate-limiting/spec.md`](specs/006-rate-limiting/spec.md)

---

## Testes

⚠️ **Importante**: Veja a seção [Executando Testes](#executando-testes) acima para instruções detalhadas.

### 🚀 Modo Fácil (Script Recomendado)

```bash
# Executar via script (faz build e roda testes automaticamente)
./scripts/test-docker.sh unit        # Testes unitários
./scripts/test-docker.sh coverage    # Com cobertura
./scripts/test-docker.sh all         # Lint + typecheck + testes
./scripts/test-docker.sh help        # Ver todas as opções
```

### Comandos Manuais (Docker)

```bash
# Build e execução completa
docker build -f Dockerfile.test -t health-api-test:latest . && \
docker run --rm health-api-test:latest poetry run pytest tests/unit/ -v --cov=src
```

### Comandos Locais (sem Docker)

```bash
# Testes unitários e integração
poetry run pytest -v

# Testes de carga (Locust)
cd tests/load
poetry run locust -f locustfile.py
```

---

## Documentação

### Specs Kit (Status)

| ID | Feature | Status | Link |
|----|---------|--------|------|
| 001 | Bootstrap do Projeto | ✅ Concluído | [spec.md](specs/001-bootstrap/spec.md) |
| 002 | Análise de Texto | ✅ Concluído | [spec.md](specs/002-text-analysis/spec.md) |
| 003 | Análise de Áudio | ✅ Concluído | [spec.md](specs/003-audio-analysis/spec.md) |
| 004 | Análise de Vídeo (YOLOv8) | ⏳ Pendente | [spec.md](specs/004-video-analysis/spec.md) |
| 005 | Fusão Multimodal | ⏳ Pendente | [spec.md](specs/005-multimodal-fusion/spec.md) |
| 006 | Rate Limiting | 🔄 Parcial | [spec.md](specs/006-rate-limiting/spec.md) |
| 007 | Security Hardening | ⏳ Pendente | [spec.md](specs/007-security-hardening/spec.md) |
| 008 | Testes Automatizados | 🔄 Parcial | [spec.md](specs/008-tests/spec.md) |
| 009 | Deploy Azure | ⏳ Pendente | [spec.md](specs/009-deploy-azure/spec.md) |
| 010 | Documentação Final | ⏳ Pendente | [spec.md](specs/010-documentation/spec.md) |

### Outros Documentos
- [📋 Índice de Especificações](specs/README.md)
- [📊 Context7 - Melhores Práticas](docs/technical/context7-best-practices.md)
- [🔒 Compliance Analysis](docs/technical/compliance-analysis.md)

---

## Vídeo de Demonstração

📹 [Assista ao vídeo de demonstração no YouTube](https://www.youtube.com/watch?v=dQw4w9WgXcQ)

O vídeo demonstra:
- Arquitetura multimodal
- Análise de texto, áudio e vídeo
- Identificação de sinais de alerta
- Dashboard de resultados
- Deploy na Azure

---

## Collection API

Arquivos de coleção compatíveis com **Postman**, **Insomnia** e **Bruno** estão disponíveis em `docs/`.

### Arquivos

- **`docs/collection.json`**: Coleção com todos os endpoints da API
- **`docs/environment.json`**: Variáveis de ambiente (`base_url`, `api_key`)

### Como Importar

#### Postman
1. File → Import → Upload Files
2. Selecione `docs/collection.json` e `docs/environment.json`
3. Clique em "Import"
4. Selecione o environment "Multimodal Health Analysis API" no dropdown superior direito

#### Insomnia
1. Application → Preferences → Data → Import Data
2. Selecione "From File"
3. Escolha `docs/collection.json`
4. Repita para `docs/environment.json`

#### Bruno
1. Collections → Import Collection
2. Selecione "Postman Collection"
3. Escolha o arquivo `docs/collection.json`
4. Para o environment, use: Environments → Create Environment e importe `docs/environment.json`

### Variáveis de Ambiente

| Variável | Descrição | Padrão |
|----------|-----------|--------|
| `{{base_url}}` | URL base da API | `http://localhost:8000` |
| `{{api_key}}` | Chave de API | `test-api-key` |

---

## Estrutura do Projeto

```
tech-challenge-fase-4/
├── src/                      # Código fonte
│   ├── api/                  # FastAPI app e rotas
│   │   ├── main.py
│   │   └── routes/
│   │       ├── health.py          # Health check com quotas
│   │       ├── text.py            # Análise de texto (✅ Task 002)
│   │       ├── audio.py           # Análise de áudio (✅ Task 003)
│   │       └── dependencies.py    # Injeção de dependências
│   ├── core/                 # Configurações, logging, exceções
│   │   ├── config.py              # Configurações da aplicação
│   │   ├── logging_config.py      # Logging estruturado
│   │   ├── exceptions.py          # Exceções customizadas
│   │   ├── cache.py               # Cache em memória
│   │   ├── rate_limit.py          # QuotaManager (✅ Task 006 parcial)
│   │   └── temp_file_manager.py   # LGPD-compliant temp files
│   ├── services/             # Lógica de negócio
│   │   ├── text_analysis.py       # Serviço de análise de texto
│   │   ├── audio_analysis.py      # Serviço de análise de áudio (✅ Task 003)
│   │   └── risk_detector.py       # Detecção de risco
│   ├── models/               # Schemas Pydantic
│   │   └── schemas.py             # Modelos de request/response
│   ├── infrastructure/       # Clientes Azure
│   │   ├── azure_clients.py       # Singleton Azure Text Analytics
│   │   └── azure_speech_client.py # Client Azure Speech (✅ Task 003)
│   └── utils/                # Helpers
│       └── file_validation.py     # Validação de arquivos
├── tests/                    # Testes
│   ├── unit/                 # Testes unitários
│   │   ├── core/
│   │   ├── services/              # Testes de serviços
│   │   └── infrastructure/
│   ├── integration/          # Testes de integração
│   └── load/                 # Testes de carga
├── specs/                    # Especificações Spec Kit
│   ├── 001-bootstrap/        # ✅ Concluído
│   ├── 002-text-analysis/      # ✅ Concluído
│   ├── 003-audio-analysis/     # ✅ Concluído
│   ├── 004-video-analysis/     # ⏳ Pendente
│   ├── 005-multimodal-fusion/  # ⏳ Pendente
│   ├── 006-rate-limiting/      # 🔄 Parcial
│   ├── 007-security-hardening/ # ⏳ Pendente
│   ├── 008-tests/              # 🔄 Parcial
│   ├── 009-deploy-azure/       # ⏳ Pendente
│   └── 010-documentation/        # ⏳ Pendente
├── docs/                     # Documentação
│   └── technical/
├── .claude/                  # Configuração Claude Code
├── .specify/                 # Configuração Spec Kit
├── docker-compose.yml
├── docker-compose.mock.yml
├── Dockerfile                # Multi-stage production
├── Dockerfile.test           # ⚠️ Imagem para testes - USE ESTE PARA TESTES
└── README.md
```

---

## ⚠️ Notas Importantes

- **Consentimento**: Todos os dados de áudio/vídeo devem ter consentimento explícito
- **LGPD**: Dados sensíveis são anonimizados antes do processamento
- **Ética**: Sistema é ferramenta de apoio, não substitui julgamento médico
- **Free Tier**: Monitorar uso para não ultrapassar limites Azure

---

## Integrantes do Grupo 27

Este projeto é desenvolvido pela mesma equipe das Fases 1, 2 e 3:

| Nome | GitHub |
|------|--------|
| Adriel Santos | [@AdrielCandido](https://github.com/AdrielCandido) |
| Leticia Nepomuceno | [@LeticiaNepomucena](https://github.com/LeticiaNepomucena) |
| Lucas Silva | [@lucfsilva](https://github.com/lucfsilva) |
| Vagner Barbosa | [@vagnerbarbosa](https://github.com/vagnerbarbosa) |

**Curso**: FIAP/Alura - AI para Devs (IADT)
**Fase**: 4 (Análise Multimodal de Dados em Saúde da Mulher)

---

## Fases Anteriores

- [Fase 1 - Diabetes Prediction](https://github.com/vagnerbarbosa/tech-challenge-fase-1)
- [Fase 2 - Otimização com Algoritmos Genéticos](https://github.com/vagnerbarbosa/tech-challenge-fase-2)
- [Fase 3 - Assistente Virtual Médico](https://github.com/vagnerbarbosa/tech-challenge-fase-3)

---

## Licença

MIT License - Copyright (c) 2026 Grupo 27 Tech Challenge
