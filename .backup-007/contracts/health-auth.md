# Contract: Health Endpoint with Authentication

**Endpoint**: `GET /health` | **Feature**: Security Hardening 2026

---

## Request

### Headers

| Header | Type | Required | Description |
|--------|------|----------|-------------|
| `X-API-Key` | string | Condicional | API Key para autenticação |

**Nota**: Em ambiente `development`, `/health` pode ser acessado sem API Key. Em `production`, requer autenticação.

### Query Parameters

| Parameter | Type | Required | Description |
|-----------|------|----------|-------------|
| `api_key` | string | Opcional | API Key via query param (desencorajado) |

---

## Responses

### 200 OK (Authenticated)

**Headers**:
```http
Content-Type: application/json
X-Content-Type-Options: nosniff
X-Frame-Options: DENY
Strict-Transport-Security: max-age=31536000; includeSubDomains
Content-Security-Policy: default-src 'self'
X-RateLimit-Limit: 60
X-RateLimit-Remaining: 59
X-RateLimit-Reset: 45
```

**Body**:
```json
{
  "status": "healthy",
  "version": "0.5.0",
  "environment": "production",
  "timestamp": "2026-04-22T10:30:00Z",
  "rate_limit_info": {
    "limit": 60,
    "remaining": 59,
    "reset_after": 45
  },
  "azure_quotas": {
    "text_analytics": {
      "daily_remaining": 150,
      "monthly_remaining": 4850
    },
    "speech": {
      "daily_remaining_minutes": 8,
      "monthly_remaining_minutes": 290
    }
  }
}
```

### 401 Unauthorized (Missing/Invalid Key)

**Headers**:
```http
WWW-Authenticate: Bearer
```

**Body**:
```json
{
  "detail": "Invalid or missing API Key",
  "type": "authentication_error",
  "code": "invalid_api_key"
}
```

### 403 Forbidden (BOLA Violation)

**Body**:
```json
{
  "detail": "Access denied to this resource",
  "type": "authorization_error",
  "code": "bola_violation"
}
```

### 429 Too Many Requests

**Headers**:
```http
Retry-After: 45
X-RateLimit-Limit: 60
X-RateLimit-Remaining: 0
X-RateLimit-Reset: 45
```

**Body**:
```json
{
  "detail": "Rate limit exceeded",
  "type": "rate_limit_error",
  "code": "rate_limit_exceeded",
  "limit": 60,
  "remaining": 0,
  "reset_after": 45,
  "retry_after": 45
}
```

---

## Security Considerations

1. **API Key Exposure**: Nunca logar a API Key em plaintext
2. **Quota Information**: Em produção, considerar ocultar azure_quotas detalhados
3. **Rate Limiting**: Endpoint `/health` tem limites mais permissivos que endpoints de análise
4. **Caching**: Response pode ser cacheado por 30 segundos em clientes
