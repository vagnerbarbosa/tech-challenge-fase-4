# Implementation Plan: Security Hardening 2026

**Branch**: `007-security-hardening` | **Date**: 2026-04-22 | **Spec**: [spec.md](spec.md)  
**Input**: Implementar hardening de segurança completo seguindo OWASP API Top 10 2023/2026 e LGPD compliance

---

## Summary

Implementação de camadas de segurança para API multimodal de saúde, cobrindo: autenticação API Key, rate limiting, headers de segurança HTTP, validação de uploads, sanitização de logs, proteção BOLA, e auditoria LGPD. Abordagem modular permite ativação gradual sem impactar funcionalidades existentes.

---

## Technical Context

**Language/Version**: Python 3.11+  
**Primary Dependencies**: FastAPI 0.135+, Pydantic v2, python-magic, slowapi  
**Storage**: In-memory (local) / Redis (opcional para rate limiting distribuído)  
**Testing**: pytest, pytest-asyncio, httpx  
**Target Platform**: Linux server / Docker containers  
**Project Type**: Web service (REST API)  
**Performance Goals**: Overhead de segurança < 10ms por requisição  
**Constraints**: Compatibilidade com Azure Free Tier, LGPD compliance, sem breaking changes em endpoints existentes  
**Scale/Scope**: Até 1000 req/min com rate limiting, suporte a múltiplos clientes simultâneos

---

## Constitution Check

*GATE: Must pass before Phase 0 research. Re-check after Phase 1 design.*

| Princípio | Status | Observações |
|-----------|--------|-------------|
| **I. LGPD Compliance** | ✅ PASS | Spec requer hash de patient_id, anonimização de logs, não logar mídia |
| **II. Azure Free Tier** | ✅ PASS | Rate limiting já existe; novas proteções não afetam quotas Azure |
| **III. Test Coverage >70%** | ✅ PASS | Plan inclui testes unitários para cada middleware e validador |
| **IV. Container-First** | ✅ PASS | Middlewares são código puro, sem dependências externas novas |
| **V. Documentação PT** | ✅ PASS | Spec e plan em português; código em inglês |
| **VI. Security-First** | ✅ PASS | Feature é exclusivamente sobre segurança |
| **VII. Multimodal Architecture** | ✅ PASS | Segurança aplicada em camada, não afeta lógica das modalidades |

**Veredicto**: ✅ **APROVADO** - Nenhuma violação detectada.

---

## Project Structure

### Documentation (this feature)

```text
specs/007-security-hardening/
├── plan.md              # Este arquivo
├── research.md          # Pesquisa de ferramentas e padrões
├── data-model.md        # Schemas de segurança (APIKey, RateLimit, etc.)
├── quickstart.md        # Guia rápido de configuração de segurança
├── contracts/           # Contratos de API (endpoints de auth)
└── tasks.md             # Checklist de implementação (próximo passo)
```

### Source Code (repository root)

```text
src/
├── api/
│   ├── main.py                 # Registro de middlewares de segurança
│   ├── dependencies.py         # Depends() para auth e rate limiting
│   └── routes/
│       └── health.py           # Atualizar: remover exposição de quotas sem auth
├── core/
│   ├── config.py               # Adicionar: SECURITY_*, CORS_*, RATE_LIMIT_*
│   ├── exceptions.py           # Adicionar: SecurityException, RateLimitExceeded
│   └── security/               # NOVO: Módulo de segurança
│       ├── __init__.py
│       ├── middleware.py       # SecurityHeadersMiddleware, CORSValidation
│       ├── auth.py             # APIKeyValidator, RBAC
│       ├── rate_limiter.py     # TokenBucketRateLimiter
│       ├── file_validator.py   # MagicBytesValidator, FilenameSanitizer
│       └── log_sanitizer.py    # SecretMasker, PatientIdHasher
├── services/
│   └── ...                     # Atualizar: usar LogSanitizer em logs
└── utils/
    └── audit_logger.py         # NOVO: AuditLogger LGPD-compliant

tests/
├── unit/
│   ├── core/
│   │   ├── test_security_middleware.py
│   │   ├── test_auth.py
│   │   ├── test_rate_limiter.py
│   │   ├── test_file_validator.py
│   │   └── test_log_sanitizer.py
│   └── services/
│       └── test_audit_logger.py
├── integration/
│   └── test_security_endpoints.py
└── security/                   # NOVO: Testes específicos de segurança
    ├── test_cors.py
    ├── test_headers.py
    ├── test_bola.py
    └── test_secrets_in_logs.py
```

**Structure Decision**: Reutilizar estrutura existente, adicionando módulo `core/security/` para manter isolamento e testabilidade.

---

## Phase 0: Research

### Decisões Técnicas

| Aspecto | Decisão | Racional |
|---------|---------|----------|
| **Rate Limiting** | slowapi + Redis (opcional) | FastAPI-native, suporte a Redis para distribuído, token bucket padrão |
| **API Key Auth** | Header `X-API-Key` | Simples, efetivo para MVP, evoluível para JWT/OAuth2 |
| **File Validation** | python-magic | Validação real de magic bytes, não só extensão |
| **Headers Security** | Middleware customizado | Controle total sobre headers, sem adicionar deps pesadas |
| **BOLA Protection** | Depends() em cada endpoint | Verificação de ownership no service layer |
| **Log Sanitization** | structlog processor | Filtro automático de secrets em todos os logs |

### Dependências Adicionais

```toml
[tool.poetry.dependencies]
python-magic = "^0.4.27"
slowapi = { version = "^0.1.9", optional = true }
redis = { version = "^5.0.0", optional = true }

[tool.poetry.extras]
security = ["slowapi", "redis"]
```

---

## Phase 1: Design

### Data Model

**SecurityConfig** (Pydantic Settings):
```python
class SecurityConfig(BaseSettings):
    api_key: str = Field(..., description="API Key para autenticação")
    api_key_header: str = "X-API-Key"
    
    # Rate Limiting
    rate_limit_per_minute: int = 60
    rate_limit_auth_per_minute: int = 5
    redis_url: Optional[str] = None
    
    # CORS
    cors_origins: List[str] = ["http://localhost:3000"]
    cors_allow_credentials: bool = True
    
    # Security Headers
    security_headers_enabled: bool = True
    hsts_max_age: int = 31536000
    
    # Environment
    environment: Literal["development", "staging", "production"] = "development"
```

**RateLimitInfo**:
```python
class RateLimitInfo(BaseModel):
    limit: int
    remaining: int
    reset_after: int  # seconds
    retry_after: Optional[int] = None
```

**AuditLogEntry**:
```python
class AuditLogEntry(BaseModel):
    timestamp: datetime
    event_type: Literal["access", "auth_failure", "rate_limit_exceeded", "suspicious_activity"]
    ip_address: str
    user_agent: Optional[str]
    api_key_hash: Optional[str]  # SHA256 da key, não a key
    endpoint: str
    result: Literal["success", "failure", "blocked"]
    details: Dict[str, Any]  # Sanitized, sem dados sensíveis
```

### Contracts

**POST /health** (com autenticação opcional):
- Request: Header `X-API-Key: <key>` (opcional em dev, obrigatório em prod)
- Response: Informações de saúde + rate limit status se autenticado

**Headers em todas as respostas**:
- `X-Content-Type-Options: nosniff`
- `X-Frame-Options: DENY`
- `Strict-Transport-Security: max-age=31536000; includeSubDomains`
- `Content-Security-Policy: default-src 'self'`
- `X-RateLimit-Limit`, `X-RateLimit-Remaining`, `X-RateLimit-Reset`

### Quickstart

```python
# Configuração mínima (.env)
API_KEY="sua-key-segura-aqui"
ENVIRONMENT="production"
CORS_ORIGINS="https://app-segura.com,https://app2.com"

# Ativação de rate limiting com Redis (opcional)
REDIS_URL="redis://localhost:6379/0"
```

---

## Implementation Phases

### Fase 1: Infraestrutura de Segurança
1. Criar `src/core/security/` com módulos base
2. Implementar `SecurityConfig` em `src/core/config.py`
3. Criar middleware `SecurityHeadersMiddleware`
4. Implementar `LogSanitizer` como processor structlog

### Fase 2: Autenticação
1. Implementar `APIKeyValidator` em `src/core/security/auth.py`
2. Criar dependency `require_api_key()`
3. Adicionar exceções customizadas (`UnauthorizedException`, `ForbiddenException`)
4. Aplicar auth em endpoints protegidos (exceto health em dev)

### Fase 3: Rate Limiting
1. Implementar `TokenBucketRateLimiter`
2. Criar middleware/dependency de rate limiting
3. Diferenciar limites por tipo de endpoint
4. Retornar headers X-RateLimit-*

### Fase 4: Validação de Uploads
1. Implementar `MagicBytesValidator` (validação real de tipo)
2. Criar `FilenameSanitizer` (remover path traversal)
3. Integrar em endpoints `/analyze/audio` e `/analyze/video`
4. Rejeitar arquivos executáveis por magic bytes

### Fase 5: Auditoria LGPD
1. Implementar `AuditLogger` em `src/utils/audit_logger.py`
2. Logar eventos de segurança (acesso, falha, bloqueio)
3. Garantir imutabilidade (append-only)
4. Exportação para formato ANPD

### Fase 6: Integração e Testes
1. Atualizar `src/api/main.py` para registrar todos os middlewares
2. Escrever testes unitários (cobertura > 70%)
3. Escrever testes de integração (end-to-end)
4. Testes de segurança específicos (CORS, headers, BOLA)

### Fase 7: Documentação e Validação
1. Atualizar `README.md` com seção de segurança
2. Documentar setup de API Key
3. Rodar `ruff check .` e `mypy src/`
4. Executar auditoria `@speckit.clarify`

---

## Complexity Tracking

| Aspecto | Justificativa |
|---------|--------------|
| **7 User Stories** | Cada uma cobre um domínio de segurança distinto; podem ser implementadas em paralelo |
| **35 Requisitos Funcionais** | Número alto reflete abrangência OWASP + LGPD; cada FR é simples individualmente |
| **Middleware Customizado** | FastAPI não tem security headers built-in; solução leve é preferida a bibliotecas pesadas |
| **Redis Opcional** | Fallback para memória local permite desenvolvimento sem infra extra; produção usa Redis |

---

## Success Criteria Mapping

| SC | Como Alcançar |
|----|----------------|
| SC-001 (Zero vulns críticas) | Bandit + Safety no CI/CD; testes de segurança |
| SC-002 (Cobertura auth 100%) | Testes unitários para todas as combinações de auth |
| SC-003 (Rate limit funciona) | Testes de integração com mock de tempo |
| SC-004 (Headers 100%) | Teste em todos os endpoints via pytest |
| SC-005 (Secrets nunca expostos) | Grep em logs de teste; verificação manual |
| SC-006 (BOLA protegido) | Teste de acesso a recurso de outro usuário |
| SC-007 (Overhead < 10ms) | Benchmark middleware com pytest-benchmark |
| SC-008 (Logs exportáveis) | Teste de exportação para JSON estruturado |

---

## Next Steps

1. **Taskify**: Criar `tasks.md` com checklist detalhado (`/speckit.tasks`)
2. **Implement**: Executar tasks em ordem
3. **Validate**: Testes, lint, type check
4. **Audit**: Executar `@speckit.clarify`
