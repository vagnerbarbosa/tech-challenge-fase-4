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

# 3. Instalar dependências
poetry install --extras security

# 4. Testar
poetry run pytest tests/security/ -v
```

---

## Setup Completo

### 1. Geração de API Key

```bash
export API_KEY=$(openssl rand -hex 32)
echo "Sua API Key: $API_KEY"
```

### 2. Configuração (.env)

```bash
SECURITY_API_KEY="sua-key-hex-de-64-caracteres"
SECURITY_ENVIRONMENT="production"
SECURITY_CORS_ORIGINS="https://sua-app.com"
```

### 3. Dependências

```bash
poetry install --extras security
```

### 4. Verificação

```bash
curl -H "X-API-Key: sua-key" http://localhost:8000/health
```

---

## Testes de Segurança

```bash
poetry run pytest tests/security/ -v
```
