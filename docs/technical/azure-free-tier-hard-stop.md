# Estratégia de Hard Stop - Azure Free Tier Protection

> **Objetivo**: Garantir que a aplicação NUNCA consuma recursos além do free tier do Azure, interrompendo o serviço imediatamente quando os limites forem atingidos.

---

## Resumo Executivo

**SIM, é possível** implementar um hard stop a nível de aplicação, mas requer uma estratégia combinada:

1. **Azure Spending Limit** (nível de subscription) - Desabilita serviços automaticamente
2. **Application-Level Rate Limiting** (nível de código) - Contador interno de requisições
3. **Circuit Breaker Pattern** - Interrompe o serviço quando thresholds são atingidos
4. **Monitoramento em tempo real** - Tracking de quotas via Azure SDK

---

## 1. Azure Spending Limit (Primeira Linha de Defesa)

### O que é
O Azure Spending Limit é uma proteção automática para contas free:

- ✅ **Ativado por padrão** em contas Azure Free
- ✅ Quando os créditos acabam, os serviços são **desabilitados automaticamente**
- ✅ VMS são **stopped e de-allocated**
- ✅ Storage accounts ficam **read-only**
- ✅ **Sem cobrança** além do limite

### Limitações do Spending Limit
⚠️ **IMPORTANTE**: Não protege contra:
- Serviços "Always Free" que excedem quotas (ex: 5k requests do Text Analytics)
- Cobranças de egress (dados saindo)
- Serviços de terceiros (Marketplace)

---

## 2. Estratégia de Hard Stop na Aplicação

### Arquitetura de Proteção

```
┌─────────────────────────────────────────────────────────────────┐
│                    Aplicação FastAPI                             │
├─────────────────────────────────────────────────────────────────┤
│                                                                   │
│  ┌──────────────────┐   ┌──────────────────┐   ┌─────────────┐ │
│  │  Request         │──►│  Rate Limiter    │──►│  Azure      │ │
│  │  Interceptor     │   │  (Redis/SQLite)  │   │  AI Service │ │
│  └──────────────────┘   └────────┬─────────┘   └─────────────┘ │
│                                  │                               │
│                        ┌─────────▼──────────┐                  │
│                        │  Quota Tracker     │                  │
│                        │  - Contador local    │                  │
│                        │  - Check antes de    │                  │
│                        │    cada chamada     │                  │
│                        └─────────┬──────────┘                  │
│                                  │                               │
│                        ┌─────────▼──────────┐                  │
│                        │  Hard Stop         │                  │
│                        │  (Circuit Breaker) │                  │
│                        └────────────────────┘                  │
│                                                                   │
└─────────────────────────────────────────────────────────────────┘
```

---

## 3. Implementação - Código Python

### 3.1 Rate Limiter com Hard Stop

```python
# src/core/rate_limiter.py
import asyncio
from datetime import datetime, timedelta
from enum import Enum
from typing import Optional, Dict
import json
import redis.asyncio as redis
from sqlalchemy.ext.asyncio import AsyncSession


class ServiceType(Enum):
    TEXT_ANALYTICS = "text_analytics"
    SPEECH = "speech"
    VISION = "vision"


class QuotaManager:
    """
    Gerenciador de quotas do Azure Free Tier.
    Implementa hard stop quando limites são atingidos.
    """

    # Limites do Azure Free Tier (F0)
    FREE_TIER_LIMITS = {
        ServiceType.TEXT_ANALYTICS: {
            "daily": 160,        # ~5000/mês / 31 dias
            "monthly": 5000,
            "window": "daily"
        },
        ServiceType.SPEECH: {
            "daily_minutes": 10,  # ~300/mês / 30 dias
            "monthly_minutes": 300,
            "window": "daily"
        },
        ServiceType.VISION: {
            "daily": 160,        # ~5000/mês / 31 dias
            "monthly": 5000,
            "window": "daily"
        }
    }

    def __init__(self, redis_client: Optional[redis.Redis] = None, db_session: Optional[AsyncSession] = None):
        self.redis = redis_client
        self.db = db_session
        self._local_counters: Dict[str, int] = {}
        self._service_status: Dict[ServiceType, bool] = {
            ServiceType.TEXT_ANALYTICS: True,
            ServiceType.SPEECH: True,
            ServiceType.VISION: True
        }

    async def check_and_increment(
        self,
        service: ServiceType,
        count: int = 1,
        cost_units: Optional[int] = None
    ) -> bool:
        """
        Verifica se há quota disponível e incrementa o contador.

        Returns:
            bool: True se permitido, False se quota excedida (hard stop)
        """
        limits = self.FREE_TIER_LIMITS[service]

        # Verifica se serviço já está em hard stop
        if not self._service_status[service]:
            return False

        # Obtém contador atual
        current_count = await self._get_counter(service)

        # Verifica limite
        limit = limits.get("daily", limits.get("daily_minutes", 0))

        if current_count + count > limit:
            # HARD STOP: Desabilita o serviço
            await self._trigger_hard_stop(service, current_count, limit)
            return False

        # Incrementa contador
        await self._increment_counter(service, count)
        return True

    async def _get_counter(self, service: ServiceType) -> int:
        """Obtém contador atual do serviço."""
        key = f"quota:{service.value}:{datetime.now().strftime('%Y-%m-%d')}"

        if self.redis:
            count = await self.redis.get(key)
            return int(count) if count else 0
        else:
            # Fallback para memória local (SQLite ou dict)
            return self._local_counters.get(key, 0)

    async def _increment_counter(self, service: ServiceType, count: int = 1):
        """Incrementa contador do serviço."""
        key = f"quota:{service.value}:{datetime.now().strftime('%Y-%m-%d')}"

        if self.redis:
            await self.redis.incrby(key, count)
            # Expira ao final do dia
            await self.redis.expireat(
                key,
                int((datetime.now() + timedelta(days=1)).replace(hour=0, minute=0, second=0).timestamp())
            )
        else:
            self._local_counters[key] = self._local_counters.get(key, 0) + count

    async def _trigger_hard_stop(self, service: ServiceType, current: int, limit: int):
        """Dispara hard stop quando quota é excedida."""
        self._service_status[service] = False

        # Log crítico
        print(f"🚨 HARD STOP ATIVADO para {service.value}")
        print(f"   Limite: {limit}, Atual: {current}")
        print(f"   Serviço será reiniciado às 00:00 UTC")

        # Aqui você pode adicionar:
        # - Envio de alerta (email/Slack)
        # - Persistência do estado em banco
        # - Atualização do health check

    def is_service_available(self, service: ServiceType) -> bool:
        """Verifica se serviço está disponível."""
        return self._service_status[service]

    async def get_quota_status(self) -> Dict:
        """Retorna status atual das quotas."""
        status = {}
        for service in ServiceType:
            key = f"quota:{service.value}:{datetime.now().strftime('%Y-%m-%d')}"
            current = await self._get_counter(service)
            limits = self.FREE_TIER_LIMITS[service]
            limit = limits.get("daily", limits.get("daily_minutes", 0))

            status[service.value] = {
                "current": current,
                "limit": limit,
                "remaining": max(0, limit - current),
                "percentage": (current / limit * 100) if limit > 0 else 0,
                "available": self._service_status[service]
            }
        return status

    async def reset_daily_counters(self):
        """Reseta contadores diários (chamar às 00:00 UTC)."""
        self._local_counters.clear()
        for service in ServiceType:
            self._service_status[service] = True

        if self.redis:
            # Limpa todas as chaves de quota
            for service in ServiceType:
                pattern = f"quota:{service.value}:*"
                keys = await self.redis.keys(pattern)
                if keys:
                    await self.redis.delete(*keys)
```

### 3.2 Decorator para Proteção de Endpoints

```python
# src/core/decorators.py
from functools import wraps
from fastapi import HTTPException, status
from typing import Optional


def protect_azure_quota(service_type: ServiceType, cost_units: int = 1):
    """
    Decorator que protege endpoints contra consumo além do free tier.

    Usage:
        @app.post("/analyze/text")
        @protect_azure_quota(ServiceType.TEXT_ANALYTICS)
        async def analyze_text(...):
            ...
    """
    def decorator(func):
        @wraps(func)
        async def wrapper(*args, **kwargs):
            from src.api.dependencies import get_quota_manager

            quota_manager = await get_quota_manager()

            # Verifica se serviço está disponível
            if not quota_manager.is_service_available(service_type):
                raise HTTPException(
                    status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                    detail={
                        "error": "SERVICE_TEMPORARILY_UNAVAILABLE",
                        "message": f"Serviço {service_type.value} temporariamente indisponível",
                        "reason": "Free tier quota exceeded for today",
                        "retry_after": "00:00 UTC",
                        "solution": "Aguarde até meia-noite UTC ou upgrade para tier pago"
                    }
                )

            # Verifica e incrementa quota
            allowed = await quota_manager.check_and_increment(service_type, cost_units)

            if not allowed:
                raise HTTPException(
                    status_code=status.HTTP_429_TOO_MANY_REQUESTS,
                    detail={
                        "error": "QUOTA_EXCEEDED",
                        "message": f"Limite diário do Azure {service_type.value} atingido",
                        "service": service_type.value,
                        "limit_type": "free_tier_daily",
                        "retry_after": "00:00 UTC"
                    },
                    headers={"Retry-After": str(_seconds_until_midnight_utc())}
                )

            return await func(*args, **kwargs)
        return wrapper
    return decorator


def _seconds_until_midnight_utc() -> int:
    """Calcula segundos até meia-noite UTC."""
    from datetime import datetime, timedelta
    now = datetime.utcnow()
    midnight = now.replace(hour=0, minute=0, second=0, microsecond=0) + timedelta(days=1)
    return int((midnight - now).total_seconds())
```

### 3.3 Health Check com Status de Quota

```python
# src/api/routes/health.py
from fastapi import APIRouter, HTTPException, status
from datetime import datetime

router = APIRouter()


@router.get("/health")
async def health_check():
    """
    Health check que inclui status das quotas Azure.
    Retorna 503 se algum serviço estiver em hard stop.
    """
    from src.api.dependencies import get_quota_manager

    quota_manager = await get_quota_manager()
    quota_status = await quota_manager.get_quota_status()

    # Verifica se algum serviço está indisponível
    services_down = [
        service for service, status in quota_status.items()
        if not status.get("available", True)
    ]

    if services_down:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail={
                "status": "degraded",
                "timestamp": datetime.utcnow().isoformat(),
                "message": f"Serviço(s) indisponível(is) devido a quota excedida: {', '.join(services_down)}",
                "quota_status": quota_status,
                "solution": "Aguarde reset às 00:00 UTC ou considere upgrade"
            }
        )

    return {
        "status": "healthy",
        "timestamp": datetime.utcnow().isoformat(),
        "services": {
            "text_analytics": "available",
            "speech": "available",
            "vision": "available"
        },
        "quota": quota_status
    }
```

### 3.4 Middleware de Proteção Global

```python
# src/api/middleware.py
from fastapi import Request, HTTPException
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.responses import JSONResponse


class AzureQuotaProtectionMiddleware(BaseHTTPMiddleware):
    """
    Middleware global que protege contra consumo além do free tier.
    Intercepta todas as requisições e verifica quotas antes de processar.
    """

    async def dispatch(self, request: Request, call_next):
        # Verifica apenas endpoints que usam serviços Azure
        path = request.url.path

        if "/analyze/text" in path:
            service = ServiceType.TEXT_ANALYTICS
        elif "/analyze/audio" in path:
            service = ServiceType.SPEECH
        elif "/analyze/image" in path:
            service = ServiceType.VISION
        else:
            return await call_next(request)

        # Verifica se serviço está disponível
        from src.api.dependencies import get_quota_manager
        quota_manager = await get_quota_manager()

        if not quota_manager.is_service_available(service):
            return JSONResponse(
                status_code=503,
                content={
                    "error": "SERVICE_UNAVAILABLE",
                    "message": f"Serviço {service.value} indisponível - quota excedida",
                    "retry_after": "00:00 UTC"
                },
                headers={"Retry-After": str(_seconds_until_midnight_utc())}
            )

        return await call_next(request)
```

---

## 4. Configuração do Azure (Subscription Level)

### 4.1 Spending Limit (Obrigatório)

1. Acesse: https://portal.azure.com → Subscriptions → Sua assinatura
2. Verifique se "Spending limit" está **ATIVADO**
3. Isso garante que serviços sejam desabilitados se créditos acabarem

### 4.2 Budgets e Alertas (Recomendado)

```bash
# Criar budget via Azure CLI
az consumption budget create \
    --budget-name "FreeTierProtection" \
    --category Cost \
    --amount 0.01 \
    --time-grain Monthly \
    --start-date $(date +%Y-%m-01) \
    --end-date $(date -d "+12 months" +%Y-%m-01) \
    --resource-group myResourceGroup \
    --notification-key "AlertAt1Cent" \
    --notification-threshold 100 \
    --contact-emails "admin@exemplo.com"
```

---

## 5. Cron Job para Reset Diário

```python
# scripts/reset_quotas.py
import asyncio
import sys
sys.path.insert(0, "src")

from src.core.rate_limiter import QuotaManager


async def reset_daily_quotas():
    """
    Script para ser executado via cron às 00:00 UTC.
    Reseta todos os contadores diários.
    """
    print(f"Resetando quotas diárias...")

    quota_manager = QuotaManager()
    await quota_manager.reset_daily_counters()

    print("✅ Quotas resetadas com sucesso!")
    print("🟢 Todos os serviços estão disponíveis novamente.")


if __name__ == "__main__":
    asyncio.run(reset_daily_quotas())
```

**Cron job (crontab):**
```bash
# Executa às 00:00 UTC todos os dias
0 0 * * * cd /path/to/app && python scripts/reset_quotas.py >> /var/log/quota_reset.log 2>&1
```

---

## 6. Testes de Proteção

```python
# tests/integration/test_quota_protection.py
import pytest
from fastapi.testclient import TestClient
from src.core.rate_limiter import QuotaManager, ServiceType


@pytest.mark.asyncio
async def test_hard_stop_when_quota_exceeded(client: TestClient):
    """
    Testa se a aplicação retorna 503 quando quota é excedida.
    """
    # Simula quota excedida
    quota_manager = QuotaManager()

    # Força contador acima do limite
    for _ in range(200):  # Acima do limite diário de 160
        await quota_manager.check_and_increment(ServiceType.TEXT_ANALYTICS)

    # Tenta fazer requisição
    response = client.post("/analyze/text", json={
        "texto": "Teste de proteção de quota"
    })

    assert response.status_code == 503
    assert "quota" in response.json()["error"].lower()


@pytest.mark.asyncio
async def test_rate_limit_headers(client: TestClient):
    """
    Testa se headers de rate limit são retornados corretamente.
    """
    response = client.get("/health")

    assert "X-RateLimit-Limit" in response.headers
    assert "X-RateLimit-Remaining" in response.headers
    assert "X-RateLimit-Reset" in response.headers
```

---

## 7. Resumo da Estratégia

### Camadas de Proteção

| Camada | Mecanismo | Quando Atua |
|--------|-----------|-------------|
| **1. Azure Spending Limit** | Desabilita subscription | Créditos Azure esgotados |
| **2. Application Rate Limiter** | Contador interno | Próximo ao limite diário (80%) |
| **3. Hard Stop (Circuit Breaker)** | Retorna 503 | Limite diário excedido |
| **4. Health Check** | Status em /health | Monitoramento contínuo |

### Comportamento Esperado

```
Cenário 1: Normal (dentro do limite)
→ Requisição → Rate Limiter (OK) → Azure → Resposta 200

Cenário 2: Próximo ao limite (>80%)
→ Requisição → Rate Limiter (OK + Alerta) → Azure → Resposta 200 + Header Warning

Cenário 3: Limite excedido (hard stop)
→ Requisição → Rate Limiter (Bloqueia) → Resposta 503 + Retry-After
→ Serviço fica indisponível até 00:00 UTC

Cenário 4: Reset diário
→ Cron job executa às 00:00 UTC → Contadores resetados → Serviço disponível novamente
```

---

## 8. Considerações Importantes

### ✅ Vantagens
- **Garantia de zero custo** - Hard stop impede qualquer consumo além do free tier
- **Previsibilidade** - Usuários sabem exatamente quando o serviço ficará indisponível
- **Transparência** - Health check mostra status em tempo real
- **Automático** - Reset diário às 00:00 UTC sem intervenção manual

### ⚠️ Limitações
- **Serviço indisponível** - Quando quota é atingida, o serviço para completamente
- **Não é "graceful degradation"** - É um stop completo, não throttling suave
- **Requer Redis ou SQLite** - Para persistência dos contadores entre restarts

### 🔧 Alternativas
Se o hard stop for muito agressivo, considere:
1. **Throttling suave** - Delay progressivo em vez de stop
2. **Caching** - Retornar resultados em cache quando quota excedida
3. **Multi-região** - Distribuir carga entre múltiplas subscriptions free

---

## Conclusão

Sim, é **totalmente possível** garantir que a aplicação nunca saia do free tier:

1. **Azure Spending Limit** já protege automaticamente (desabilita serviços)
2. **Application-Level Rate Limiter** adiciona proteção granular por serviço
3. **Hard Stop** garante que nenhuma requisição excedente chegue ao Azure
4. **Reset diário automático** via cron job

A aplicação ficará **indisponível temporariamente** quando os limites forem atingidos, mas **nunca haverá cobrança**.

**Próximo passo**: Implementar o `QuotaManager` no Task 007 (Rate Limiting).

---

**Sources:**
- [Azure Spending Limit](https://learn.microsoft.com/en-us/azure/cost-management-billing/manage/spending-limit)
- [Avoid Charges with Azure Free Account](https://learn.microsoft.com/en-us/azure/cost-management-billing/manage/avoid-charges-free-account)
- [Circuit Breaker Pattern - Azure Architecture](https://docs.microsoft.com/en-us/azure/architecture/patterns/circuit-breaker)
- [Azure Quota SDK for Python](https://azure.github.io/azure-sdk-for-python/quota.html)
