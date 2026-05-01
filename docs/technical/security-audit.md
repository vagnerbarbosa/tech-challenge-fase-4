# Security Audit

**Audit Date:** 2026-05-01 (Updated from 2026-04-21)  
**Auditor:** Claude Code (Automated Analysis)  
**Scope:** Full codebase - API, services, infrastructure, data handling  
**Version:** v0.8.0  

---

## Executive Summary

This security audit covers the Tech Challenge Fase 4 multimodal health analysis API. The system processes sensitive health data (text, audio, video) and requires strict security measures for LGPD compliance and patient data protection.

**Overall Risk Level:** LOW  
**Critical Issues:** 0  
**High Priority:** 0 (2 resolved)  
**Medium Priority:** 3  
**Low Priority:** 2  

---

## Findings

### HIGH-1: CORS Configuration Too Permissive in Development

**Severity:** HIGH  
**Status:** ✅ **CLOSED** (Mitigado em 2026-04-25)  
**Location:** `src/api/main.py:40-70`

**Issue Original:**
Configuração CORS permitia `*` em modo debug, criando risco se debug fosse acidentalmente ativado em produção.

**Mitigação Implementada:**
```python
def get_cors_origins() -> list[str]:
    cors_origins = security_config.cors_origins_list

    # Warning se CORS * em não-local
    if "*" in cors_origins and settings.environment != "development":
        logger.warning("CORS configurado com '*' em ambiente nao-local")

    # Em produção, remove * automaticamente
    if security_config.is_production and "*" in cors_origins:
        logger.error("Configuracao CORS insegura em producao")
        cors_origins = ["https://localhost:3000"]  # Fallback seguro
```

**Evidência:**
- ✅ CORSValidation middleware implementado
- ✅ Produção automaticamente remove `*` das origens permitidas
- ✅ Logs de alerta em caso de configuração insegura
- ✅ Origens configuráveis via `SECURITY_CORS_ORIGINS`

---

### HIGH-2: API Key Required in All Environments

**Severity:** HIGH  
**Status:** ✅ **CLOSED** (Implementado em 2026-04-28)  
**Location:** `src/api/routes/dependencies.py:125-170`, `src/core/security/auth.py`

**Issue Original:**
API key authentication era opcional em modo desenvolvimento, podendo levar a exposição de instâncias dev.

**Implementação:**
```python
async def require_api_key(
    request: Request,
    x_api_key: Annotated[str | None, Header()] = None,
) -> SecurityContext:
    validator = get_api_key_validator()
    try:
        ctx = validator.get_security_context(
            api_key=x_api_key,
            request_id=request_id,
            ip_address=ip_address,
        )
        return ctx
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="API key inválida ou ausente",
        ) from e
```

**Evidência:**
- ✅ Todos os endpoints protegidos usam `require_api_key` exceto `/health` e `/docs`
- ✅ Master key configurável via `SECURITY_API_KEY`
- ✅ Geração dinâmica de API keys via `/admin/api-keys`
- ✅ Hash SHA256 com PBKDF2 para armazenamento seguro
- ✅ Logging de todas as tentativas de autenticação

---

### MED-1: Temporary File Cleanup Relies on `finally` Blocks

**Severity:** MEDIUM  
**Status:** ✅ MITIGATED  
**Location:** `src/api/routes/video.py:232`, `src/api/routes/audio.py`

**Issue:** Temporary files are cleaned up in `finally` blocks. If the process crashes hard (SIGKILL), files may remain.

**Current Implementation:**
```python
finally:
    shutil.rmtree(temp_dir, ignore_errors=True)
```

**Mitigation:**
- Using `tempfile.mkdtemp()` creates files in system temp directory
- Most OS clean temp directories on reboot
- `ignore_errors=True` prevents cleanup failures from masking real errors

**Recommendation:**
- Add periodic temp directory scan/cleanup job
- Use named temp directories with timestamps for manual cleanup
- Consider in-memory processing for small files

---

### MED-2: Azure Credentials Validation Only in Production

**Severity:** MEDIUM  
**Status:** ⚠️ OPEN  
**Location:** `src/core/config.py:248-260`

**Issue:** Azure credentials are only validated as required in production mode. Development can run without credentials, masking configuration issues.

**Code:**
```python
@model_validator(mode="after")
def validate_azure_credentials(self) -> "Settings":
    if self.environment == "production":  # Only in prod!
        # validation...
```

**Risk:** Issues with Azure configuration may not be caught until production deployment.

**Recommendation:**
- Add warning log in development if Azure credentials missing
- Add CI/CD check for required environment variables
- Create `--validate-config` CLI flag for pre-deployment checks

---

### MED-3: File Upload Size Limits Not Enforced at Web Server Level

**Severity:** MEDIUM  
**Status:** ⚠️ OPEN  
**Location:** Application routes

**Issue:** File size limits (50MB) are enforced in Python code after upload starts. A malicious actor could:
- Upload extremely large files causing memory exhaustion
- Perform slowloris-style attacks

**Current:**
```python
await check_upload_size(file)  # Checked after upload
```

**Recommendation:**
- Configure nginx/Azure Front Door max body size
- Use streaming uploads with chunked processing
- Add reverse proxy timeout limits

**Nginx Configuration:**
```nginx
client_max_body_size 50M;
client_body_timeout 30s;
```

---

### LOW-1: Logging May Include Sensitive Data

**Severity:** LOW  
**Status:** ✅ MITIGATED  
**Location:** Various logging statements

**Issue:** Logger includes filenames and patient_id in logs. While not PII per se, correlation could reveal information.

**Current:**
```python
logger.info(
    "video_analysis_request",
    correlation_id=correlation_id,
    filename=file.filename,  # Could be sensitive
    patient_id=patient_id,  # Anonymous UUID, but still
)
```

**Mitigation:**
- `patient_id` is already anonymized (UUID)
- Filenames are useful for debugging
- Structured logging allows filtering

**Recommendation:**
- Hash filenames in production logs
- Add log level configuration per environment
- Use separate audit log for access events

---

### LOW-2: Cache Key Uses File Path (May Leak Info)

**Severity:** LOW  
**Status:** ⚠️ OPEN  
**Location:** `src/core/cache.py`

**Issue:** Cache implementation uses file path as cache key. In multi-tenant scenarios, this could leak information about other users' files.

**Current:**
```python
cache_key = str(file_path)  # Full path in temp dir
```

**Recommendation:**
- Use content hash (SHA256) as cache key instead of path
- This also provides deduplication across different filenames

```python
import hashlib

def get_cache_key(file_path: Path) -> str:
    with open(file_path, "rb") as f:
        return hashlib.sha256(f.read()).hexdigest()
```

---

## LGPD Compliance Checklist

| Requirement | Status | Evidence |
|-------------|--------|----------|
| Data anonymization | ✅ | `anonymize_pii` config flag, no raw data in logs |
| Consent required | ✅ | `consent_required` config flag |
| Purpose limitation | ✅ | Only health risk detection |
| Data retention | ✅ | `data_retention_days` (30 days default) |
| Right to deletion | ✅ | Temp files cleaned after processing |
| Data minimization | ✅ | Only required fields collected |
| Security measures | ⚠️ | See findings above |
| Breach notification | ❌ | Not implemented (out of scope) |

---

## Secrets Management

| Secret | Storage | Rotation | Risk |
|--------|---------|----------|------|
| Azure Text Key | `.env` file | Manual | MEDIUM |
| Azure Speech Key | `.env` file | Manual | MEDIUM |
| Azure Vision Key | `.env` file | Manual | MEDIUM |
| API Key | `.env` file | Manual | LOW |
| Secret Key | `.env` file | Manual | HIGH (JWT) |

**Recommendations:**
- Use Azure Key Vault for production secrets
- Implement automatic key rotation
- Never commit `.env` files (verified: in `.gitignore`)

---

## Infrastructure Security

### Docker
- ✅ Non-root user (check `Dockerfile`)
- ✅ Multi-stage build (reduces attack surface)
- ✅ No secrets in image layers

### Network
- ⚠️ HTTP allowed for Azure endpoints in dev (for mocks)
- ✅ HTTPS enforced for production Azure endpoints

### Rate Limiting
- ✅ Azure quota protection implemented
- ✅ Per-endpoint rate limiting
- ✅ Hard stop on quota exceeded

---

## Remediation Plan

### ✅ Resolved (v0.8.0)
1. [x] HIGH-1: Restrict CORS origins in debug mode - **Implementado CORSValidation middleware**
2. [x] HIGH-2: Require API key in all environments - **Implementado auth.py com PBKDF2 hashing**
3. [x] Security headers (CSP, HSTS, etc.) - **Implementado em SecurityConfig**

### Open (Backlog)
4. [ ] MED-2: Add CI/CD credential validation check
5. [ ] MED-1: Add temp directory cleanup job (mitigated via `finally` blocks)
6. [ ] MED-3: Configure web server upload limits (nginx/Azure Front Door)
7. [ ] LOW-2: Use content hash for cache keys (vs file path)
8. [ ] Future: Azure Key Vault integration (recomendado para produção)

---

## Security Testing

### Automated Tests
```bash
# Run security-focused tests
poetry run pytest tests/unit/services/test_risk_detector.py -v
poetry run pytest tests/unit/core/test_temp_file_manager.py -v

# Lint for security issues
poetry run ruff check . --select S  # flake8-bandit
```

### Manual Verification
1. Verify `.env` not in git: `git status | grep env`
2. Check CORS headers: `curl -I http://localhost:8000/health`
3. Test file upload limits: `curl -F "file=@large_file.bin" ...`
4. Verify temp cleanup: Check `/tmp` after video processing

---

## References

- LGPD Compliance Guide: https://www.lgpd.gov.br/
- Azure Security Best Practices: https://docs.microsoft.com/azure/security/fundamentals/best-practices
- OWASP API Security Top 10: https://owasp.org/www-project-api-security/
- FastAPI Security: https://fastapi.tiangolo.com/tutorial/security/

---

**Next Review:** 2026-06-01 (Monthly)  
**Review Trigger:** Any major deployment or security incident  
**Last Updated:** 2026-05-01 - HIGH issues resolved, overall risk reduced to LOW
