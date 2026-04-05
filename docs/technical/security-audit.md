# Análise de Vulnerabilidades - Deep Dive de Segurança

**Data**: 2026-04-05
**Projeto**: Tech Challenge Fase 4 - Sistema Multimodal de Análise de Saúde
**Classificação**: Confidencial - Documento Interno
**Status**: ✅ Análise Completa

---

## 🚨 Resumo Executivo de Segurança

### Classificação de Risco Geral: 🔴 **MÉDIO-ALTO**

**Vulnerabilidades Críticas**: 2
**Vulnerabilidades Altas**: 5
**Vulnerabilidades Médias**: 8
**Vulnerabilidades Baixas**: 4

**Observação**: Nenhuma vulnerabilidade crítica de arquitetura. A maioria pode ser mitigada durante a implementação.

---

## 📊 Inventário de Vulnerabilidades por Categoria

| Categoria OWASP | Quantidade | Severidade Máxima |
|----------------|------------|-------------------|
| **A01: Broken Access Control** | 2 | 🔴 Alta |
| **A02: Cryptographic Failures** | 2 | 🔴 Alta |
| **A03: Injection** | 2 | 🟡 Média |
| **A04: Insecure Design** | 3 | 🔴 Alta |
| **A05: Security Misconfiguration** | 4 | 🔴 Alta |
| **A06: Vulnerable Components** | 1 | 🟢 Baixa |
| **A07: Auth Failures** | 3 | 🔴 Alta |
| **A08: Data Integrity** | 1 | 🟡 Média |
| **A09: Logging Failures** | 2 | 🟡 Média |
| **A10: SSRF** | 1 | 🟢 Baixa |

---

## 🔴 VULNERABILIDADES CRÍTICAS (CVSS 9.0-10.0)

### V-CRIT-001: Ausência Completa de Autenticação
**Categoria**: A07:2021 - Identification and Authentication Failures
**Severidade**: 🔴 **CRÍTICA (CVSS 9.1)**
**Status**: ✅ Documentado (MVP)

#### Descrição
O MVP está planejado para rodar **SEM autenticação** (linha 26 de `api-contracts.md`):
```
## Autenticação
**MVP**: Sem autenticação (para facilitar demonstração)
**Pós-MVP**: API Key no header `X-API-Key`
```

#### Impacto
- Qualquer pessoa com acesso à URL pode submeter dados sensíveis de saúde
- Exposição de dados médicos (LGPD - vazamento de dados sensíveis)
- Risco de abuso da API (consumir toda a quota Azure)
- Possibilidade de envenenamento de dados

#### Recomendação URGENTE
```python
# Implementar MÍNIMO antes de deploy em produção:
@app.middleware("http")
async def minimal_auth(request: Request, call_next):
    # Opção 1: API Key simples (mínimo viável)
    api_key = request.headers.get("X-API-Key")
    if api_key != os.getenv("API_KEY"):
        raise HTTPException(status_code=401, detail="Unauthorized")

    # Opção 2: JWT básico (recomendado)
    # Implementar com python-jose

    return await call_next(request)
```

**Mitigação Mínima**: Pelo menos uma API Key fixa em variável de ambiente.

---

### V-CRIT-002: Upload de Arquivos sem Restrições de Tipo Verificado
**Categoria**: A04:2021 - Insecure Design
**Severidade**: 🔴 **CRÍTICA (CVSS 9.3)**
**Status**: 🟠 Parcialmente documentado

#### Descrição
O sistema aceita upload de arquivos de áudio e vídeo via `multipart/form-data`:
- `/analyze/audio`: WAV, MP3, OGG
- `/analyze/image`: JPEG, PNG, MP4

**Problema**: A documentação menciona validação de formato (`formato_recebido` no erro 400), mas **NÃO especifica verificação de magic numbers ou análise de conteúdo real**.

#### Cenários de Ataque
1. **Upload de arquivo malicioso com extensão alterada**:
   ```bash
   # Renomear shell script para .wav
   mv payload.sh consulta.wav
   curl -F "audio=@consulta.wav" http://api/analyze/audio
   ```

2. **Polyglot files** (arquivos válidos em múltiplos formatos)

3. **Path Traversal em nomes de arquivo**:
   ```bash
   curl -F "audio=@../etc/passwd" http://api/analyze/audio
   ```

#### Impacto
- Execução remota de código (RCE) se FFmpeg/OpenCV processarem arquivo malicioso
- Path traversal e leitura de arquivos do servidor
- DoS via upload de arquivos gigantescos

#### Recomendação URGENTE
```python
import magic  # python-magic
from pathlib import Path

ALLOWED_AUDIO_TYPES = {
    'audio/wav': '.wav',
    'audio/mpeg': '.mp3',
    'audio/ogg': '.ogg',
    'audio/x-wav': '.wav'
}

async def validate_audio_file(file: UploadFile):
    # 1. Validar extensão
    ext = Path(file.filename).suffix.lower()
    if ext not in ['.wav', '.mp3', '.ogg']:
        raise HTTPException(400, "Extensão não permitida")

    # 2. Verificar magic numbers (conteúdo real)
    content = await file.read(2048)  # Primeiros 2KB
    await file.seek(0)

    mime = magic.from_buffer(content, mime=True)
    if mime not in ALLOWED_AUDIO_TYPES:
        raise HTTPException(400, f"Tipo de arquivo não suportado: {mime}")

    # 3. Sanitizar nome de arquivo
    safe_filename = secure_filename(file.filename)  # werkzeug.utils

    # 4. Verificar tamanho (já documentado: 50MB)
    # 5. Salvar em diretório isolado (chroot-like)
```

---

## 🟠 VULNERABILIDADES ALTAS (CVSS 7.0-8.9)

### V-HIGH-001: Secrets Azure em Variáveis de Ambiente sem Proteção
**Categoria**: A05:2021 - Security Misconfiguration
**Severidade**: 🟠 **ALTA (CVSS 7.5)**

#### Descrição
O arquivo `.env.example` (documentado em `001-bootstrap.md`) contém:
```bash
AZURE_TEXT_KEY=your_key_here
AZURE_SPEECH_KEY=your_key_here
AZURE_VISION_KEY=your_key_here
```

**Problemas**:
1. Sem rotação automática de keys
2. Sem separação de secrets por ambiente
3. Sem uso de Azure Key Vault (documentado como opcional)
4. `.env` pode ser commitado por engano

#### Impacto
- Exposição de credenciais Azure em logs ou Git
- Uso não autorizado dos serviços Azure
- Cobranças inesperadas

#### Recomendação
```python
# src/core/config.py
from pydantic_settings import BaseSettings
from azure.identity import DefaultAzureCredential
from azure.keyvault.secrets import SecretClient

class Settings(BaseSettings):
    # Desenvolvimento: usar .env
    # Produção: usar Azure Key Vault
    AZURE_KEY_VAULT_URL: Optional[str] = None

    async def get_azure_secret(self, secret_name: str) -> str:
        if self.AZURE_KEY_VAULT_URL:
            # Produção: Azure Key Vault
            credential = DefaultAzureCredential()
            client = SecretClient(self.AZURE_KEY_VAULT_URL, credential)
            return client.get_secret(secret_name).value
        else:
            # Desenvolvimento: variável de ambiente
            return getattr(self, secret_name)
```

---

### V-HIGH-002: Falta de Rate Limiting na Camada de Aplicação
**Categoria**: A07:2021 - Authentication Failures (DoS)
**Severidade**: 🟠 **ALTA (CVSS 7.1)**

#### Descrição
O rate limiting documentado em `azure-free-tier-hard-stop.md` foca em **proteger a quota Azure**, mas **NÃO protege contra DoS na própria API**:

```python
# O atual rate limiter protege CONTRA o Azure, não CONTRA a API
class QuotaManager:
    FREE_TIER_LIMITS = {...}  # Limites AZURE, não da API
```

#### Impacto
- DoS por flooding de requisições
- Esgotamento de recursos do servidor (CPU, memória)
- Consumo de conexões do pool

#### Recomendação
```python
# src/core/rate_limit.py
from slowapi import Limiter, _rate_limit_exceeded_handler
from slowapi.util import get_remote_address
from slowapi.errors import RateLimitExceeded

limiter = Limiter(key_func=get_remote_address)

app = FastAPI()
app.state.limiter = limiter
app.add_exception_handler(RateLimitExceeded, _rate_limit_exceeded_handler)

# Endpoints protegidos
@app.post("/analyze/text")
@limiter.limit("100/minute")  # Limite por IP
async def analyze_text(request: Request, ...):
    ...

@app.post("/analyze/multimodal")
@limiter.limit("10/minute")   # Mais restritivo para multimodal
async def analyze_multimodal(request: Request, ...):
    ...
```

---

### V-HIGH-003: Ausência de Validação de SSL/TLS para Chamadas Azure
**Categoria**: A02:2021 - Cryptographic Failures
**Severidade**: 🟠 **ALTA (CVSS 7.4)**

#### Descrição
A documentação não menciona configuração de SSL para chamadas aos serviços Azure e APIs externas.

#### Impacto
- Possibilidade de MITM (Man-in-the-Middle)
- Interceptação de dados sensíveis de saúde
- Exposição de credenciais Azure

#### Recomendação
```python
# Em toda chamada HTTP (httpx/aiohttp)
import httpx
import ssl

# Configurar SSL context
ssl_context = ssl.create_default_context()
ssl_context.minimum_version = ssl.TLSVersion.TLSv1_2
ssl_context.check_hostname = True
ssl_context.verify_mode = ssl.CERT_REQUIRED

async with httpx.AsyncClient(verify=ssl_context) as client:
    response = await client.post(...)

# Para Azure SDKs (já fazem isso por padrão, mas documentar)
# Verificar que DEFAULT_SSL_CONTEXT está sendo usado
```

---

### V-HIGH-004: CORS Aberto ou Não Configurado
**Categoria**: A05:2021 - Security Misconfiguration
**Severidade**: 🟠 **ALTA (CVSS 7.1)**

#### Descrição
Nenhuma menção à configuração de CORS (Cross-Origin Resource Sharing) na documentação.

#### Impacto
- CSRF (Cross-Site Request Forgery) em requisições
- Exposição de dados a domínios não autorizados
- Possível bypass de autenticação via CSRF

#### Recomendação
```python
from fastapi.middleware.cors import CORSMiddleware

app = FastAPI()

# Configuração RESTRITIVA (não aberta)
app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "https://portal-saude.exemplo.com",  # Apenas origens conhecidas
        "https://app-mobile.exemplo.com"
    ],
    allow_credentials=True,
    allow_methods=["POST", "GET"],
    allow_headers=["*"],
    max_age=3600,
)
```

**NUNCA usar** `allow_origins=["*"]` em produção.

---

### V-HIGH-005: Ausência de Sanitização de Saída (XSS)
**Categoria**: A03:2021 - Injection
**Severidade**: 🟠 **ALTA (CVSS 7.2)**

#### Descrição
O sistema retorna texto processado (transcrição de áudio) que pode conter conteúdo malicioso:
```json
{
  "transcricao": "Doutor, eu não sei se posso contar... <script>alert('XSS')</script>"
}
```

#### Impacto
- XSS Refletido/Armazenado se dados forem exibidos em frontend
- Injeção de código em relatórios
- Comprometimento de sessões

#### Recomendação
```python
from markupsafe import escape
from html import escape as html_escape

class AudioAnalysisResponse(BaseModel):
    transcricao: str

    @validator('transcricao')
    def sanitize_transcricao(cls, v):
        # 1. Escapar HTML
        v = html_escape(v)

        # 2. Remover scripts (defesa em profundidade)
        import re
        v = re.sub(r'<script.*?</script>', '', v, flags=re.DOTALL | re.IGNORECASE)
        v = re.sub(r'javascript:', '', v, flags=re.IGNORECASE)

        return v
```

---

### V-HIGH-006: Falta de Timeout em Chamadas Azure
**Categoria**: A04:2021 - Insecure Design
**Severidade**: 🟠 **ALTA (CVSS 7.0)**

#### Descrição
Nenhuma menção a timeouts nas chamadas aos serviços Azure. Uma chamada travada pode bloquear workers indefinidamente.

#### Impacto
- DoS por esgotamento de workers
- Degradação de performance
- Deadlocks

#### Recomendação
```python
import asyncio
from httpx import Timeout

TIMEOUT_AZURE = Timeout(
    connect=5.0,      # Timeout de conexão
    read=30.0,        # Timeout de leitura (30s para análise)
    write=5.0,        # Timeout de escrita
    pool=5.0          # Timeout de pool
)

async def call_azure_with_timeout(service_call, timeout_secs=30):
    try:
        return await asyncio.wait_for(
            service_call(),
            timeout=timeout_secs
        )
    except asyncio.TimeoutError:
        raise HTTPException(
            status_code=504,
            detail="Tempo limite excedido ao chamar serviço Azure"
        )
```

---

### V-HIGH-007: Health Check Expondo Informações Sensíveis
**Categoria**: A01:2021 - Broken Access Control
**Severidade**: 🟠 **ALTA (CVSS 7.1)**

#### Descrição
O endpoint `/health` documentado em `api-contracts.md` expõe:
```json
{
  "quota_restante": {
    "text_requests": "4800/5000",
    "audio_minutes": "180/300",
    "vision_requests": "4500/5000"
  }
}
```

#### Impacto
- Exposição de limites internos (facilita ataques planejados)
- Informações sobre uso (leak de dados operacionais)
- Possível reconhecimento de infraestrutura

#### Recomendação
```python
@app.get("/health")
async def health_check(request: Request):
    # Verificar se é requisição interna ou autenticada
    # Opcional: retornar apenas "status": "healthy" para público

    public_response = {
        "status": "healthy",
        "version": "1.0.0",
        "timestamp": datetime.utcnow().isoformat()
    }

    # Detalhes de quota apenas para admins
    if is_admin(request):  # Verificar API key específica
        return detailed_health()

    return public_response
```

---

## 🟡 VULNERABILIDADES MÉDIAS (CVSS 4.0-6.9)

### V-MED-001: Validação de Input Insuficiente (Texto)
**Categoria**: A03:2021 - Injection
**Severidade**: 🟡 **MÉDIA (CVSS 6.5)**

#### Descrição
O campo `texto` aceita 10-5000 caracteres, mas **NÃO há proteção contra**:
- Unicode homoglyphs (caracteres que parecem iguais)
- Zero-width characters
- Control characters
- Injection de prompts (prompt injection para Azure AI)

#### Recomendação
```python
import unicodedata
import re

def sanitize_text_input(text: str) -> str:
    # 1. Normalizar Unicode
    text = unicodedata.normalize('NFKC', text)

    # 2. Remover zero-width characters (steganography)
    zero_width = '\u200B\u200C\u200D\u2060\uFEFF'
    for char in zero_width:
        text = text.replace(char, '')

    # 3. Remover control characters
    text = re.sub(r'[\x00-\x08\x0B\x0C\x0E-\x1F\x7F-\x9F]', '', text)

    # 4. Limitar sequências repetidas (prevenir DoS)
    text = re.sub(r'(.)\1{10,}', r'\1', text)  # Max 10 repetições

    return text.strip()
```

---

### V-MED-002: Ausência de Content Security Policy (CSP)
**Categoria**: A05:2021 - Security Misconfiguration
**Severidade**: 🟡 **MÉDIA (CVSS 5.4)**

#### Descrição
A documentação Swagger (`/docs`) e a API não mencionam CSP headers.

#### Recomendação
```python
@app.middleware("http")
async def security_headers(request: Request, call_next):
    response = await call_next(request)

    # Content Security Policy
    response.headers["Content-Security-Policy"] = (
        "default-src 'self'; "
        "script-src 'self'; "
        "style-src 'self' 'unsafe-inline'; "  # Swagger precisa disso
        "img-src 'self' data:; "
        "connect-src 'self';"
    )

    # Outros headers de segurança
    response.headers["X-Content-Type-Options"] = "nosniff"
    response.headers["X-Frame-Options"] = "DENY"
    response.headers["X-XSS-Protection"] = "1; mode=block"
    response.headers["Referrer-Policy"] = "strict-origin-when-cross-origin"
    response.headers["Permissions-Policy"] = "geolocation=(), microphone=(), camera=()"

    return response
```

---

### V-MED-003: Logging Insuficiente para Auditoria LGPD
**Categoria**: A09:2021 - Security Logging and Monitoring Failures
**Severidade**: 🟡 **MÉDIA (CVSS 5.5)**

#### Descrição
Documentação menciona logging mas **sem detalhes de**:
- Quem acessou (identificador)
- O que foi acessado (endpoint + patient_id)
- Resultado da operação
- Retenção de logs

**LGPD requer**: "registro das operações realizadas com dados pessoais" (art. 46)

#### Recomendação
```python
# src/core/audit_logger.py
import structlog
from datetime import datetime

logger = structlog.get_logger()

async def log_audit_event(
    event_type: str,  # "ANALYSIS_TEXT", "ANALYSIS_AUDIO", etc.
    patient_id: str,
    correlation_id: str,
    user_id: Optional[str],  # Quando implementar auth
    success: bool,
    metadata: Dict
):
    """Log estruturado para auditoria LGPD"""

    logger.info(
        "audit_event",
        event_type=event_type,
        patient_id=patient_id,  # Hash anonimizado
        correlation_id=correlation_id,
        user_id=user_id,
        timestamp=datetime.utcnow().isoformat(),
        success=success,
        metadata=metadata,  # Sem dados sensíveis
        retention_days=365  # LGPD: mínimo
    )

# Uso em endpoints
@app.post("/analyze/text")
async def analyze_text(request: Request, data: TextRequest):
    try:
        result = await service.analyze(data.texto)
        await log_audit_event(
            event_type="ANALYSIS_TEXT",
            patient_id=data.patient_id,
            correlation_id=get_correlation_id(request),
            user_id=get_current_user(request),
            success=True,
            metadata={"risk_level": result.risco_violencia}
        )
        return result
    except Exception as e:
        await log_audit_event(..., success=False, metadata={"error": str(e)})
        raise
```

---

### V-MED-004: Dependências com Vulnerabilidades Conhecidas
**Categoria**: A06:2021 - Vulnerable and Outdated Components
**Severidade**: 🟡 **MÉDIA (CVSS 5.3)**

#### Descrição
Dependências listadas no PRD podem ter vulnerabilidades quando não especificadas com versões mínimas seguras:
- OpenCV 4.8.0+ (CVEs históricos conhecidos)
- FFmpeg (processamento de mídia é alvo de exploração)
- Azure SDKs (precisam de atualização regular)

#### Recomendação
```bash
# Adicionar ao CI/CD
pip install safety
safety check -r requirements.txt

# E/ou
pip install pip-audit
pip-audit -r requirements.txt
```

```toml
# pyproject.toml - pin versões seguras
[tool.poetry.dependencies]
opencv-python = "^4.8.1.78"  # Versão específica
ffmpeg-python = "^0.2.0"
azure-ai-textanalytics = "^5.4.0"
# etc.

[tool.poetry.dev-dependencies]
safety = "^3.0.0"
pip-audit = "^2.6.0"
```

---

### V-MED-005: Falta de HSTS (HTTP Strict Transport Security)
**Categoria**: A02:2021 - Cryptographic Failures
**Severidade**: 🟡 **MÉDIA (CVSS 5.4)**

#### Descrição
Nenhuma menção a forçar HTTPS via HSTS header.

#### Recomendação
```python
# Em produção (Azure App Service já tem HTTPS)
@app.middleware("http")
async def hsts_header(request: Request, call_next):
    response = await call_next(request)
    response.headers["Strict-Transport-Security"] = (
        "max-age=31536000; includeSubDomains; preload"
    )
    return response
```

---

### V-MED-006: Exposição de Detalhes de Erro
**Categoria**: A04:2021 - Insecure Design
**Severidade**: 🟡 **MÉDIA (CVSS 5.3)**

#### Descrição
Em desenvolvimento, o FastAPI expõe stack traces completos. Isso pode vazar:
- Estrutura de diretórios
- Versões de bibliotecas
- Trechos de código

#### Recomendação
```python
# src/core/exceptions.py
from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse

class BaseAppException(Exception):
    """Exceção base da aplicação"""
    pass

async def global_exception_handler(request: Request, exc: Exception):
    """Handler global de exceções"""

    # Log completo (interno)
    logger.error("Unhandled exception", exc_info=exc, path=request.url.path)

    # Resposta para cliente (genérica em produção)
    if os.getenv("ENVIRONMENT") == "production":
        return JSONResponse(
            status_code=500,
            content={
                "error": "INTERNAL_ERROR",
                "message": "Erro interno do servidor",
                "correlation_id": get_correlation_id(request)
            }
        )
    else:
        # Em desenvolvimento, pode retornar mais detalhes
        raise exc

app = FastAPI()
app.add_exception_handler(Exception, global_exception_handler)
```

---

### V-MED-007: Requisição de Recursos Externos sem Validação (SSRF)
**Categoria**: A10:2021 - Server-Side Request Forgery (SSRF)
**Severidade**: 🟡 **MÉDIA (CVSS 6.5)**

#### Descrição
Se o sistema aceitar URLs para download (em vez de upload), pode haver SSRF. Não está documentado, mas é um risco se implementado no futuro.

#### Recomendação
```python
from urllib.parse import urlparse
import ipaddress

BLOCKED_HOSTS = [
    "localhost",
    "127.0.0.1",
    "169.254.169.254",  # AWS/Azure metadata
    "10.0.0.0/8",       # RFC1918
    "172.16.0.0/12",
    "192.168.0.0/16"
]

def validate_external_url(url: str) -> bool:
    parsed = urlparse(url)
    hostname = parsed.hostname

    if not hostname:
        return False

    # Verificar IPs privados
    try:
        ip = ipaddress.ip_address(hostname)
        if ip.is_private or ip.is_loopback or ip.is_reserved:
            return False
    except ValueError:
        pass  # Não é IP, continuar

    # Verificar hosts bloqueados
    if hostname in BLOCKED_HOSTS:
        return False

    # Só permitir HTTPS
    if parsed.scheme != "https":
        return False

    return True
```

---

### V-MED-008: Ausência de Sub-resource Integrity (SRI)
**Categoria**: A08:2021 - Software and Data Integrity Failures
**Severidade**: 🟡 **MÉDIA (CVSS 5.4)**

#### Descrição
Se o Swagger UI (`/docs`) carregar recursos externos (CSS/JS do CDN), não há SRI para verificar integridade.

#### Recomendação
```python
# FastAPI já serve recursos locais por padrão
# Verificar configuração:
from fastapi.openapi.docs import get_swagger_ui_html

app = FastAPI(
    docs_url="/docs",
    redoc_url="/redoc",
    # Garantir que serve recursos locais
)

# Ou desabilitar em produção se não necessário
app = FastAPI(docs_url=None, redoc_url=None)  # Produção
```

---

## 🟢 VULNERABILIDADES BAIXAS (CVSS 1.0-3.9)

### V-LOW-001: Informação de Versão Exposta
**Categoria**: A05:2021 - Security Misconfiguration
**Severidade**: 🟢 **BAIXA (CVSS 2.3)**

#### Descrição
O health check expõe `version: "1.0.0"` que facilita fingerprinting.

#### Recomendação
```python
# Em produção, não expor versão exata
@app.get("/health")
async def health():
    return {
        "status": "healthy",
        "version": "v1",  # Apenas major version
        # ...
    }
```

---

### V-LOW-002: Sem Sub-resource Integrity no Swagger
**Categoria**: A08:2021 - Data Integrity
**Severidade**: 🟢 **BAIXA (CVSS 2.0)**

#### Descrição
Swagger UI carrega JS/CSS de CDNs sem hash de integridade.

#### Recomendação
FastAPI serve recursos locais por padrão quando instalado com `fastapi[all]`. Verificar configuração.

---

### V-LOW-003: Headers de Cache Inseguros
**Categoria**: A05:2021 - Security Misconfiguration
**Severidade**: 🟢 **BAIXA (CVSS 2.7)**

#### Descrição
Nenhuma configuração de cache headers para dados sensíveis.

#### Recomendação
```python
@app.post("/analyze/text")
async def analyze_text(...):
    response = await call_service(...)
    response.headers["Cache-Control"] = "no-store, no-cache, must-revalidate, private"
    response.headers["Pragma"] = "no-cache"
    response.headers["Expires"] = "0"
    return response
```

---

### V-LOW-004: Uso de UUID v4 Previsível
**Categoria**: A02:2021 - Cryptographic Failures
**Severidade**: 🟢 **BAIXA (CVSS 3.1)**

#### Descrição
Se `patient_id` usar UUID v4 padrão, pode ser previsível.

#### Recomendação
```python
import secrets
from uuid import uuid4

def generate_secure_patient_id() -> str:
    """Gerar ID de paciente criptograficamente seguro"""
    # Combinação de UUID + random seguro
    return f"{uuid4().hex}-{secrets.token_hex(8)}"
```

---

## 📋 Matriz de Prioridade de Remediação

| ID | Vulnerabilidade | Prioridade | Esforço | Status |
|----|----------------|------------|---------|--------|
| **V-CRIT-001** | Sem Autenticação | 🔴 P0 | 4h | ✅ Documentado (MVP) |
| **V-CRIT-002** | Upload sem Verificação | 🔴 P0 | 6h | 🟠 Não implementado |
| **V-HIGH-001** | Secrets sem Proteção | 🟠 P1 | 8h | 🟠 Parcial |
| **V-HIGH-002** | Sem Rate Limiting | 🟠 P1 | 4h | 🟠 Não implementado |
| **V-HIGH-003** | SSL não Configurado | 🟠 P1 | 2h | 🟠 Não documentado |
| **V-HIGH-004** | CORS Aberto | 🟠 P1 | 2h | 🟠 Não documentado |
| **V-HIGH-005** | XSS | 🟠 P1 | 4h | 🟠 Não implementado |
| **V-HIGH-006** | Timeout Azure | 🟠 P1 | 3h | 🟠 Não implementado |
| **V-HIGH-007** | Health Expondo Dados | 🟠 P1 | 2h | 🟠 Documentado |
| **V-MED-001** | Input Sanitization | 🟡 P2 | 4h | 🟠 Não implementado |
| **V-MED-002** | CSP Headers | 🟡 P2 | 2h | 🟠 Não implementado |
| **V-MED-003** | Audit Logging | 🟡 P2 | 6h | 🟠 Não implementado |
| **V-MED-004** | Dependências | 🟡 P2 | 2h | 🟠 CI/CD |
| **V-MED-005** | HSTS | 🟡 P2 | 1h | 🟠 Não documentado |
| **V-MED-006** | Error Exposure | 🟡 P2 | 2h | 🟠 Não implementado |
| **V-LOW-001** | Version Exposure | 🟢 P3 | 0.5h | 🟠 Não implementado |

---

## 🔒 Checklist de Implementação Segura

### Task 001: Bootstrap (Adicionar)
- [ ] `safety` e `pip-audit` no CI/CD
- [ ] `.safety-project` configurado
- [ ] `bandit` (SAST Python) no CI/CD

### Task 002: Health Endpoint (Adicionar)
- [ ] Autenticação mínima (API Key)
- [ ] Rate limiting por IP
- [ ] Response sanitizado (sem quotas)

### Task 003-005: Services (Adicionar)
- [ ] Sanitização de input em todos endpoints
- [ ] Timeout em chamadas Azure
- [ ] Exception handlers genéricos
- [ ] Audit logging estruturado

### Task 007: Rate Limiting (Expandir)
- [ ] Rate limit por IP (DoS protection)
- [ ] Rate limit por usuário (autenticado)
- [ ] Circuit breaker para Azure

### Task 009: Deploy Azure (Adicionar)
- [ ] Azure Key Vault configurado
- [ ] HTTPS forçado (HSTS)
- [ ] Security headers (CSP, etc.)
- [ ] CORS restrito

---

## 📚 Referências

### OWASP Top 10 2021
- [A01: Broken Access Control](https://owasp.org/Top10/A01_2021-Broken_Access_Control/)
- [A02: Cryptographic Failures](https://owasp.org/Top10/A02_2021-Cryptographic_Failures/)
- [A03: Injection](https://owasp.org/Top10/A03_2021-Injection/)
- [A04: Insecure Design](https://owasp.org/Top10/A04_2021-Insecure_Design/)
- [A05: Security Misconfiguration](https://owasp.org/Top10/A05_2021-Security_Misconfiguration/)

### LGPD
- Art. 46: Segurança do processo
- Art. 50: Relatório de impacto

### FastAPI Security
- [FastAPI Security](https://fastapi.tiangolo.com/tutorial/security/)
- [OWASP FastAPI](https://github.com/OWASP/CheatSheetSeries/blob/master/cheatsheets/FastAPI_Security_Cheat_Sheet.md)

---

## ✅ Recomendações Finais

### Para Deploy em Produção (Obrigatório)

1. **NUNCA** deployar sem autenticação mínima (API Key)
2. **NUNCA** expor `/health` com detalhes sem autenticação
3. **SEMPRE** validar magic numbers de arquivos uploadados
4. **SEMPRE** usar Azure Key Vault para secrets em produção
5. **SEMPRE** implementar rate limiting por IP

### Mitigações Imediatas

```python
# Mínimo viável de segurança (adicionar a Task 001/002)
from fastapi import FastAPI, Request, HTTPException
from fastapi.middleware.trustedhost import TrustedHostMiddleware

app = FastAPI()

# 1. Trusted Hosts (protege contra Host header attacks)
app.add_middleware(
    TrustedHostMiddleware,
    allowed_hosts=["api.exemplo.com", "*.azurewebsites.net"]
)

# 2. API Key mínima (até implementar JWT)
API_KEY = os.getenv("API_KEY")  # Gerar com: openssl rand -hex 32
@app.middleware("http")
async def api_key_check(request: Request, call_next):
    if request.url.path not in ["/health"]:
        key = request.headers.get("X-API-Key")
        if key != API_KEY:
            raise HTTPException(401, "Invalid API Key")
    return await call_next(request)

# 3. Security Headers
@app.middleware("http")
async def security_headers(request: Request, call_next):
    response = await call_next(request)
    response.headers["X-Content-Type-Options"] = "nosniff"
    response.headers["X-Frame-Options"] = "DENY"
    response.headers["X-XSS-Protection"] = "1; mode=block"
    return response
```

---

**Próximo Passo**: Criar Task específica para implementação de segurança (ou adicionar aos critérios de aceite das Tasks existentes).

---

*Documento criado para análise de segurança. NÃO incluir em repositório público sem revisão.*
