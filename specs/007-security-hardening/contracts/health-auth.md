# Contract: Health Endpoint with Authentication

**Endpoint**: `GET /health` | **Feature**: Security Hardening 2026

---

## Request

### Headers

| Header | Type | Required | Description |
|--------|------|----------|-------------|
| `X-API-Key` | string | Condicional | API Key para autenticação |

### Query Parameters

| Parameter | Type | Required | Description |
|-----------|------|----------|-------------|
| `api_key` | string | Opcional | API Key via query param |

---

## Responses

### 200 OK (Authenticated)

**Headers**:
```http
Content-Type: application/json
X-Content-Type-Options: nosniff
X-Frame-Options: DENY
X-RateLimit-Limit: 60
X-RateLimit-Remaining: 59
```

**Body**:
```json
{
  "status": "healthy",
  "version": "0.6.0",
  "rate_limit_info": {
    "limit": 60,
    "remaining": 59,
    "reset_after": 45
  }
}
```

### 401 Unauthorized

```json
{
  "detail": "Invalid or missing API Key",
  "type": "authentication_error"
}
```

### 429 Too Many Requests

```json
{
  "detail": "Rate limit exceeded",
  "retry_after": 45
}
```
