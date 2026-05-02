# Como Executar a Aplicação Localmente

> **Última Atualização**: 2026-05-01

Este guia explica como executar a Multimodal Health Analysis API em seu ambiente local.

---

## Opções Disponíveis

| Opção | Quando Usar | Tempo |
|-------|-------------|-------|
| [Docker Automático](#opção-1-docker-automático-recomendado) | Primeira vez ou desenvolvimento rápido | 5 min |
| [Docker Manual](#opção-2-docker-manual) | Precisa de controle dos containers | 10 min |
| [Poetry Local](#opção-3-poetry-local) | Desenvolvimento ativo | 15 min |

---

## Pré-requisitos

Verifique se tem instalado:

```bash
# Docker (para opções 1 e 2)
docker --version
docker-compose --version

# Python 3.11+ e Poetry (para opção 3)
python3 --version
poetry --version
```

---

## Opção 1: Docker Automático (Recomendado)

Execute um comando e tenha tudo funcionando.

### Passo 1: Clone o repositório

```bash
git clone https://github.com/vagnerbarbosa/tech-challenge-fase-4.git
cd tech-challenge-fase-4
```

### Passo 2: Execute o script

```bash
./scripts/run-mock.sh
```

Este script:
- Builda a imagem Docker
- Sobe a API na porta 8000
- Sobe mocks Azure nas portas 3001/3002
- Sobe Redis na porta 6379

### Passo 3: Verifique se funcionou

```bash
curl http://localhost:8000/health
```

Resposta esperada:
```json
{"status": "healthy", "version": "0.8.0"}
```

### Passo 4: Acesse a documentação

Abra no navegador: http://localhost:8000/docs

### Parar a aplicação

```bash
./scripts/stop-mock.sh
# ou
docker-compose -f docker-compose.mock.yml down
```

> **ℹ️ Nota sobre o Mock Mode**: Ao executar com `./scripts/run-mock.sh` ou `docker-compose.mock.yml`, os serviços Azure são **mockados** (simulados localmente). Isso permite desenvolvimento e testes sem consumir quota do Azure Free Tier e sem necessidade de credenciais reais.
> 
> Para usar serviços Azure reais, configure as variáveis no `.env` e execute com `docker-compose.yml`.

---

## Opção 2: Docker Manual

Para quem quer entender cada passo.

### Passo 1: Clone e configure

```bash
git clone https://github.com/vagnerbarbosa/tech-challenge-fase-4.git
cd tech-challenge-fase-4
cp .env.example .env
```

### Passo 2: Edite o .env (opcional)

```bash
# Abra o arquivo .env em seu editor
# Modifique apenas se necessário
```

### Passo 3: Build e run

```bash
# Build da imagem
docker-compose -f docker-compose.mock.yml build

# Inicie os serviços
docker-compose -f docker-compose.mock.yml up -d

# Verifique se está rodando
docker-compose -f docker-compose.mock.yml ps
```

### Passo 4: Veja os logs

```bash
# Logs da API
docker-compose -f docker-compose.mock.yml logs -f api

# Pressione Ctrl+C para sair
```

### Parar

```bash
docker-compose -f docker-compose.mock.yml down
```

---

## Opção 3: Poetry Local

Para desenvolvimento Python sem Docker.

### Passo 1: Instale o Poetry (se não tiver)

```bash
curl -sSL https://install.python-poetry.org | python3 -
```

### Passo 2: Clone e configure

```bash
git clone https://github.com/vagnerbarbosa/tech-challenge-fase-4.git
cd tech-challenge-fase-4
cp .env.example .env
```

### Passo 3: Instale as dependências

```bash
poetry install --extras security
```

### Passo 4: Execute a aplicação

```bash
# Entre no ambiente Poetry
poetry shell

# Execute a API
uvicorn src.api.main:app --reload --port 8000
```

Ou sem entrar no shell:

```bash
poetry run uvicorn src.api.main:app --reload --port 8000
```

### Parar

Pressione `Ctrl+C` no terminal.

---

## Testando a API

Após iniciar, teste os endpoints:

### Health Check

```bash
curl http://localhost:8000/health
```

### Análise de Texto

```bash
curl -X POST http://localhost:8000/analyze/text \
  -H "Content-Type: application/json" \
  -d '{"texto": "Estou me sentindo ansiosa"}'
```

### Documentação da API

**Desenvolvimento (local):**
- Swagger UI: http://localhost:8000/docs
- ReDoc: http://localhost:8000/redoc
- OpenAPI JSON: http://localhost:8000/openapi.json

**Produção (Azure):**
- Swagger UI e ReDoc estão **desabilitados** (HTTP sem HTTPS causa erros de Mixed Content)
- Use o OpenAPI JSON: `http://20.201.82.8:8000/openapi.json`
- Importe em Postman/Insomnia para interface visual

---

## Configuração com Azure Real (Opcional)

Por padrão, a aplicação roda em modo mock (simulado). Para usar Azure real:

### 1. Obtenha credenciais Azure

- Crie conta em [azure.microsoft.com/free](https://azure.microsoft.com/free)
- Crie recursos de Text Analytics e Speech
- Copie as chaves e endpoints

### 2. Configure o .env

```bash
# Edite o arquivo .env
AZURE_TEXT_KEY=sua-chave-aqui
AZURE_TEXT_ENDPOINT=https://seu-endpoint.cognitiveservices.azure.com
AZURE_SPEECH_KEY=sua-chave-speech
AZURE_SPEECH_REGION=brazilsouth
```

### 3. Execute com docker-compose.yml (não mock)

```bash
docker-compose up -d
```

---

## Azure AI Content Safety (Opcional)

O Azure AI Content Safety fornece detecção multilíngue de riscos em texto, incluindo violência, autoagressão e conteúdo prejudicial em mais de 100 idiomas.

### 1. Como Habilitar

Content Safety é opcional e controlado pela variável `CONTENT_SAFETY_ENABLED`. Quando desabilitado, o campo `content_safety` é omitido das respostas.

### 2. Variáveis de Ambiente Necessárias

| Variável | Descrição | Obrigatório |
|----------|-----------|-------------|
| `CONTENT_SAFETY_ENABLED` | Ativa a análise de conteúdo (`true`/`false`) | Sim (para usar) |
| `AZURE_CONTENT_SAFETY_KEY` | Chave do recurso Azure Content Safety | Se habilitado |
| `AZURE_CONTENT_SAFETY_ENDPOINT` | Endpoint do recurso Azure Content Safety | Se habilitado |

### 3. Exemplo de Configuração no .env

```bash
# Azure AI Content Safety (Multilingual Risk Detection)
# Detecta violência, autoagressão e conteúdo prejudicial em 100+ idiomas
CONTENT_SAFETY_ENABLED=true
AZURE_CONTENT_SAFETY_KEY=your_content_safety_key_here
AZURE_CONTENT_SAFETY_ENDPOINT=https://your-resource.cognitiveservices.azure.com/
```

### 4. Como Verificar se Está Funcionando

Após configurar e reiniciar a API, faça uma requisição de análise de texto:

```bash
curl -X POST http://localhost:8000/analyze/text \
  -H "Content-Type: application/json" \
  -H "X-API-Key: sua-api-key" \
  -d '{
    "texto": "Estou com medo e muito ansiosa",
    "tipo": "diario",
    "patient_id": "paciente-123"
  }'
```

Se Content Safety estiver habilitado e funcionando, a resposta incluirá o campo `content_safety`.

### 5. Exemplo de Resposta da API com Content Safety

```json
{
  "sentimento": "negativo",
  "score": -0.75,
  "risco_violencia": "medio",
  "risco_saude_mental": "alto",
  "palavras_chave": ["medo", "ansiosa"],
  "indicadores": ["ansiedade", "expressao_medo"],
  "content_safety": {
    "self_harm_severity": 0,
    "violence_severity": 2,
    "hate_severity": 0,
    "sexual_severity": 0,
    "is_harmful": false,
    "highest_category": "violence",
    "highest_severity": 2
  },
  "metadata": {
    "correlation_id": "txt-abc-123",
    "timestamp": "2026-04-23T14:30:00Z",
    "tempo_processamento_ms": 680
  }
}
```

**Escala de Severidade:**
- `0` - Nenhum conteúdo detectado
- `1-2` - Severidade baixa
- `3-4` - Severidade média
- `5-6` - Severidade alta

**Categorias Analisadas:**
- `self_harm_severity` - Autoagressão
- `violence_severity` - Violência
- `hate_severity` - Discurso de ódio
- `sexual_severity` - Conteúdo sexual

---

## Solução de Problemas

### Porta 8000 já em uso

```bash
# Encontre o processo
lsof -i :8000

# Pare o processo
kill -9 <PID>

# Ou use outra porta
uvicorn src.api.main:app --reload --port 8001
```

### Erro de permissão no Docker

```bash
# Linux/Mac: Adicione seu usuário ao grupo docker
sudo usermod -aG docker $USER
# Faça logout e login novamente
```

### Erro "command not found: poetry"

```bash
# Adicione ao PATH
export PATH="$HOME/.local/bin:$PATH"

# Ou use o caminho completo
~/.local/bin/poetry install
```

---

## Scripts Úteis

| Script | Descrição |
|--------|-----------|
| `./scripts/run-mock.sh` | Inicia com Docker + mocks |
| `./scripts/stop-mock.sh` | Para todos os containers |
| `./scripts/test-docker.sh` | Executa testes em Docker |
| `./scripts/setup.sh` | Configuração inicial |

---

## Serviços e Portas

| Serviço | Porta | Descrição |
|---------|-------|-----------|
| API | 8000 | Aplicação principal |
| Mock Azure Text | 3001 | Simulador Azure Language |
| Mock Azure Speech | 3002 | Simulador Azure Speech |
| Redis | 6379 | Cache e rate limiting |
| OpenAPI JSON | 8000/openapi.json | Schema da API (Postman/Insomnia) |
| Swagger UI* | 8000/docs | *Apenas desenvolvimento (não produção) |

---

## Usando a API no Azure

Se a API já estiver hospedada no Azure, siga estas instruções para autenticar e chamar os endpoints.

### 1. Obter Acesso

Você precisará de:
- **URL da API**: fornecida pelo administrador (ex: `http://20.201.82.8:8000`)
- **API Key**: chave de autenticação fornecida separadamente

### 2. Autenticação

Todas as requisições protegidas devem incluir o header `X-API-Key`:

```bash
# Exemplo de header
X-API-Key: sua-api-key-aqui
```

### 3. Testando a Conexão

```bash
# Substitua URL e API_KEY pelos valores fornecidos
API_URL="http://20.201.82.8:8000"
API_KEY="sua-api-key-aqui"

# Health check
curl -H "X-API-Key: $API_KEY" \
  "$API_URL/health"
```

Resposta esperada:
```json
{
  "status": "healthy",
  "version": "0.8.0",
  "environment": "production"
}
```

### 4. Chamando Endpoints

#### Análise de Texto

```bash
curl -X POST "$API_URL/analyze/text" \
  -H "Content-Type: application/json" \
  -H "X-API-Key: $API_KEY" \
  -d '{
    "texto": "Estou me sentindo muito ansiosa e com medo",
    "tipo": "diario",
    "patient_id": "uuid-do-paciente-123"
  }'
```

Resposta:
```json
{
  "sentimento": "negativo",
  "score": -0.85,
  "risco_violencia": "alto",
  "risco_saude_mental": "alto",
  "palavras_chave": ["ansiosa", "medo"],
  "indicadores": ["ansiedade", "expressao_medo"],
  "metadata": {
    "correlation_id": "abc-123",
    "timestamp": "2026-04-23T14:30:00Z",
    "tempo_processamento_ms": 450
  }
}
```

#### Análise de Áudio

```bash
# Upload de arquivo de áudio
curl -X POST "$API_URL/analyze/audio" \
  -H "X-API-Key: $API_KEY" \
  -F "file=@/caminho/para/audio.wav" \
  -F "patient_id=uuid-do-paciente-123"
```

#### Análise de Vídeo

```bash
# Upload de arquivo de vídeo
curl -X POST "$API_URL/analyze/video" \
  -H "X-API-Key: $API_KEY" \
  -F "video=@/caminho/para/video.mp4" \
  -F "tipo=consulta" \
  -F "patient_id=uuid-do-paciente-123"
```

#### Análise Multimodal

```bash
# Combinar texto, áudio e vídeo
curl -X POST "$API_URL/analyze/multimodal" \
  -H "X-API-Key: $API_KEY" \
  -F "texto=Estou me sentindo ansiosa" \
  -F "audio=@/caminho/para/audio.wav" \
  -F "video=@/caminho/para/video.mp4" \
  -F "patient_id=uuid-do-paciente-123"
```

### 5. Tratamento de Erros

#### 401 - Não Autorizado

```json
{
  "detail": "API Key inválida ou ausente"
}
```

**Solução**: Verifique se o header `X-API-Key` está correto.

#### 429 - Muitas Requisições

```json
{
  "error": "RateLimitExceeded",
  "message": "Limite de requisições excedido",
  "retry_after": 60
}
```

**Solução**: Aguarde o tempo indicado em `retry_after` antes de tentar novamente.

#### 503 - Serviço Indisponível (Quota Azure)

```json
{
  "error": "QuotaExceeded",
  "message": "Quota do Azure excedida. Tente amanhã.",
  "service": "text",
  "reset_time": "2026-04-24T00:00:00Z"
}
```

**Solução**: Aguarde até o horário de reset ou use o modo mock localmente.

### 6. Documentação da API (OpenAPI)

**NOTA:** Swagger UI e ReDoc estão **desabilitados em produção** porque a API roda em HTTP (não HTTPS). Navegadores modernos bloqueiam recursos de CDN externos em páginas HTTP por segurança (Mixed Content).

Para acessar a documentação em produção:

1. **Baixe o OpenAPI JSON:**
```bash
curl -H "X-API-Key: sua-api-key" \
  "http://20.201.82.8:8000/openapi.json" > openapi.json
```

2. **Importe em Postman/Insomnia:**
   - Postman: File → Import → Upload Files → openapi.json
   - Insomnia: Workspace → Import/Export → Import Data → From File

3. **Configure o Environment:**
   - `base_url`: http://20.201.82.8:8000
   - `api_key`: sua-api-key

### 7. Limites e Rate Limiting

| Endpoint | Limite | Janela |
|----------|--------|--------|
| Geral | 60 req/min | 1 minuto |
| Auth | 5 req/min | 1 minuto |
| Health/Docs | Ilimitado | - |

**Headers de Rate Limit** (incluídos em toda resposta):

```http
X-RateLimit-Limit: 60
X-RateLimit-Remaining: 59
X-RateLimit-Reset: 58
```

### 7. Collection Postman/Insomnia

Baixe as collections em `docs/collection.json` e `docs/environment.json` para importar no Postman ou Insomnia com todos os endpoints configurados.

#### Importar no Postman:

1. File → Import → Upload Files
2. Selecione `docs/collection.json`
3. Selecione `docs/environment.json`
4. No environment, configure:
   - `base_url`: URL da API Azure
   - `api_key`: Sua API Key

### 9. Exemplo em Python

```python
import requests

API_URL = "http://20.201.82.8:8000"
API_KEY = "sua-api-key-aqui"

headers = {
    "X-API-Key": API_KEY,
    "Content-Type": "application/json"
}

# Análise de texto
response = requests.post(
    f"{API_URL}/analyze/text",
    headers=headers,
    json={
        "texto": "Estou me sentindo ansiosa",
        "tipo": "diario"
    }
)

print(response.json())
```

### 10. Exemplo em JavaScript

```javascript
const API_URL = 'http://20.201.82.8:8000';
const API_KEY = 'sua-api-key-aqui';

// Análise de texto
fetch(`${API_URL}/analyze/text`, {
  method: 'POST',
  headers: {
    'Content-Type': 'application/json',
    'X-API-Key': API_KEY
  },
  body: JSON.stringify({
    texto: 'Estou me sentindo ansiosa',
    tipo: 'diario'
  })
})
.then(response => response.json())
.then(data => console.log(data));
```
