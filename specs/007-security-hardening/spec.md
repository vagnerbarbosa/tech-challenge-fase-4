# Feature Specification: Security Hardening

**Feature Branch**: `[007-security-hardening]`
**Created**: 2026-04-11
**Status**: Draft
**Input**: User description: "Corrigir vulnerabilidades de segurança identificadas no security-audit.md"

---

## User Scenarios & Testing

### User Story 1 - Validação de Uploads (Priority: P1)

Como sistema, quero validar rigorosamente arquivos enviados para prevenir injeção de malware.

**Why this priority**: Uploads de arquivos são vetor de ataque comum (malware, path traversal).

**Independent Test**: Tentativa de upload de arquivo não permitido é bloqueada.

**Acceptance Scenarios**:

1. **Given** arquivo com extensão válida mas conteúdo malicioso, **When** submetido, **Then** bloqueado após validação de conteúdo
2. **Given** arquivo com path traversal no nome, **When** submetido, **Then** nome sanitizado ou rejeitado
3. **Given** arquivo executável (.exe, .sh), **When** submetido, **Then** rejeitado imediatamente
4. **Given** arquivo muito grande, **When** submetido, **Then** rejeitado antes de upload completo

### User Story 2 - Proteção de Secrets (Priority: P1)

Como sistema, quero garantir que secrets nunca sejam expostos em logs ou erros.

**Why this priority**: Exposição de credenciais é vulnerabilidade crítica.

**Independent Test**: Logs não contêm Azure keys mesmo em caso de erro.

**Acceptance Scenarios**:

1. **Given** erro de conexão Azure, **When** logado, **Then** não contém a key nos logs
2. **Given** stack trace de exceção, **When** exibido, **Then** secrets são mascarados
3. **Given** variáveis de ambiente, **When** dump acidental, **Then** secrets não aparecem

### User Story 3 - Sanitização de Dados (Priority: P1)

Como sistema LGPD-compliant, quero sanitizar todos os dados de entrada e saída.

**Why this priority**: LGPD exige proteção de dados pessoais.

**Independent Test**: Dados sensíveis não aparecem em responses ou logs.

**Acceptance Scenarios**:

1. **Given** texto com dados pessoais, **When** processado, **Then** dados são anonimizados
2. **Given** nome real do paciente, **When** armazenado, **Then** convertido para patient_id hash
3. **Given** logs de requisição, **When** verificados, **Then** não contêm conteúdo sensível

### User Story 4 - Headers de Segurança (Priority: P2)

Como sistema, quero incluir headers de segurança em todas as respostas HTTP.

**Why this priority**: Proteção contra XSS, clickjacking, sniffing.

**Independent Test**: Verificar headers de segurança nas respostas.

**Acceptance Scenarios**:

1. **Given** qualquer resposta, **When** recebida, **Then** inclui X-Content-Type-Options: nosniff
2. **Given** qualquer resposta, **When** recebida, **Then** inclui X-Frame-Options: DENY
3. **Given** qualquer resposta, **When** recebida, **Then** inclui Content-Security-Policy

---

## Requirements

### Functional Requirements

- **FR-001**: Validação de tipo MIME além da extensão
- **FR-002**: Sanitização de filenames (path traversal)
- **FR-003**: Limite de tamanho de arquivo no nginx/FastAPI
- **FR-004**: Mascaramento de secrets em logs
- **FR-005**: Anonimização de dados pessoais
- **FR-006**: Headers de segurança HTTP (CSP, HSTS, etc.)
- **FR-007**: Rate limiting por IP (proteção DDoS)
- **FR-008**: CORS configurado restritivamente

### Key Entities

- **SecurityMiddleware**: Middleware de segurança FastAPI
- **FileValidator**: Validação de uploads
- **LogSanitizer**: Sanitização de logs
- **DataAnonymizer**: Anonimização de dados

---

## Success Criteria

- **SC-001**: Nenhuma vulnerabilidade crítica/alta no security scan
- **SC-002**: Secrets nunca expostos em logs/erros
- **SC-003**: Uploads validados por tipo MIME e conteúdo
- **SC-004**: Headers de segurança presentes em todas respostas

---

## Assumptions

- Security audit já realizado (docs/technical/security-audit.md)
- Python-magic disponível para validação MIME
- Hashlib para anonimização
- python-dotenv para gerenciamento de secrets

---

## Technical Notes

### Headers de Segurança
```python
headers = {
    "X-Content-Type-Options": "nosniff",
    "X-Frame-Options": "DENY",
    "X-XSS-Protection": "1; mode=block",
    "Strict-Transport-Security": "max-age=31536000; includeSubDomains",
    "Content-Security-Policy": "default-src 'self'",
    "Referrer-Policy": "strict-origin-when-cross-origin"
}
```

### Validação de Uploads
- Biblioteca: `python-magic` para validação MIME real
- Verificar magic bytes dos arquivos
- Bloquear: executable, script, html
- Permitir: audio (wav, mp3, ogg), image (jpg, png)

### Sanitização
- Usar hashlib.sha256 para patient_id
- Mascarar Azure keys em logs: key[:4] + "****" + key[-4:]
- Nunca logar texto transcrito ou descrição de imagem

---

## Vulnerabilidades Identificadas

### 🔴 CRÍTICAS (CVSS 9.0-10.0)

| ID | Vulnerabilidade | Impacto | Mitigação |
|----|----------------|---------|-----------|
| V-CRIT-001 | Sem Autenticação | Acesso não autorizado | Implementar API Key mínima |
| V-CRIT-002 | Upload sem Verificação | RCE, Path Traversal | Validar magic numbers MIME |

### 🟠 ALTAS (CVSS 7.0-8.9)

| ID | Vulnerabilidade | Impacto | Mitigação |
|----|----------------|---------|-----------|
| V-HIGH-001 | Secrets sem Proteção | Vazamento credenciais | Azure Key Vault |
| V-HIGH-002 | Sem Rate Limiting App | DoS | slowapi + limiter |
| V-HIGH-003 | SSL não Configurado | MITM | TLS 1.2+ |
| V-HIGH-004 | CORS Aberto | CSRF | Origens restritas |
| V-HIGH-005 | XSS | Execução código | Escapar HTML output |
| V-HIGH-006 | Timeout Azure | DoS | Timeout 30s |
| V-HIGH-007 | Health Expondo Dados | Info leak | Response sanitizado |

### 🟡 MÉDIAS (CVSS 4.0-6.9)

| ID | Vulnerabilidade | Mitigação |
|----|----------------|-----------|
| V-MED-001 | Input Sanitization | Normalizar Unicode, remover zero-width chars |
| V-MED-002 | CSP Headers | Content-Security-Policy |
| V-MED-003 | Audit Logging | structlog com eventos LGPD |
| V-MED-004 | Dependências | safety + pip-audit no CI/CD |
| V-MED-005 | HSTS | Strict-Transport-Security header |
| V-MED-006 | Error Exposure | Exception handlers genéricos em produção |

### 🟢 BAIXAS (CVSS 1.0-3.9)

| ID | Vulnerabilidade | Mitigação |
|----|----------------|-----------|
| V-LOW-001 | Version Exposure | Mostrar apenas major version |
| V-LOW-002 | Swagger SRI | FastAPI serve recursos locais |
| V-LOW-003 | Cache Headers | no-store, no-cache |
| V-LOW-004 | UUID Previsível | secrets.token_hex combinado |

---

## Checklist de Implementação Segura

### Task 001: Bootstrap (Adicionar)
- [ ] `safety` e `pip-audit` no CI/CD
- [ ] `bandit` (SAST Python) no CI/CD

### Task 002: Health Endpoint (Adicionar)
- [ ] Autenticação mínima (API Key)
- [ ] Rate limiting por IP
- [ ] Response sanitizado (sem quotas detalhadas públicas)

### Task 003-005: Services (Adicionar)
- [ ] Sanitização de input em todos endpoints
- [ ] Timeout em chamadas Azure (30s)
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

## Código Mínimo de Segurança

```python
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
    response.headers["Strict-Transport-Security"] = "max-age=31536000; includeSubDomains"
    return response
```

---

## Referências

- Documentação completa: `docs/technical/security-audit.md`
- [OWASP Top 10 2021](https://owasp.org/Top10/)
- [FastAPI Security](https://fastapi.tiangolo.com/tutorial/security/)
- [OWASP FastAPI Cheat Sheet](https://github.com/OWASP/CheatSheetSeries/blob/master/cheatsheets/FastAPI_Security_Cheat_Sheet.md)
