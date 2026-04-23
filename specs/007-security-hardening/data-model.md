# Data Model: Security Hardening 2026

**Feature**: Security Hardening | **Date**: 2026-04-22

---

## Core Security Models

### SecurityConfig

Configurações de segurança carregadas do environment.

```python
class SecurityConfig(BaseSettings):
    """Configurações de segurança da aplicação"""
    
    # API Key Authentication
    api_key: str = Field(..., description="API Key para autenticação")
    api_key_header: str = Field(default="X-API-Key", description="Header name para API Key")
    
    # Rate Limiting
    rate_limit_per_minute: int = Field(default=60, ge=1)
    rate_limit_auth_per_minute: int = Field(default=5, ge=1)  # Mais restritivo para auth
    redis_url: Optional[str] = Field(default=None, description="Redis URL para rate limit distribuído")
    
    # CORS Configuration
    cors_origins: List[str] = Field(default=["http://localhost:3000"])
    cors_allow_credentials: bool = Field(default=True)
    cors_allow_methods: List[str] = Field(default=["GET", "POST", "PUT", "DELETE"])
    cors_allow_headers: List[str] = Field(default=["Authorization", "Content-Type", "X-API-Key"])
    
    # Security Headers
    security_headers_enabled: bool = Field(default=True)
    hsts_max_age: int = Field(default=31536000, description="HSTS max-age em segundos (1 ano)")
    hsts_include_subdomains: bool = Field(default=True)
    
    # Environment
    environment: Literal["development", "staging", "production"] = Field(default="development")
    
    # File Upload Security
    max_upload_size_mb: int = Field(default=50, ge=1, le=500)
    allowed_audio_mime_types: List[str] = Field(default=["audio/wav", "audio/mpeg", "audio/ogg"])
    allowed_video_mime_types: List[str] = Field(default=["video/mp4", "video/avi", "video/quicktime"])
    blocked_extensions: List[str] = Field(default=[".exe", ".sh", ".bat", ".cmd", ".php", ".jsp"])
    
    # Logging
    audit_log_path: str = Field(default="logs/audit")
    audit_log_retention_days: int = Field(default=180)  # 6 meses LGPD
    
    class Config:
        env_prefix = "SECURITY_"
        env_file = ".env"
```

---

### APIKey

Representação interna de uma API Key (nunca exposta em plaintext).

```python
class APIKey(BaseModel):
    """API Key com metadata"""
    
    key_hash: str  # SHA256 da key, usado para lookup
    key_prefix: str  # Primeiros 8 caracteres, para identificação
    roles: List[Literal["read", "write", "admin"]]
    created_at: datetime
    expires_at: Optional[datetime]
    last_used_at: Optional[datetime]
    is_active: bool = True
    
    @field_validator("key_hash")
    @classmethod
    def validate_hash(cls, v: str) -> str:
        """Garante que é um hash SHA256 válido"""
        if len(v) != 64:
            raise ValueError("Invalid SHA256 hash")
        return v
```

---

### RateLimitInfo

Informações de rate limiting para retornar ao cliente.

```python
class RateLimitInfo(BaseModel):
    """Informações de rate limiting"""
    
    limit: int = Field(description="Limite de requisições")
    remaining: int = Field(description="Requisições restantes no período")
    reset_after: int = Field(description="Segundos até reset do limite")
    retry_after: Optional[int] = Field(default=None, description="Segundos para retry (quando excedido)")
    
    def to_headers(self) -> Dict[str, str]:
        """Converte para headers HTTP"""
        headers = {
            "X-RateLimit-Limit": str(self.limit),
            "X-RateLimit-Remaining": str(self.remaining),
            "X-RateLimit-Reset": str(self.reset_after),
        }
        if self.retry_after:
            headers["Retry-After"] = str(self.retry_after)
        return headers
```

---

### AuditLogEntry

Entrada de log de auditoria LGPD-compliant.

```python
class AuditLogEntry(BaseModel):
    """Entrada de log de auditoria"""
    
    timestamp: datetime = Field(default_factory=datetime.utcnow)
    event_type: Literal[
        "access_granted",
        "access_denied",
        "auth_success",
        "auth_failure",
        "rate_limit_exceeded",
        "suspicious_activity",
        "data_export",
        "config_change"
    ]
    
    # Request Info
    ip_address: str
    user_agent: Optional[str] = None
    request_id: str  # correlation_id
    endpoint: str
    http_method: str
    
    # Auth Info (sanitized)
    api_key_hash: Optional[str] = None  # SHA256 da key, não a key
    patient_id_hash: Optional[str] = None  # SHA256 do patient_id
    roles: List[str] = Field(default_factory=list)
    
    # Result
    result: Literal["success", "failure", "blocked", "error"]
    status_code: Optional[int] = None
    
    # Details (sanitized - nunca dados sensíveis)
    details: Dict[str, Any] = Field(default_factory=dict)
    
    # Risk Assessment
    risk_score: Optional[float] = Field(default=None, ge=0.0, le=1.0)
    risk_flags: List[str] = Field(default_factory=list)
    
    class Config:
        json_encoders = {
            datetime: lambda v: v.isoformat()
        }
```

---

### FileValidationResult

Resultado da validação de arquivo.

```python
class FileValidationResult(BaseModel):
    """Resultado da validação de arquivo"""
    
    is_valid: bool
    original_filename: str
    sanitized_filename: str
    detected_mime_type: Optional[str] = None
    expected_mime_types: List[str] = Field(default_factory=list)
    size_bytes: int
    max_size_bytes: int
    
    # Error Info
    errors: List[str] = Field(default_factory=list)
    warnings: List[str] = Field(default_factory=list)
    
    def raise_if_invalid(self) -> None:
        """Levanta exceção se arquivo inválido"""
        if not self.is_valid:
            raise ValueError(f"Invalid file: {', '.join(self.errors)}")
```

---

### SecurityContext

Contexto de segurança da requisição atual.

```python
class SecurityContext(BaseModel):
    """Contexto de segurança da requisição"""
    
    request_id: str
    api_key: Optional[str] = None  # Apenas durante validação, nunca logado
    api_key_hash: Optional[str] = None  # Hash SHA256, seguro para logar
    roles: List[str] = Field(default_factory=list)
    ip_address: str
    user_agent: Optional[str] = None
    is_authenticated: bool = False
    
    # Rate Limiting
    rate_limit_key: Optional[str] = None  # Key usada para rate limiting
    
    # BOLA Protection
    resource_owner_hash: Optional[str] = None  # Hash do dono do recurso
    
    def has_role(self, role: str) -> bool:
        """Verifica se tem papel específico"""
        return role in self.roles
    
    def can_access_resource(self, resource_owner_hash: str) -> bool:
        """Verifica se pode acessar recurso (BOLA protection)"""
        if "admin" in self.roles:
            return True
        return self.resource_owner_hash == resource_owner_hash
```

---

## State Diagrams

### API Key Lifecycle

```
[Created] --(activate)--> [Active] --(use)--> [Active]
    |                            |
    |--(expire)                  |--(revoke)
    v                            v
[Expired]                    [Revoked]
```

### Rate Limiting State

```
[Within Limit] --(exceed)--> [Rate Limited] --(reset)--> [Within Limit]
       |                           |
       |--(request allowed)        |--(request blocked: 429)
       v                           v
   [Process]                  [Return 429 with Retry-After]
```

---

## Validation Rules

### Filename Sanitization

```python
# Regras aplicadas em ordem:
1. Strip path separators: /, \, \x00
2. Remove null bytes
3. Collapse multiple dots: ... -> .
4. Remove leading dots (hidden files)
5. Limit length: max 255 chars
6. Replace special chars: _ (underscore)
7. Ensure unique: append counter se necessário
```

### MIME Type Validation

```python
# Audio
ALLOWED_AUDIO_MAGIC = {
    "audio/wav": [b"RIFF"],  # RIFF....WAVE
    "audio/mpeg": [b"\xff\xfb", b"\xff\xf3", b"\xff\xf2"],  # MP3
    "audio/ogg": [b"OggS"],  # OGG
}

# Video
ALLOWED_VIDEO_MAGIC = {
    "video/mp4": [b"\x00\x00\x00", b"ftyp"],  # MP4
    "video/avi": [b"RIFF"],  # AVI (RIFF....AVI)
    "video/quicktime": [b"\x00\x00\x00", b"moov"],  # MOV
}
```

### Secret Masking Patterns

```python
SECRET_PATTERNS = [
    # Azure keys
    (r'[a-f0-9]{32}([a-f0-9]{8})[a-f0-9]{24}', r'****-****-****-\1'),
    # API keys genéricas
    (r'(api[_-]?key[=:\s])([^\s&]+)', r'\1****'),
    # JWT tokens (nunca logar payload)
    (r'(eyJ[a-zA-Z0-9_-]*\.[a-zA-Z0-9_-]*)', r'\1.****.****'),
]
```

---

## JSON Schema Examples

### Audit Log JSON Line

```json
{
  "timestamp": "2026-04-22T10:30:00Z",
  "event_type": "access_granted",
  "ip_address": "192.168.1.100",
  "user_agent": "Mozilla/5.0...",
  "request_id": "550e8400-e29b-41d4-a716-446655440000",
  "endpoint": "/analyze/text",
  "http_method": "POST",
  "api_key_hash": "a1b2c3d4e5f6...",  // SHA256, 64 chars
  "patient_id_hash": "f6e5d4c3b2a1...",  // SHA256, 64 chars
  "roles": ["read", "write"],
  "result": "success",
  "status_code": 200,
  "details": {
    "text_length": 150,  // Não o conteúdo!
    "processing_time_ms": 45
  },
  "risk_score": 0.1,
  "risk_flags": []
}
```

### Rate Limit Response

```json
{
  "error": "Rate limit exceeded",
  "limit": 60,
  "remaining": 0,
  "reset_after": 45,
  "retry_after": 45
}
```

---

## Storage

### Audit Log Files

```
logs/
└── audit/
    ├── audit-2026-04-22.jsonl      # Logs do dia
    ├── audit-2026-04-21.jsonl      # Logs do dia anterior
    └── archive/
        └── audit-2026-03-22.jsonl.gz  # Arquivados após retenção
```

Formato: JSON Lines (um JSON por linha), append-only.

Rotação: Diária via logrotate ou aplicação.

Retenção: 180 dias (6 meses LGPD), depois arquivamento em GZIP.
