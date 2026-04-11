# Feature Specification: Rate Limiting e Proteção Azure

**Feature Branch**: `[006-rate-limiting]`
**Created**: 2026-04-11
**Status**: Draft
**Input**: User description: "Implementar rate limiting para proteger quotas do Azure Free Tier"

---

## User Scenarios & Testing

### User Story 1 - Rate Limiting por Endpoint (Priority: P1)

Como operador da API, quero limitar requisições por minuto para não exceder os limites do Azure Free Tier.

**Why this priority**: Exceder quotas Azure pode bloquear o serviço e gerar custos inesperados.

**Independent Test**: Após limite excedido, retorna 429 Too Many Requests.

**Acceptance Scenarios**:

1. **Given** limite de 10 req/min, **When** excedo o limite, **Then** recebo HTTP 429
2. **Given** rate limit ativo, **When** verifico headers, **Then** vejo X-RateLimit-Remaining
3. **Given** nova janela de tempo, **When** tempo passa, **Then** contador reseta automaticamente

### User Story 2 - Monitoramento de Quotas (Priority: P1)

Como operador, quero monitorar o uso de quotas Azure em tempo real.

**Why this priority**: Prevenção proactive de interrupções de serviço.

**Independent Test**: Health check mostra quotas restantes.

**Acceptance Scenarios**:

1. **Given** serviços Azure em uso, **When** consulto health, **Then** vejo quotas restantes
2. **Given** quota > 80%, **When** verifico, **Then** vejo warning no health status
3. **Given** quota excedida, **When** tento usar serviço, **Then** sistema bloqueia automaticamente

### User Story 3 - Hard Stop Automático (Priority: P1)

Como sistema, quero interromper automaticamente quando quotas forem atingidas.

**Why this priority**: Requisito crítico do projeto - hard stop obrigatório.

**Independent Test**: Quando quota atinge 100%, serviço retorna 429 imediatamente.

**Acceptance Scenarios**:

1. **Given** quota diária atingida, **When** nova requisição chega, **Then** retorna 429 sem chamar Azure
2. **Given** hard stop ativado, **When** verifico logs, **Then** vejo registro do bloqueio
3. **Given** novo dia, **When** meia-noite UTC passa, **Then** contador reseta

---

## Requirements

### Functional Requirements

- **FR-001**: Rate limiting por endpoint configurável
- **FR-002**: Headers X-RateLimit-* em todas respostas
- **FR-003**: HTTP 429 quando limite excedido
- **FR-004**: Health check mostra quotas restantes
- **FR-005**: Hard stop automático em 100% quota
- **FR-006**: Cache de uso em Redis/memory
- **FR-007**: Reset diário às 00:00 UTC
- **FR-008**: Configuração via variáveis de ambiente

### Key Entities

- **RateLimitConfig**: { daily_limit, per_minute, service }
- **QuotaTracker**: Armazena uso atual
- **RateLimitMiddleware**: Intercepta requisições
- **AzureQuotaService**: Consulta quotas Azure

---

## Success Criteria

- **SC-001**: Nunca excede 100% da quota diária
- **SC-002**: Latência do rate limiting < 10ms
- **SC-003**: Health check atualizado em tempo real
- **SC-004**: Hard stop funciona sem intervenção manual

---

## Assumptions

- Redis opcional (fallback para memory)
- Azure SDK permite consulta de uso (ou estimamos)
- Um contador por serviço (text, speech, vision)
- Rate limit por IP ou API key (futuro)

---

## Technical Notes

### Limites Azure Free Tier
```python
RATE_LIMITS = {
    "text_analytics": {"daily": 160, "monthly": 5000},
    "speech": {"daily_minutes": 10, "monthly_minutes": 300},
    "computer_vision": {"daily": 160, "monthly": 5000}
}
```

### Arquitetura de Proteção (3 Camadas)

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

### Implementação - QuotaManager

```python
class QuotaManager:
    """Gerenciador de quotas com hard stop automático"""

    FREE_TIER_LIMITS = {
        ServiceType.TEXT_ANALYTICS: {"daily": 160, "monthly": 5000},
        ServiceType.SPEECH: {"daily_minutes": 10, "monthly_minutes": 300},
        ServiceType.VISION: {"daily": 160, "monthly": 5000}
    }

    async def check_and_increment(
        self,
        service: ServiceType,
        count: int = 1
    ) -> bool:
        """
        Verifica se há quota disponível e incrementa o contador.
        Returns: True se permitido, False se quota excedida (hard stop)
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

    async def _trigger_hard_stop(self, service: ServiceType, current: int, limit: int):
        """Dispara hard stop quando quota é excedida."""
        self._service_status[service] = False
        logger.critical(f"HARD STOP ATIVADO para {service.value}")
```

### Decorator para Proteção de Endpoints

```python
def protect_azure_quota(service_type: ServiceType, cost_units: int = 1):
    """Decorator que protege endpoints contra consumo além do free tier."""
    def decorator(func):
        @wraps(func)
        async def wrapper(*args, **kwargs):
            quota_manager = await get_quota_manager()

            # Verifica se serviço está disponível
            if not quota_manager.is_service_available(service_type):
                raise HTTPException(
                    status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                    detail={
                        "error": "SERVICE_TEMPORARILY_UNAVAILABLE",
                        "message": f"Serviço {service_type.value} temporariamente indisponível",
                        "reason": "Free tier quota exceeded for today",
                        "retry_after": "00:00 UTC"
                    }
                )

            # Verifica e incrementa quota
            allowed = await quota_manager.check_and_increment(service_type, cost_units)

            if not allowed:
                raise HTTPException(
                    status_code=status.HTTP_429_TOO_MANY_REQUESTS,
                    detail={
                        "error": "QUOTA_EXCEEDED",
                        "message": f"Limite diário do Azure {service_type.value} atingido"
                    },
                    headers={"Retry-After": str(_seconds_until_midnight_utc())}
                )

            return await func(*args, **kwargs)
        return wrapper
    return decorator
```

### Implementação
- Middleware FastAPI para interceptar requisições
- Redis INCR para contadores atômicos
- TTL nas chaves para reset automático
- Headers padrão: X-RateLimit-Limit, X-RateLimit-Remaining, X-RateLimit-Reset
- Circuit breaker: retorna HTTP 503 quando quota excedida
- Reset automático às 00:00 UTC via cron job ou TTL

### Referências
- [Azure Spending Limit](https://learn.microsoft.com/en-us/azure/cost-management-billing/manage/spending-limit)
- [Avoid Charges with Azure Free Account](https://learn.microsoft.com/en-us/azure/cost-management-billing/manage/avoid-charges-free-account)
- Documentação completa: `docs/technical/azure-free-tier-hard-stop.md`
