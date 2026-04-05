# Task 008: Security Hardening - Correções de Segurança

## Objetivo

Implementar correções para todas as vulnerabilidades identificadas em `docs/technical/security-audit.md` antes do deploy em produção no Azure.

> **⚠️ CRÍTICO**: Esta task deve ser completada ANTES do Task 010 (Deploy Azure). Não faça deploy sem corrigir as vulnerabilidades CRÍTICAS e HIGH.

## Contexto

O [security-audit.md](../docs/technical/security-audit.md) identificou **21 vulnerabilidades**:
- **2 CRÍTICAS** (CVSS 9.1-9.3) - Devem ser corrigidas imediatamente
- **7 HIGH** (CVSS 7.0-8.5) - Devem ser corrigidas antes do deploy
- **8 MEDIUM** - Recomendadas para pós-MVP
- **4 LOW** - Recomendadas para pós-MVP

## Critérios de Aceite

### CA1: Autenticação da API (V-CRIT-001)
- [ ] Implementar API Key authentication via header `X-API-Key`
- [ ] Criar middleware em `src/core/security.py`
- [ ] Proteger todos endpoints `/analyze/*` e `/admin/*`
- [ ] Endpoint `/health` pode permanecer público (com limitação de informações)
- [ ] Retornar 401 para requisições sem autenticação válida
- [ ] API Key configurável via `API_KEY` no `.env`

```python
# Exemplo de uso
from fastapi import Depends
from src.core.security import get_current_api_key

@app.post("/analyze/text")
async def analyze_text(data: TextRequest, api_key: str = Depends(get_current_api_key)):
    ...
```

### CA2: Validação de Uploads (V-CRIT-002)
- [ ] Implementar validação de magic numbers em `src/utils/file_validator.py`
- [ ] Verificar assinatura real do arquivo vs extensão informada
- [ ] Bloquear arquivos executáveis/scripts disfarçados (PDF, JS, EXE, etc.)
- [ ] Lista de magic numbers permitidos:
  - Imagens: `FF D8 FF` (JPEG), `89 50 4E 47` (PNG)
  - Áudio: `52 49 46 46` (WAV), `FF FB`/`FF F3` (MP3)
  - Vídeo: `00 00 00 18 66 74 79 70 6D 70 34 32` (MP4)
- [ ] Retornar 400 com mensagem "Tipo de arquivo inválido ou corrompido"

### CA3: Rate Limiting (V-HIGH-002)
- [ ] Implementar SlowAPI com limites estritos
- [ ] Limites por IP:
  - Análise (todos endpoints `/analyze/*`): 10 req/minuto
  - Health check: 100 req/minuto
  - Uploads: 5 req/minuto
- [ ] Headers `X-RateLimit-*` presentes em todas respostas
- [ ] Configurar Redis opcional para rate limiting distribuído

### CA4: Headers de Segurança (V-HIGH-005)
- [ ] Implementar middleware com headers de segurança:
  - `Content-Security-Policy`: `default-src 'self'`
  - `X-Content-Type-Options`: `nosniff`
  - `X-Frame-Options`: `DENY`
  - `X-XSS-Protection`: `1; mode=block`
  - `Referrer-Policy`: `strict-origin-when-cross-origin`
  - `Permissions-Policy`: `camera=(), microphone=(), geolocation=()`
- [ ] HSTS em produção: `Strict-Transport-Security: max-age=31536000; includeSubDomains`

### CA5: CORS Restrito (V-HIGH-004)
- [ ] Configurar CORS apenas com origens explícitas na whitelist
- [ ] Em produção: permitir apenas domínios específicos (Azure)
- [ ] Em desenvolvimento: permitir `localhost:3000`, `localhost:8000`
- [ ] Nunca usar `allow_origins=["*"]` em produção

### CA6: Sanitização de Saída
- [ ] Mascarar secrets nos logs (regex para keys Azure)
- [ ] Sanitizar health check (remover detalhes sensíveis)
- [ ] Validar formato das chaves Azure no startup

### CA7: Timeout e Limites
- [ ] Timeout de upload: máximo 300 segundos
- [ ] Tamanho máximo de arquivo: 50MB
- [ ] Timeout de processamento Azure: 60 segundos

### CA8: Testes de Segurança
- [ ] Testes automatizados para cada vulnerabilidade CRITICAL/HIGH
- [ ] Cobertura mínima 70% para módulos `src/core/security.py` e `src/utils/file_validator.py`
- [ ] Testes de penetração básicos (autenticação, upload malicioso)

## Arquivos a Criar/Modificar

### Novos arquivos:
```
src/
├── core/
│   ├── security.py              # Autenticação, API Key
│   └── middleware.py            # Security headers, CORS
├── utils/
│   ├── file_validator.py        # Magic number validation
│   └── validators.py            # Input sanitization
└── api/
    └── dependencies.py          # Depends(get_current_api_key)

tests/unit/security/
├── test_authentication.py       # Testes de API Key
├── test_file_validation.py      # Testes de magic numbers
└── test_middleware.py           # Testes de headers
```

### Arquivos a modificar:
- `src/api/main.py` - Adicionar middlewares de segurança
- `src/api/routes/*.py` - Proteger endpoints com `Depends(get_current_api_key)`
- `src/core/config.py` - Validar secrets, forçar HTTPS em prod
- `src/core/exceptions.py` - Adicionar SecurityException

## Checklist de Vulnerabilidades

### CRITICAL (Corrigir antes de qualquer deploy)
- [ ] V-CRIT-001: Ausência de autenticação na API
- [ ] V-CRIT-002: Upload de arquivos sem verificação de magic numbers

### HIGH (Corrigir antes do deploy produtivo)
- [ ] V-HIGH-001: Secrets expostos em logs
- [ ] V-HIGH-002: Ausência de rate limiting por IP
- [ ] V-HIGH-003: Comunicação sem SSL/TLS obrigatório
- [ ] V-HIGH-004: CORS permissivo demais
- [ ] V-HIGH-005: Ausência de headers de segurança
- [ ] V-HIGH-006: Timeout de processamento não configurado
- [ ] V-HIGH-007: Health check expõe informações sensíveis

### MEDIUM (Pós-MVP se necessário)
- [ ] V-MED-001: Ausência de sanitização de input
- [ ] V-MED-002: Logging sem mascaramento de PII

## Estimativa
**Pontuação**: 5 pontos
**Tempo estimado**: 4-6 horas

## Dependências
- Task 001: Bootstrap (estrutura base)
- Task 002-006: Endpoints funcionais
- Task 007: Rate Limiting (pode ser feito junto)

## Bloqueia
- Task 010: Deploy Azure **(NÃO deployar sem estas correções)**

## Referências
- [security-audit.md](../docs/technical/security-audit.md) - Lista completa de vulnerabilidades
- OWASP Top 10 2021: https://owasp.org/www-project-top-ten/
- Azure Security Best Practices: https://docs.microsoft.com/azure/security/fundamentals/best-practices-and-patterns

## Notas de Implementação

### API Key Pattern
```python
# src/core/security.py
from fastapi import HTTPException, Security, status
from fastapi.security import APIKeyHeader
from src.core.config import settings

api_key_header = APIKeyHeader(name=settings.api_key_header, auto_error=False)

async def get_current_api_key(api_key: str = Security(api_key_header)) -> str:
    if not api_key or api_key != settings.api_key:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="API Key inválida ou ausente",
        )
    return api_key
```

### Magic Number Validation
```python
# src/utils/file_validator.py
MAGIC_NUMBERS = {
    'image/jpeg': b'\xff\xd8\xff',
    'image/png': b'\x89PNG\r\n\x1a\n',
    'audio/wav': b'RIFF',
    'audio/mpeg': [b'\xff\xfb', b'\xff\xf3', b'\xff\xf2'],
}

def validate_file_type(file_bytes: bytes, expected_type: str) -> bool:
    # Implementação em security-audit.md
    pass
```

### Security Headers Middleware
```python
# src/core/middleware.py
from fastapi import Request, Response
from starlette.middleware.base import BaseHTTPMiddleware

class SecurityHeadersMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request: Request, call_next):
        response = await call_next(request)
        response.headers["X-Content-Type-Options"] = "nosniff"
        response.headers["X-Frame-Options"] = "DENY"
        # ... mais headers
        return response
```
