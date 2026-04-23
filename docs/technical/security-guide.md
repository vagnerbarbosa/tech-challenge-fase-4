# Guia de Segurança - Multimodal Health Analysis API

> **Versão**: 1.0  
> **Última Atualização**: 2026-04-23  
> **Público-Alvo**: Desenvolvedores de todas as senioridades (Júnior, Pleno, Sênior)  
> **Escopo**: Implementação, execução e testes do sistema de segurança

---

## Índice

1. [Visão Geral](#1-visão-geral)
2. [Arquitetura de Segurança](#2-arquitetura-de-segurança)
3. [Executando Localmente](#3-executando-localmente)
4. [Testes de Segurança](#4-testes-de-segurança)
5. [Deploy no Azure](#5-deploy-no-azure)
6. [Checklist de Segurança](#6-checklist-de-segurança)
7. [Troubleshooting](#7-troubleshooting)

---

## 1. Visão Geral

### 1.1 O que é este Guia?

Este guia explica **como implementamos um sistema de segurança completo** na Multimodal Health Analysis API, seguindo:

- **OWASP API Security Top 10 2023/2026**
- **OWASP ASVS (Application Security Verification Standard)**
- **LGPD (Lei Geral de Proteção de Dados)**

### 1.2 Camadas de Segurança Implementadas

```
┌─────────────────────────────────────────────────────────────┐
│                    SECURITY LAYERS                         │
├─────────────────────────────────────────────────────────────┤
│  Layer 1: HTTP Security Headers (HSTS, CSP, etc)           │
│  Layer 2: CORS (Cross-Origin Resource Sharing)              │
│  Layer 3: Rate Limiting (DDoS/Brute Force Protection)       │
│  Layer 4: Authentication (API Key)                          │
│  Layer 5: Authorization (RBAC + BOLA Protection)          │
│  Layer 6: Input Validation (Pydantic + Custom Validators)  │
│  Layer 7: Audit Logging (LGPD Compliance)                  │
│  Layer 8: File Upload Security (Magic Bytes, Sanitization)   │
└─────────────────────────────────────────────────────────────┘
```

---

## 2. Arquitetura de Segurança

### 2.1 Estrutura de Arquivos

```
src/core/security/
├── __init__.py              # Exports principais
├── auth.py                  # API Key validation, RBAC, BOLA
├── middleware.py            # CORS, Security Headers
├── rate_limiter.py          # Token Bucket rate limiting
├── models.py                # SecurityContext, audit models
├── audit_logger.py          # LGPD-compliant logging
├── file_validator.py        # Upload security
└── config.py                # Security-specific config

src/api/middleware/
├── rate_limit.py            # RateLimitMiddleware (FastAPI)
├── security_headers.py      # SecurityHeadersMiddleware
└── audit.py                 # AuditMiddleware
```

### 2.2 Componentes Principais

#### 2.2.1 Authentication (API Key)

**O que faz**: Valida API keys em todas as requisições protegidas.

**Como funciona**:
```python
# Em src/core/security/auth.py
class APIKeyValidator:
    def validate(self, api_key: str) -> bool:
        # Comparação em tempo constante (timing-safe)
        return secrets.compare_digest(api_key, self.config.api_key)

    def get_security_context(self, api_key: str, ...) -> SecurityContext:
        # Retorna contexto com roles baseadas na key
        roles = self._determine_roles(api_key)
        return SecurityContext(..., roles=roles)
```

**Para Júnior**: Sempre use `secrets.compare_digest()` para comparar keys, nunca `==`. Isso previne ataques de timing.

#### 2.2.2 Authorization (RBAC + BOLA)

**RBAC (Role-Based Access Control)**: Define permissões por papel.
```python
# Roles disponíveis:
- "read": Pode ler dados (todos usuários autenticados)
- "write": Pode criar/analisar dados
- "admin": Acesso total, bypass BOLA
```

**BOLA (Broken Object Level Authorization)**: Proteção contra acesso a recursos de outros usuários.
```python
# Em src/core/security/auth.py
class BOLAProtector:
    def verify_ownership(self, ctx, resource_owner_id, resource_id):
        # Admin bypass
        if "admin" in ctx.roles:
            return True

        # Verifica se usuário é dono do recurso
        if ctx.api_key_hash != resource_owner_id:
            raise ForbiddenException("Acesso negado ao recurso")
```

**Para Pleno**: O BOLA é validado em camada de serviço, não apenas no middleware. Isso garante proteção mesmo se o middleware for bypassado.

#### 2.2.3 Rate Limiting

**Algoritmo**: Token Bucket

```python
# Configuração em src/core/config.py
class Settings:
    RATE_LIMIT_ENABLED: bool = True
    RATE_LIMIT_PER_MINUTE: int = 60      # Geral
    AUTH_RATE_LIMIT_PER_MINUTE: int = 5   # Auth endpoints
```

**Implementação**:
```python
# Token Bucket - em src/core/security/rate_limiter.py
class TokenBucket:
    def __init__(self, capacity: int, refill_rate: float):
        self.capacity = capacity    # Máximo de tokens
        self.tokens = capacity      # Tokens disponíveis
        self.refill_rate = refill_rate  # Tokens/segundo

    async def is_allowed(self, key: str) -> tuple[bool, dict]:
        # Refill tokens based on time elapsed
        # Return (allowed, info_dict)
```

**Headers de Resposta**:
```http
X-RateLimit-Limit: 60
X-RateLimit-Remaining: 59
X-RateLimit-Reset: 58
Retry-After: 60  # Quando 429
```

#### 2.2.4 CORS (Cross-Origin Resource Sharing)

**Configuração**:
```python
# Em src/core/config.py
class SecurityConfig:
    cors_origins: str = "http://localhost:3000,http://localhost:8000"
    cors_credentials: bool = True
```

**Regras**:
- ❌ `*` nunca permitido em produção
- ✅ Preflight requests validados
- ✅ Warning em logs se CORS insecure

**Para Sênior**: O middleware de rate limiting é executado ANTES do CORS para evitar DDoS em preflight requests.

#### 2.2.5 Security Headers

**Headers Implementados** (OWASP compliant):

| Header | Valor | Proteção |
|--------|-------|----------|
| `Strict-Transport-Security` | `max-age=31536000; includeSubDomains` | HTTPS forcing (HSTS) |
| `X-Content-Type-Options` | `nosniff` | MIME sniffing |
| `X-Frame-Options` | `DENY` | Clickjacking |
| `Content-Security-Policy` | Ver abaixo | XSS, injection |
| `X-XSS-Protection` | `1; mode=block` | XSS legacy |
| `Referrer-Policy` | `strict-origin-when-cross-origin` | Privacy |

**CSP (Content Security Policy)**:
```http
Content-Security-Policy: default-src 'self'; script-src 'self'; style-src 'self' 'unsafe-inline'; img-src 'self' data:; font-src 'self'; connect-src 'self'; frame-ancestors 'none'; upgrade-insecure-requests
```

#### 2.2.6 Audit Logging (LGPD)

**O que logamos**:
```json
{
  "timestamp": "2026-04-23T14:30:00Z",
  "event_type": "api_request",
  "request_id": "abc-123",
  "method": "POST",
  "path": "/analyze/text",
  "user_hash": "sha256-of-api-key",
  "ip_hash": "sha256-of-ip",
  "status_code": 200,
  "duration_ms": 450,
  "risk_flags": ["risco_violencia_alto"]
}
```

**Proteções LGPD**:
- 🔐 PII hasheada (patient_id, IP)
- 🔒 Campos sensíveis nunca logados em plain text
- ⏱️ Retenção: 365 dias (configurável)
- ✅ Integridade: SHA-256 checksums

---

## 3. Executando Localmente

Esta seção foi escrita para **qualquer pessoa** conseguir rodar a aplicação, independente da experiência. Escolha o caminho que melhor se adequa ao seu nível.

### 3.1 Entendendo as Opções

| Método | Dificuldade | Quando Usar | Tempo Estimado |
|--------|-------------|-------------|----------------|
| **Docker (Automático)** | ⭐ Fácil | Primeira vez, Windows, ou quando quiser focar apenas no código | 5 minutos |
| **Docker (Manual)** | ⭐⭐ Médio | Quando precisa de controle sobre containers | 10 minutos |
| **Poetry (Local)** | ⭐⭐⭐ Avançado | Desenvolvimento diário, debugging profundo | 15 minutos |

---

### 3.2 Opção 1: Docker Automático (Recomendado para Todos)

> **Para quem é**: Você quer rodar a aplicação AGORA sem se preocupar com dependências.

#### Passo 1: Verifique se tem o Docker instalado

```bash
# Execute no terminal:
docker --version
docker-compose --version

# Deve mostrar versões (ex: Docker version 24.0.0)
# Se não tiver, instale em: https://docs.docker.com/get-docker/
```

#### Passo 2: Clone o projeto

```bash
# No terminal, execute:
git clone https://github.com/vagnerbarbosa/tech-challenge-fase-4.git

# Entre na pasta do projeto:
cd tech-challenge-fase-4
```

#### Passo 3: Execute o script mágico

```bash
# Linux/Mac:
./scripts/run-mock.sh

# Windows (Git Bash):
bash ./scripts/run-mock.sh
```

**O que este script faz automaticamente:**
1. 🐳 Build da imagem Docker
2. 🚀 Sobe a API na porta 8000
3. 🤖 Sobe mocks do Azure nas portas 3001 e 3002
4. 🔄 Sobe o Redis na porta 6379
5. ✅ Mostra mensagem quando está pronto

#### Passo 4: Verifique se funcionou

```bash
# Abra OUTRO terminal e execute:
curl http://localhost:8000/health

# Deve retornar:
# {"status": "healthy", "version": "0.6.0"}
```

**🎉 Parabéns!** A API está rodando!

#### Passo 5: Teste a segurança (básico)

```bash
# Teste 1: Sem API Key (deve dar erro)
curl http://localhost:8000/health
# Esperado: {"detail":"API Key inválida ou ausente"}

# Teste 2: Com API Key (deve funcionar)
curl -H "X-API-Key: dev-api-key" http://localhost:8000/health
# Esperado: {"status": "healthy", ...}
```

---

### 3.3 Opção 2: Docker Manual (Para quem quer entender)

> **Para quem é**: Você quer entender o que cada comando faz ou precisa customizar algo.

#### Passo 1: Clone e entre no projeto

```bash
git clone https://github.com/vagnerbarbosa/tech-challenge-fase-4.git
cd tech-challenge-fase-4
```

#### Passo 2: Configure as variáveis de ambiente

```bash
# Copie o arquivo de exemplo:
cp .env.example .env

# Gere uma API key (anote o resultado):
openssl rand -hex 32
```

**Edite o arquivo `.env`** com seu editor favorito:
```bash
# Use nano (Linux/Mac):
nano .env

# Ou VS Code:
code .env
```

**Adicione estas linhas no final do arquivo:**
```env
SECURITY_API_KEY=sua-key-aqui  # Cole a key gerada acima
SECURITY_ENVIRONMENT=development
```

#### Passo 3: Build da imagem Docker

```bash
# Este comando cria a imagem Docker (pode levar alguns minutos na primeira vez):
docker-compose -f docker-compose.mock.yml build

# Você verá muitas linhas de output - isso é normal!
```

#### Passo 4: Inicie os serviços

```bash
# Inicie em modo detached (background):
docker-compose -f docker-compose.mock.yml up -d

# Veja se está rodando:
docker-compose -f docker-compose.mock.yml ps
```

#### Passo 5: Verifique os logs

```bash
# Veja os logs da API:
docker-compose -f docker-compose.mock.yml logs -f api

# Pressione Ctrl+C para sair (não para o container)
```

#### Passo 6: Pare quando quiser

```bash
# Quando quiser parar:
docker-compose -f docker-compose.mock.yml down
```

---

### 3.4 Opção 3: Poetry Local (Para desenvolvedores Python)

> **Para quem é**: Você é desenvolvedor Python e quer rodar direto na sua máquina para debugging ou desenvolvimento ativo.

#### Pré-requisitos

```bash
# Verifique se tem Python 3.11+:
python3 --version

# Verifique se tem Poetry:
poetry --version

# Se não tiver Poetry, instale:
curl -sSL https://install.python-poetry.org | python3 -
```

#### Passo 1: Clone e configure

```bash
git clone https://github.com/vagnerbarbosa/tech-challenge-fase-4.git
cd tech-challenge-fase-4

# Copie o .env:
cp .env.example .env
```

#### Passo 2: Instale as dependências

```bash
# Instala todas as dependências (pode levar alguns minutos):
poetry install --extras security

# Saída esperada: "Installing dependencies from lock file"
```

#### Passo 3: Ative o ambiente Poetry

```bash
# Opção A: Entre no shell do Poetry (recomendado)
poetry shell
# Seu prompt mudará para mostrar que está no ambiente

# Opção B: Use 'poetry run' antes de cada comando
poetry run python src/api/main.py
```

#### Passo 4: Configure a API Key

```bash
# Gere uma key:
openssl rand -hex 32

# Edite o .env e adicione:
# SECURITY_API_KEY=sua-key-aqui
```

#### Passo 5: Execute a API

```bash
# Se você está no shell do Poetry (prompt alterado):
uvicorn src.api.main:app --reload --port 8000

# Se você NÃO está no shell (use poetry run):
poetry run uvicorn src.api.main:app --reload --port 8000
```

**Você verá:**
```
INFO:     Uvicorn running on http://127.0.0.1:8000
INFO:     Application startup complete.
```

#### Passo 6: Acesse a documentação

Abra no navegador: http://localhost:8000/docs

---

### 3.5 Guia Rápido: Comandos por Nível

#### Para Júnior (Comece aqui!)

```bash
# 1. Clone
git clone https://github.com/vagnerbarbosa/tech-challenge-fase-4.git
cd tech-challenge-fase-4

# 2. Execute (Docker faz tudo automaticamente)
./scripts/run-mock.sh

# 3. Teste em outro terminal
curl -H "X-API-Key: dev-api-key" http://localhost:8000/health
```

#### Para Pleno (Quer mais controle)

```bash
# Setup completo manual
git clone https://github.com/vagnerbarbosa/tech-challenge-fase-4.git
cd tech-challenge-fase-4
cp .env.example .env
# Edite .env com suas configurações
docker-compose -f docker-compose.mock.yml up -d --build
```

#### Para Sênior (Desenvolvimento ativo)

```bash
# Poetry com hot reload
git clone https://github.com/vagnerbarbosa/tech-challenge-fase-4.git
cd tech-challenge-fase-4
cp .env.example .env
poetry install --extras security
poetry shell
uvicorn src.api.main:app --reload --port 8000
```

---

### 3.6 Testando a Segurança Manualmente

Depois que a aplicação está rodando, teste cada camada de segurança:

#### Teste 1: API Key obrigatória (Authentication)

```bash
# ❌ Sem API Key - deve retornar 401 (Não autorizado)
curl http://localhost:8000/health
echo "^ Deve mostrar erro de autenticação"

# ✅ Com API Key correta - deve retornar 200 (OK)
curl -H "X-API-Key: dev-api-key" http://localhost:8000/health
echo "^ Deve mostrar {\"status\": \"healthy\"}"

# ❌ Com API Key errada - deve retornar 401
curl -H "X-API-Key: key-errada" http://localhost:8000/health
echo "^ Deve mostrar erro de autenticação"
```

#### Teste 2: Rate Limiting (Proteção contra abuso)

```bash
# Faça muitas requisições rápidas (60+ por minuto)
# Em Linux/Mac:
for i in {1..65}; do
  curl -s -o /dev/null -w "%{http_code}\n" \
    -H "X-API-Key: dev-api-key" \
    http://localhost:8000/health
done

# Você verá:
# 200 (sucesso)
# 200 (sucesso)
# ...
# 429 (muitas requisições - rate limit atingido!)
```

#### Teste 3: Headers de Segurança OWASP

```bash
# Veja os headers de segurança
curl -I -H "X-API-Key: dev-api-key" http://localhost:8000/health

# Procure por:
# X-Content-Type-Options: nosniff        ← Protege contra MIME sniffing
# X-Frame-Options: DENY                 ← Protege contra clickjacking
# Strict-Transport-Security: ...        ← Força HTTPS (HSTS)
# Content-Security-Policy: ...          ← Previne XSS
```

#### Teste 4: CORS (Cross-Origin Resource Sharing)

```bash
# Simule uma requisição de outro site
curl -X OPTIONS \
  -H "Origin: http://localhost:3000" \
  -H "Access-Control-Request-Method: GET" \
  -H "X-API-Key: dev-api-key" \
  http://localhost:8000/health

# Deve retornar 200 com headers CORS
```

#### Teste 5: Swagger UI (Documentação Interativa)

```bash
# Abra no navegador:
# http://localhost:8000/docs

# Clique em um endpoint → "Try it out" → "Execute"
# Adicione a API key clicando no cadeado 🔒 no topo da página
```

---

## 4. Testes de Segurança

Esta seção explica **como testar** se a segurança está funcionando corretamente. Você não precisa entender todos os detalhes - siga os passos de acordo com seu nível.

### 4.1 Tipos de Testes de Segurança

| Tipo | O que verifica | Importância |
|------|----------------|-------------|
| **Unitários** | Funções individuais de segurança | ⭐⭐⭐ Alta |
| **Integração** | Fluxos completos (ex: auth + rate limit) | ⭐⭐⭐ Alta |
| **SAST** | Código fonte por vulnerabilidades | ⭐⭐⭐ Alta |
| **SCA** | Dependências por vulnerabilidades | ⭐⭐ Alta |
| **Carga** | Performance sob ataque | ⭐⭐ Média |

---

### 4.2 Para Júnior: Testes Automáticos Simples

Execute tudo com um comando:

```bash
# Este script executa TODOS os testes de segurança
./scripts/test-docker.sh security

# Ou, se preferir ver em tempo real:
./scripts/test-docker.sh security 2>&1 | tee test-output.txt
```

**O que você verá:**
```
==============================
tests/security/test_csp_policy.py::TestCSPSecurity PASSED
tests/security/test_api_key_validator.py::TestAPIKeyValidator PASSED
...
============================== 45 passed in 12.34s
```

> **Dica**: Se algum teste falhar, não se preocupe! Veja a seção [Troubleshooting](#7-troubleshooting).

---

### 4.3 Para Pleno: Executar Testes Específicos

Às vezes você quer testar apenas uma parte. Aqui está como:

#### Testar apenas autenticação:
```bash
# Testa API Key, RBAC e BOLA
poetry run pytest tests/security/test_api_key_validator.py -v
```

#### Testar apenas rate limiting:
```bash
# Testa o algoritmo token bucket
poetry run pytest tests/unit/security/test_rate_limiter.py -v
```

#### Testar apenas CSP (Content Security Policy):
```bash
# Testa headers CSP
poetry run pytest tests/security/test_csp_policy.py -v
```

#### Testar apenas CORS:
```bash
# Testa CORS em diferentes cenários
poetry run pytest tests/integration/test_cors_production.py -v
```

---

### 4.4 Para Sênior: Análise Estática (SAST) com Bandit

O Bandit procura automaticamente por padrões de código inseguros.

#### Executar Bandit:

```bash
# Análise completa
poetry run bandit -r src/ -f json -o bandit-report.json

# Ou análise rápida no terminal
poetry run bandit -r src/ -ll
```

#### Entender os resultados:

```
Issue: [B105:hardcoded_password_string] Possible hardcoded password
Location: src/example.py:10
CWE: CWE-259
```

**Categorias de severidade:**
- **LOW**: Problemas de baixo risco (ex: uso de `assert`)
- **MEDIUM**: Problemas médios (ex: hardcoded strings)
- **HIGH**: Problemas graves (ex: execução de código dinâmico)

#### Corrigir falhas comuns:

**❌ Erro: Hardcoded password**
```python
# Antes (Bandit reclama):
if password == "admin123":  # B105
    ...

# Depois (Correto):
import secrets
if secrets.compare_digest(password, settings.admin_password):
    ...
```

**❌ Erro: Uso de `eval()`**
```python
# Antes (Muito perigoso!):
result = eval(user_input)  # B307

# Depois (Correto):
import json
result = json.loads(user_input)
```

---

### 4.5 Para Sênior: Análise de Dependências (SCA) com Safety

Verifica se alguma biblioteca Python tem vulnerabilidades conhecidas.

#### Executar Safety:

```bash
# Verificação completa
poetry run safety check

# Com saída JSON (para CI/CD)
poetry run safety check --json
```

#### Manter dependências atualizadas:

```bash
# Atualiza todas as dependências (faça mensalmente)
poetry update

# Atualiza apenas segurança (mais seguro)
poetry update --only=security
```

---

### 4.6 Tabela de Testes de Segurança Disponíveis

| Categoria | Arquivo | Descrição Simples | Comando |
|-----------|---------|-------------------|---------|
| Auth | `test_api_key_validator.py` | Testa login com API key | `pytest tests/security/test_api_key_validator.py` |
| Rate Limit | `test_rate_limiter.py` | Testa proteção contra muitas requisições | `pytest tests/unit/security/test_rate_limiter.py` |
| CSP | `test_csp_policy.py` | Testa headers anti-XSS | `pytest tests/security/test_csp_policy.py` |
| CORS | `test_cors_production.py` | Testa acesso de outros sites | `pytest tests/integration/test_cors_production.py` |
| CORS Origins | `test_cors_origins.py` | Testa lista de sites permitidos | `pytest tests/integration/test_cors_origins.py` |
| File Upload | `test_file_upload_security.py` | Testa upload de arquivos | `pytest tests/security/test_file_upload_security.py` |
| Audit | `test_audit_integration.py` | Testa logs de auditoria | `pytest tests/integration/test_audit_integration.py` |
| Middleware | `test_security_middleware.py` | Testa camadas de proteção | `pytest tests/security/test_security_middleware.py` |
| BOLA | Dentro de `test_api_key_validator.py` | Testa acesso a recursos alheios | `pytest tests/security/test_api_key_validator.py::TestBOLAProtector` |

---

### 4.7 Checklist de Testes para Pull Request

Antes de abrir um PR, execute este checklist:

```bash
# 1. Todos os testes de segurança passam
poetry run pytest tests/security/ -v --tb=short

# 2. Análise estática passa (sem erros HIGH/MEDIUM)
poetry run bandit -r src/ -ll

# 3. Dependências estão seguras
poetry run safety check

# 4. Testes de integração passam
poetry run pytest tests/integration/ -v --tb=short -x
```

**Se tudo passar**, pode abrir o PR! ✅

---

## 5. Deploy no Azure

### 5.1 Configuração de Produção

#### Variáveis de Ambiente Obrigatórias

```bash
# .env.production
SECURITY_ENVIRONMENT=production
SECURITY_API_KEY=sua-key-super-secreta-min-32-chars
SECURITY_SECRET_KEY=chave-para-criptografia-dados

# CORS - apenas origens permitidas
SECURITY_CORS_ORIGINS="https://app-segura.com,https://admin.segura.com"

# Rate Limiting
RATE_LIMIT_ENABLED=true
RATE_LIMIT_PER_MINUTE=60

# Azure
AZURE_TEXT_KEY=sua-key-azure
AZURE_TEXT_ENDPOINT=https://seu-endpoint.cognitiveservices.azure.com
```

#### Checklist Pré-Deploy

- [ ] API Key com mínimo 32 caracteres gerada
- [ ] CORS não usa `*`
- [ ] `SECURITY_ENVIRONMENT=production`
- [ ] `DEBUG=false`
- [ ] Rate limiting habilitado
- [ ] HSTS habilitado
- [ ] Audit logging configurado
- [ ] Secrets não commitados (verificar com `git log --all --source --remotes -- '*.env'`)

### 5.2 Azure App Service

```bash
# Deploy via Azure CLI
az webapp up \
  --name health-api-multimodal \
  --resource-group rg-health \
  --runtime "PYTHON:3.11" \
  --sku B1

# Configurar variáveis de ambiente
az webapp config appsettings set \
  --name health-api-multimodal \
  --resource-group rg-health \
  --settings @appsettings.json
```

### 5.3 Azure Key Vault (Recomendado para Produção)

Para secrets em produção, use Azure Key Vault:

```bash
# Criar Key Vault
az keyvault create \
  --name kv-health-api \
  --resource-group rg-health \
  --location brazilsouth

# Adicionar secrets
az keyvault secret set \
  --vault-name kv-health-api \
  --name api-key \
  --value "sua-key-super-secreta"

# Configurar App Service para usar Key Vault
# Em appsettings.json:
{
  "name": "SECURITY_API_KEY",
  "value": "@Microsoft.KeyVault(SecretName=api-key)"
}
```

### 5.4 HTTPS e Custom Domain

```bash
# Configurar HTTPS obrigatório
az webapp update \
  --name health-api-multimodal \
  --resource-group rg-health \
  --set httpsOnly=true

# Configurar custom domain (opcional)
az webapp config hostname add \
  --webapp-name health-api-multimodal \
  --resource-group rg-health \
  --hostname api.seudominio.com
```

### 5.5 WAF (Web Application Firewall)

Para proteção adicional DDoS:

```bash
# Criar Application Gateway com WAF
az network application-gateway create \
  --name ag-health \
  --resource-group rg-health \
  --sku WAF_v2 \
  --public-ip-address pip-health
```

---

## 6. Checklist de Segurança

### 6.1 Checklist Desenvolvimento

```markdown
## Antes de Commit

- [ ] Nenhum secret em código (use `git add -p` para revisar)
- [ ] Bandit passou sem erros (`poetry run bandit -r src/`)
- [ ] Testes de segurança passaram (`poetry run pytest tests/security/ -v`)
- [ ] Logs não expõem PII
- [ ] Validações de input implementadas

## Antes de Deploy

- [ ] `.env.production` configurado
- [ ] API Key >= 32 caracteres
- [ ] CORS não usa `*`
- [ ] Rate limiting habilitado
- [ ] HSTS habilitado (produção)
- [ ] Audit logging configurado
- [ ] Azure Key Vault configurado (se aplicável)
```

### 6.2 Verificação Automatizada

```bash
# Script completo de verificação
./scripts/security-check.sh

# Ou manualmente:
echo "=== Bandit (SAST) ==="
poetry run bandit -r src/ -ll

echo "=== Safety (SCA) ==="
poetry run safety check

echo "=== Testes de Segurança ==="
poetry run pytest tests/security/ -v --tb=short

echo "=== Verificação de Secrets ==="
git log --all --source --remotes -- '*.env' '*.key' '*.pem' 2>/dev/null || echo "OK - No secrets in git"
```

---

## 7. Troubleshooting

### 7.1 Problemas Comuns

#### ❌ "401 Unauthorized" em todos requests

**Causa**: API Key não configurada ou incorreta.

**Solução**:
```bash
# Verifique se .env existe
cat .env | grep SECURITY_API_KEY

# Gere uma nova key
openssl rand -hex 32

# Teste manualmente
curl -H "X-API-Key: sua-key" http://localhost:8000/health
```

#### ❌ "429 Too Many Requests" imediatamente

**Causa**: Rate limit backend em memória pode estar em estado inconsistente.

**Solução**:
```bash
# Reinicie o servidor
# O backend em memória é resetado

# Ou use Redis para rate limit persistente
# Em .env:
REDIS_URL=redis://localhost:6379/0
```

#### ❌ Testes de rate limit falham no TestClient

**Causa**: Backend em memória do rate limiter é resetado entre requisições no TestClient.

**Solução**: Isso é uma limitação conhecida do TestClient. Para testes de rate limit completos, use Redis ou execute testes de carga com Locust.

```bash
# Executar testes de carga reais
poetry run locust -f tests/load/locustfile.py
```

#### ❌ Bandit reporta "hardcoded password"

**Causa**: String que parece senha em código.

**Solução**:
```python
# Adicione comentário de skip se for falso positivo
password = "default"  # nosec: B105 - valor padrão documentado

# Ou mova para variável de ambiente
password = settings.default_password
```

#### ❌ CORS bloqueando requisições do frontend

**Causa**: Origem não configurada em `SECURITY_CORS_ORIGINS`.

**Solução**:
```bash
# No .env, adicione a origem do frontend:
SECURITY_CORS_ORIGINS="http://localhost:3000,http://localhost:8000,https://meu-app.com"
```

### 7.2 Debug de Segurança

#### Habilitar Logs Detalhados

```bash
# Em .env
LOG_LEVEL=debug
SECURITY_LOG_LEVEL=debug

# Ver logs de segurança
tail -f logs/security.log
tail -f logs/audit/audit-*.log
```

#### Verificar Middleware Stack

```python
# Em src/api/main.py, adicione temporariamente:
@app.on_event("startup")
async def print_middleware():
    print("Middlewares registrados:")
    for middleware in app.user_middleware:
        print(f"  - {middleware.cls.__name__}")
```

#### Testar Rate Limit Manualmente

```python
# Script de teste rápido
import asyncio
import httpx

async def test_rate_limit():
    async with httpx.AsyncClient() as client:
        for i in range(65):
            r = await client.get(
                "http://localhost:8000/health",
                headers={"X-API-Key": "test-key"}
            )
            print(f"Request {i}: {r.status_code}")
            if r.status_code == 429:
                print(f"Rate limited! Retry after: {r.headers.get('Retry-After')}")
                break

asyncio.run(test_rate_limit())
```

---

## 8. Recursos Adicionais

### 8.1 Documentação Oficial

- [OWASP API Security Top 10](https://owasp.org/www-project-api-security/)
- [OWASP ASVS](https://owasp.org/www-project-application-security-verification-standard/)
- [FastAPI Security](https://fastapi.tiangolo.com/tutorial/security/)
- [Azure Security Best Practices](https://docs.microsoft.com/azure/security/fundamentals/best-practices-and-patterns)

### 8.2 Ferramentas Recomendadas

| Ferramenta | Uso | Comando |
|------------|-----|---------|
| Bandit | SAST | `poetry run bandit -r src/` |
| Safety | SCA | `poetry run safety check` |
| Semgrep | SAST avançado | `semgrep --config=auto src/` |
| TruffleHog | Secret scanning | `truffleHog git file://.` |

### 8.3 Contato e Suporte

- **Issues**: [GitHub Issues](https://github.com/vagnerbarbosa/tech-challenge-fase-4/issues)
- **Security Reports**: Envie para vagner.barbosa@gmail.com com assunto "[SECURITY]"

---

## 9. Glossário

| Termo | Significado |
|-------|-------------|
| **API Key** | Chave de autenticação para acessar a API |
| **BOLA** | Broken Object Level Authorization - vulnerabilidade de acesso a recursos |
| **CORS** | Cross-Origin Resource Sharing - compartilhamento entre origens |
| **CSP** | Content Security Policy - política de conteúdo |
| **HSTS** | HTTP Strict Transport Security - força HTTPS |
| **LGPD** | Lei Geral de Proteção de Dados |
| **PII** | Personally Identifiable Information - dados pessoais |
| **RBAC** | Role-Based Access Control - controle por papéis |
| **SAST** | Static Application Security Testing - análise estática |
| **SCA** | Software Composition Analysis - análise de dependências |
| **WAF** | Web Application Firewall - firewall de aplicação |

---

**Fim do Guia** ✓

Para atualizações, verifique o repositório oficial ou execute `./scripts/security-check.sh`.
