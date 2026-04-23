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
    rate_limit_auth_per_minute: int = Field(default=5, ge=1)
    redis_url: Optional[str] = Field(default=None, description="Redis URL para rate limit distribuído")
    
    # CORS Configuration
    cors_origins: List[str] = Field(default=["http://localhost:3000"])
    cors_allow_credentials: bool = Field(default=True)
    cors_allow_methods: List[str] = Field(default=["GET", "POST", "PUT", "DELETE"])
    cors_allow_headers: List[str] = Field(default=["Authorization", "Content-Type", "X-API-Key"])
    
    # Security Headers
    security_headers_enabled: bool = Field(default=True)
    hsts_max_age: int = Field(default=31536000, description="HSTS max-age em segundos")
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
    audit_log_retention_days: int = Field(default=180)
```

---

### APIKey

```python
class APIKey(BaseModel):
    """API Key com metadata"""
    
    key_hash: str
    key_prefix: str
    roles: List[Literal["read", "write", "admin"]]
    created_at: datetime
    expires_at: Optional[datetime]
    last_used_at: Optional[datetime]
    is_active: bool = True
```

---

### RateLimitInfo

```python
class RateLimitInfo(BaseModel):
    """Informações de rate limiting"""
    
    limit: int
    remaining: int
    reset_after: int
    retry_after: Optional[int] = None
```

---

### AuditLogEntry

```python
class AuditLogEntry(BaseModel):
    """Entrada de log de auditoria"""
    
    timestamp: datetime
    event_type: Literal["access", "auth_failure", "rate_limit_exceeded", "suspicious_activity"]
    ip_address: str
    user_agent: Optional[str]
    api_key_hash: Optional[str]
    endpoint: str
    result: Literal["success", "failure", "blocked"]
    details: Dict[str, Any]
```

---

### FileValidationResult

```python
class FileValidationResult(BaseModel):
    """Resultado da validação de arquivo"""
    
    is_valid: bool
    original_filename: str
    sanitized_filename: str
    detected_mime_type: Optional[str]
    size_bytes: int
    errors: List[str]
```

---

### SecurityContext

```python
class SecurityContext(BaseModel):
    """Contexto de segurança da requisição"""
    
    request_id: str
    api_key_hash: Optional[str]
    roles: List[str]
    ip_address: str
    is_authenticated: bool = False
```
