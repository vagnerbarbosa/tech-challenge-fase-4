# 🏥💜 Tech Challenge Fase 4 - Sistema multimodal de análise de saúde da mulher usando Azure AI Services

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

| Tipo | Tecnologia Azure | SDK Python | Uso |
|------|------------------|------------|-----|
| **Texto** | Azure AI Language (Text Analytics) | `azure-ai-textanalytics` | Análise de sentimento, NLP |
| **Áudio** | Azure AI Speech | `azure-cognitiveservices-speech` | Transcrição + análise de voz |
| **Vídeo** | Azure AI Vision | `azure-ai-vision-imageanalysis` | Análise de expressões faciais |

> **Nota**: Azure Cognitive Services foi renomeado para **Azure AI Services** (2024) e agora faz parte do **Azure AI Foundry** (2025). O SDK `azure-cognitiveservices-vision-computervision` foi deprecated; usar `azure-ai-vision-imageanalysis`.

---

## Tecnologias

- **Framework**: FastAPI (Python 3.11+)
- **Cloud**: Azure AI Services (Free Tier) - **Deploy em produção obrigatório**
  - Azure App Service: Hospedagem API
  - Azure AI Speech: Transcrição (5h/mês free)
  - Azure AI Language: NLP (5k requests/mês free)
  - Azure AI Vision: Análise de imagem (5k requests/mês free)
  - Azure SQL Database: Metadados (250GB free)
- **SDKs Azure**:
  - `azure-ai-textanalytics` 5.4.0 (Texto)
  - `azure-cognitiveservices-speech` 1.48.x (Áudio)
  - `azure-ai-vision-imageanalysis` 1.0.x (Imagem/Vídeo)
- **ML**: scikit-learn, transformers
- **Vídeo**: FFmpeg/OpenCV (extração de frames)
- **Container**: Docker + Docker Compose
- **Testes**: pytest

> **ℹ️ Sobre o Rebranding**: Os serviços anteriormente chamados "Azure Cognitive Services" foram renomeados para **Azure AI Services** em 2024 e agora fazem parte do **Azure AI Foundry**. Os SDKs Python foram atualizados conforme lista acima.

---

## Como Executar

### Pré-requisitos

- **Python 3.11+**
- **Poetry** (gerenciamento de dependências)
- **Docker e Docker Compose** (opcional, para modo com mocks)
- **Git**

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

# Deve retornar: {"status": "ok", "version": "1.0.0"}
```

### Passo 3: Testar o Endpoint de Análise de Texto

```bash
# Via curl
curl -X POST http://localhost:8000/analyze/text \
  -H "Content-Type: application/json" \
  -d '{"texto": "Estou me sentindo muito ansiosa e com medo quando ele chega em casa", "tipo": "diario"}'

# Ou use a interface Swagger
# Abra no navegador: http://localhost:8000/docs
```

**Serviços disponíveis:**
- API: http://localhost:8000
- Swagger UI: http://localhost:8000/docs
- Mock Azure Text: http://localhost:3001
- Mock Azure Speech: http://localhost:3002
- Mock Azure Vision: http://localhost:3003
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
```

---

## Scripts Disponíveis

A pasta `/scripts` contém utilitários para facilitar o desenvolvimento:

| Script | Descrição | Uso |
|--------|-----------|-----|
| `setup.sh` | Configuração inicial do projeto | `./scripts/setup.sh` |
| `run-mock.sh` | Inicia com Docker + Mocks | `./scripts/run-mock.sh` |
| `run.sh` | Inicia localmente com Poetry | `./scripts/run.sh` |
| `test.sh` | Executa testes | `./scripts/test.sh [unit\|integration\|coverage]` |
| `lint.sh` | Verifica código (Ruff + mypy) | `./scripts/lint.sh` |
| `check-azure.sh` | Verifica credenciais Azure | `./scripts/check-azure.sh` |

**Nota para Windows:** Execute os scripts via Git Bash, WSL ou use `bash ./scripts/nome-do-script.sh`.

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

| Endpoint | Método | Descrição | Modalidade |
|----------|--------|-----------|------------|
| `/health` | GET | Health check da API | - |
| `/analyze/text` | POST | Análise de texto | 📝 Texto |
| `/analyze/audio` | POST | Análise de áudio | 🎙️ Áudio |
| `/analyze/image` | POST | Análise de imagem ou vídeo | 🎥 Imagem/Vídeo |
| `/analyze/multimodal` | POST | Fusão de 3 modalidades | 📝🎙️🎥 |
| `/docs` | GET | Documentação Swagger | - |

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

```bash
curl -X POST "http://localhost:8000/analyze/audio" \
  -H "Content-Type: multipart/form-data" \
  -F "audio=@consulta.wav" \
  -F "metadata={\"tipo_consulta\":\"pré-natal\"}"
```

**Resposta:**
```json
{
  "transcricao": "Doutor, eu não sei se posso contar isso...",
  "sentimento": "negativo",
  "entonação": "hesitante",
  "risco_violencia": "medio",
  "pausas_suspeitas": 3,
  "voz_tremida": true
}
```

### Análise de Imagem/Vídeo

**Imagem:**
```bash
curl -X POST "http://localhost:8000/analyze/image" \
  -H "Content-Type: multipart/form-data" \
  -F "imagem=@foto_consulta.jpg"
```

**Vídeo (frames extraídos automaticamente):**
```bash
curl -X POST "http://localhost:8000/analyze/image" \
  -H "Content-Type: multipart/form-data" \
  -F "imagem=@consulta_video.mp4"
```

**Resposta:**
```json
{
  "emoção_principal": "tristeza",
  "confiança": 0.89,
  "expressoes": ["evitando_olho", "expressao_tensa"],
  "sinais_alertas": [],
  "risco_violencia": "medio"
}
```

### Análise Multimodal

```bash
curl -X POST "http://localhost:8000/analyze/multimodal" \
  -H "Content-Type: multipart/form-data" \
  -F "texto=@relatorio.txt" \
  -F "audio=@consulta.wav" \
  -F "imagem=@foto.jpg"
```

**Resposta:**
```json
{
  "fusao": {
    "risco_violencia": "alto",
    "confiança": 0.92,
    "alerta": true
  },
  "texto": { ... },
  "audio": { ... },
  "imagem": { ... },
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

### 🎥 Imagem/Vídeo (Azure AI Vision + FFmpeg)

**Processamento:**
- **Imagens**: Análise direta com Azure AI Vision
- **Vídeos**: Extração automática de frames (1 a cada 5s) + análise
- Análise de expressões faciais
- Detecção de emoções
- Identificação de marcas/sinais

**Exemplos de entrada:**
- Fotos de consulta (JPEG, PNG)
- Vídeos curtos de atendimento (MP4, max 30s)

---

## Azure Free Tier - Limites

| Serviço | Limite Free | Estimativa de Uso |
|---------|-------------|-------------------|
| Speech Services | 5h áudio/mês | ~300 consultas |
| Text Analytics | 5k requests/mês | Suficiente para MVP |
| Computer Vision | 5k transactions/mês | ~5k análises |
| SQL Database | 250GB | Metadados + logs |
| App Service | 60min CPU/dia | API contínua |
| Blob Storage | 5GB | Áudios + imagens |

**Custo total: $0** (dentro do free tier)

### 🔒 Proteção Contra Custos (Hard Stop)

O sistema implementa uma **estratégia de hard stop** que garante **zero custos**:

- **Contadores internos** por serviço (Texto, Áudio, Visão)
- **Interrupção automática** quando quotas forem atingidas
- **Retorno HTTP 503** com informação de retry
- **Reset automático** às 00:00 UTC

> Ver detalhes em: [`specs/006-rate-limiting/spec.md`](specs/006-rate-limiting/spec.md)

---

## Testes

```bash
# Testes unitários e integração
poetry run pytest -v

# Testes de carga (Locust)
cd tests/load
poetry run locust -f locustfile.py
```

---

## Documentação

- [📋 Especificações do Projeto](specs/README.md)
- [🚀 Task 001 - Bootstrap](specs/001-bootstrap/spec.md)
- [📝 Task 002 - Análise de Texto](specs/002-text-analysis/spec.md)
- [🎙️ Task 003 - Análise de Áudio](specs/003-audio-analysis/spec.md)
- [🎥 Task 004 - Análise de Imagem](specs/004-image-analysis/spec.md)
- [🔀 Task 005 - Fusão Multimodal](specs/005-multimodal-fusion/spec.md)
- [📊 Context7 - Melhores Práticas](docs/technical/context7-best-practices.md)

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
│   │       ├── health.py          # Health check endpoints
│   │       └── text.py            # Análise de texto (Task 002)
│   ├── core/                 # Configurações, logging, exceções
│   │   ├── config.py              # Configurações da aplicação
│   │   ├── logging_config.py      # Logging estruturado
│   │   ├── exceptions.py          # Exceções customizadas
│   │   └── cache.py               # Cache em memória (Task 002)
│   ├── services/             # Lógica de negócio
│   │   ├── text_analysis.py       # Serviço de análise de texto
│   │   └── risk_detector.py     # Detecção de risco (Task 002)
│   ├── models/               # Schemas Pydantic
│   │   └── schemas.py             # Modelos de request/response
│   ├── infrastructure/       # Clientes Azure
│   │   └── azure_clients.py       # Singleton Azure Text Analytics
│   └── utils/                # Helpers
├── tests/                    # Testes
│   ├── unit/                 # Testes unitários
│   │   ├── core/                  # Testes de cache
│   │   └── services/              # Testes de serviços
│   ├── integration/          # Testes de integração
│   │   ├── test_text_endpoint.py
│   │   └── test_azure_services.py
│   └── load/                 # Testes de carga
├── specs/                    # Especificações Spec Kit
│   ├── 001-bootstrap/
│   ├── 002-text-analysis/
│   └── ...
├── tasks/                    # Status das tasks
├── docs/                     # Documentação
│   └── technical/
├── .claude/                  # Configuração Claude Code
├── .specify/                 # Configuração Spec Kit
├── .github/                  # GitHub Actions
├── docker-compose.yml
├── docker-compose.mock.yml
├── Dockerfile
├── Dockerfile.dev
└── README.md
```

---

## Licença

MIT License - Copyright (c) 2026 Equipe Tech Challenge

---

## ⚠️ Notas Importantes

- **Consentimento**: Todos os dados de áudio/vídeo devem ter consentimento explícito
- **LGPD**: Dados sensíveis são anonimizados antes do processamento
- **Ética**: Sistema é ferramenta de apoio, não substitui julgamento médico
- **Free Tier**: Monitorar uso para não ultrapassar limites Azure

---

## Equipe

Este projeto é desenvolvido pela mesma equipe das Fases 1, 2 e 3:

| Nome | GitHub |
|------|--------|
| Adriel Santos | [@AdrielCandido](https://github.com/AdrielCandido) |
| Leticia Nepomuceno | [@LeticiaNepomuceno](https://github.com/LeticiaNepomuceno) |
| Lucas Silva | [@lucfsilva](https://github.com/lucfsilva) |
| Vagner Barbosa | [@vagnerbarbosa](https://github.com/vagnerbarbosa) |

**Curso**: FIAP/Alura - AI para Devs (IADT)
**Fase**: 4 (Análise Multimodal de Dados em Saúde da Mulher)

---

## Fases Anteriores

- [Fase 1 - Diabetes Prediction](https://github.com/vagnerbarbosa/tech-challenge-fase-1)
- [Fase 2 - Otimização com Algoritmos Genéticos](https://github.com/vagnerbarbosa/tech-challenge-fase-2)
- [Fase 3 - Assistente Virtual Médico](https://github.com/vagnerbarbosa/tech-challenge-fase-3)
