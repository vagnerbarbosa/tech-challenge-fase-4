# Research: Security Hardening 2026

**Feature**: Security Hardening | **Date**: 2026-04-22

---

## Decisions

### D1: Rate Limiting Strategy

**Decision**: Usar `slowapi` (wrapper do limits) com backend Redis (produção) / Memory (dev)

**Rationale**:
- Native FastAPI integration via decorator `@limiter.limit("60/minute")`
- Suporte a múltiplos backends (Redis, Memory, Memcached)
- Headers X-RateLimit-* automáticos
- Token bucket algorithm (indústria standard)

**Alternatives considered**:
- ~~fastapi-limiter~~: Menos flexível, não suporta múltiplos limites por endpoint
- ~~Implementação própria~~: Reinventa roda, mais código para manter
- ~~nginx rate limit~~: Não cobre casos de uso específicos (por API key, por endpoint)

### D2: API Key vs JWT vs OAuth2

**Decision**: API Key simples para MVP, com estrutura para evoluir

**Rationale**:
- MVP requer simplicidade; OAuth2 adiciona complexidade desnecessária
- JWT pode evoluir a partir da mesma estrutura de auth
- API Key é suficiente para uso server-to-server (caso principal)

**Alternatives considered**:
- ~~OAuth2 com scopes~~: Melhor para múltiplos clientes, mas overkill para MVP
- ~~JWT stateless~~: Bem-vindo para escala, mas requer refresh token logic

### D3: File Validation Approach

**Decision**: `python-magic` para validação real + whitelist de MIME types

**Rationale**:
- Validação por extensão é insegura (fácil spoofing)
- Magic bytes é o padrão da indústria (file command no Linux)
- Whitelist (permitir explícito) é mais seguro que blacklist

**Alternatives considered**:
- ~~python-filetype~~: Menos dependencies, mas menos magic signatures
- ~~Pure Python magic~~: Mais código, mais risco de erro

### D4: Security Headers Implementation

**Decision**: Middleware customizado em vez de biblioteca externa

**Rationale**:
- FastAPI não tem built-in security headers
- Starlette (base do FastAPI) tem middleware simples
- Bibliotecas como `secure` adicionam dependências desnecessárias
- Middleware customizado permite configuração granular

**Alternatives considered**:
- ~~fastapi-security~~: Projeto pequeno, pouca manutenção
- ~~secure~~: Adiciona ~100KB, não necessário para headers simples

### D5: BOLA Protection Strategy

**Decision**: Verificação de ownership em service layer, não apenas no middleware

**Rationale**:
- BOLA (Broken Object Level Authorization) é a #1 da OWASP API Top 10
- Middleware não tem contexto de negócio para verificar ownership
- Service layer deve filtrar queries por `user_id` ou `api_key_hash`

**Alternatives considered**:
- ~~Verificação em middleware~~: Sem contexto, impossível implementar corretamente
- ~~Uso de UUID não-sequenciais~~: Dificulta adivinhação, mas não substitui verificação

### D6: Log Sanitization

**Decision**: Structlog processor para máscara automática de secrets

**Rationale**:
- Projeto já usa structlog (consistente)
- Processor é aplicado globalmente (não esquece de sanitizar)
- Regex patterns para máscara de keys Azure, API keys, etc.

**Alternatives considered**:
- ~~Manual sanitização~~: Arriscado (esquecimentos)
- ~~Log proxy~~: Complexidade desnecessária

### D7: Audit Logger Storage

**Decision**: Arquivos JSON Lines (append-only) com rotação diária

**Rationale**:
- LGPD requer retenção mínima de 6 meses
- JSON Lines é parseável, append-only (imutável)
- Rotação diária facilita backup e arquivamento
- Para escala, pode evoluir para PostgreSQL com immutable rows

**Alternatives considered**:
- ~~PostgreSQL audit table~~: Overkill para MVP, mas escala melhor
- ~~Azure Monitor Logs~~: Custo adicional, vendor lock-in

---

## Security Patterns

### Pattern 1: Defense in Depth

Múltiplas camadas de segurança:
1. **Network**: TLS 1.3, HSTS
2. **Transport**: API Key em header seguro
3. **Application**: Rate limiting, input validation
4. **Data**: Sanitização de logs, hashing de IDs

### Pattern 2: Fail Secure

Em caso de erro ou configuração inválida, sistema falha para estado seguro:
- Sem API_KEY configurada: sistema não inicia (fail fast)
- Redis indisponível: fallback para memory (mas loga warning)
- Erro em middleware: não bloqueia requisição, mas loga incidente

### Pattern 3: Least Privilege

Cada componente tem apenas as permissões necessárias:
- API Key de leitura: acesso apenas a GET endpoints
- API Key de escrita: acesso a POST endpoints
- API Key admin: acesso a endpoints administrativos

---

## Technology Stack Confirmation

| Component | Library | Version | Notes |
|-----------|---------|---------|-------|
| Rate Limiting | slowapi | ^0.1.9 | Opcional, extras=["security"] |
| Redis Client | redis | ^5.0.0 | Opcional, para rate limit distribuído |
| File Magic | python-magic | ^0.4.27 | Requer libmagic-dev no container |
| Auth | FastAPI native | - | API Key via Depends() |
| Headers | Starlette Middleware | - | Native, sem deps extras |

---

## References

- [slowapi documentation](https://github.com/laurentS/slowapi)
- [python-magic documentation](https://github.com/ahupp/python-magic)
- [OWASP API Security Top 10](https://owasp.org/www-project-api-security/)
- [OWASP Cheat Sheet Series](https://cheatsheetseries.owasp.org/)
- [FastAPI Security](https://fastapi.tiangolo.com/tutorial/security/)
- [LGPD - Lei 13.709/2018](http://www.planalto.gov.br/ccivil_03/_ato2015-2018/2018/lei/l13709.htm)
