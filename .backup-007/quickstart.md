# Quickstart: Security Hardening

**Feature**: Security Hardening 2026 | **Setup Time**: 5 minutos

---

## TL;DR

```bash
# 1. Gerar API Key
openssl rand -hex 32

# 2. Configurar .env
echo "SECURITY_API_KEY=sua-key-aqui" >> .env
echo "SECURITY_ENVIRONMENT=production" >> .env

# 3. Instalar dependências de segurança
poetry install --extras security

# 4. Testar
poetry run pytest tests/security/ -v
```

---

## Setup Completo

### 1. Geração de API Key

```bash
# Gere uma API Key segura (256 bits)
export API_KEY=$(openssl rand -hex 32)
echo "Sua API Key: $API_KEY"
```

### 2. Configuração (.env)

```bash
# .env - Configuração mínima de segurança
SECURITY_API_KEY="sua-key-hex-de-64-caracteres-aqui"
SECURITY_ENVIRONMENT="production"
SECURITY_CORS_ORIGINS="https://sua-app.com,https://admin.sua-app.com"

# Rate Limiting (opcional)
SECURITY_RATE_LIMIT_PER_MINUTE=60
SECURITY_RATE_LIMIT_AUTH_PER_MINUTE=5
SECURITY_REDIS_URL="redis://localhost:6379/0"  # Opcional

# File Upload
SECURITY_MAX_UPLOAD_SIZE_MB=50

# Audit Logging
SECURITY_AUDIT_LOG_PATH="logs/audit"
SECURITY_AUDIT_LOG_RETENTION_DAYS=180
```

### 3. Dependências

```bash
# Instalar com suporte a segurança completo
poetry install --extras security

# Ou instalar manualmente
poetry add python-magic
poetry add slowapi --optional
poetry add redis --optional
```

**Nota**: `python-magic` requer `libmagic-dev` no sistema:

```dockerfile
# Dockerfile
RUN apt-get update && apt-get install -y libmagic1
```

### 4. Verificação

```bash
# Health check deve retornar 401 sem API Key
curl http://localhost:8000/health
# Expected: {"detail":"Invalid or missing API Key"}

# Health check com API Key válida
curl -H "X-API-Key: sua-key-aqui" http://localhost:8000/health
# Expected: {"status":"healthy", ...}

# Headers de segurança
curl -I -H "X-API-Key: sua-key-aqui" http://localhost:8000/health
# Expected: X-Content-Type-Options, X-Frame-Options, Strict-Transport-Security
```

---

## Uso da API

### Autenticação

Todas as requisições (exceto `/health` em dev) requerem API Key:

```bash
# Header padrão
curl -H "X-API-Key: sua-key" https://api.seu-app.com/analyze/text

# Ou via query param (menos seguro, desabilitável)
curl https://api.seu-app.com/analyze/text?api_key=sua-key
```

### Rate Limiting

Headers retornados em cada resposta:

```bash
curl -i -H "X-API-Key: sua-key" https://api.seu-app.com/analyze/text

# Headers:
# X-RateLimit-Limit: 60
# X-RateLimit-Remaining: 59
# X-RateLimit-Reset: 45
```

Quando limite excedido (HTTP 429):

```bash
# Response Headers:
# Retry-After: 45
# X-RateLimit-Retry-After: 45

# Response Body:
{
  "detail": "Rate limit exceeded",
  "limit": 60,
  "remaining": 0,
  "reset_after": 45,
  "retry_after": 45
}
```

---

## Testes de Segurança

```bash
# Todos os testes de segurança
poetry run pytest tests/security/ -v

# Testes específicos
poetry run pytest tests/security/test_cors.py -v
poetry run pytest tests/security/test_headers.py -v
poetry run pytest tests/security/test_bola.py -v
poetry run pytest tests/security/test_secrets_in_logs.py -v

# Verificar secrets em logs (não deve encontrar)
grep -r "sua-key-aqui" logs/ || echo "✅ No secrets in logs"
```

---

## Troubleshooting

### Erro: "python-magic: Unable to find magic library"

```bash
# Ubuntu/Debian
sudo apt-get install libmagic1

# Alpine Linux
apk add libmagic

# macOS
brew install libmagic
```

### Erro: "Rate limiting not working without Redis"

```bash
# Rate limiting funciona em memória sem Redis
# Mas para múltiplos containers, Redis é necessário

# Start Redis local
docker run -d -p 6379:6379 redis:alpine

# Ou desative rate limiting distribuído
SECURITY_REDIS_URL=""
```

### CORS bloqueando requisições legítimas

```bash
# Verificar CORS configurado
curl -H "Origin: https://sua-app.com" \
     -H "X-API-Key: sua-key" \
     -I http://localhost:8000/health

# Deve retornar:
# Access-Control-Allow-Origin: https://sua-app.com
```

---

## Checklist de Deploy

- [ ] API Key gerada com `openssl rand -hex 32`
- [ ] `.env` configurado com `SECURITY_ENVIRONMENT=production`
- [ ] CORS origins restritos (nunca `*`)
- [ ] Redis configurado para rate limiting distribuído (multi-container)
- [ ] `libmagic1` instalado no container
- [ ] Audit log path configurado e com permissões de escrita
- [ ] TLS 1.2+ ativado (nginx/Azure Front Door)
- [ ] Testes de segurança passando

---

## Referências

- [Spec](spec.md) - Especificação completa
- [Data Model](data-model.md) - Modelos de dados de segurança
- [OWASP API Security](https://owasp.org/www-project-api-security/) - Top 10
- [LGPD Compliance](https://www.gov.br/anpd/) - ANPD
