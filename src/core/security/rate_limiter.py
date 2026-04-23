"""Implementação de rate limiting com algoritmo Token Bucket.

Fornece backends de rate limiting para Redis (distribuído) e
memória (fallback local). Usa o algoritmo Token Bucket para
rate limiting suave com capacidade de burst.
"""

import hashlib
import time
from abc import ABC, abstractmethod
from typing import Any

from structlog import get_logger

from src.core.config import settings

logger = get_logger(__name__)


class RateLimiterBackend(ABC):
    """Classe base abstrata para backends de rate limiter."""

    @abstractmethod
    async def get_token_bucket(self, key: str) -> dict[str, Any] | None:
        """Obtém o estado atual do bucket de tokens para uma chave.

        Args:
            key: Identificador único para o bucket de rate limit

        Returns:
            Dict com tokens e last_update ou None se não existir
        """
        ...

    @abstractmethod
    async def set_token_bucket(self, key: str, bucket: dict[str, Any], ttl: int) -> None:
        """Define o estado do bucket de tokens para uma chave.

        Args:
            key: Identificador único para o bucket de rate limit
            bucket: Dict com tokens e last_update
            ttl: Tempo de vida em segundos
        """
        ...

    @abstractmethod
    async def increment_counter(self, key: str, ttl: int) -> int:
        """Incrementa um contador e retorna o novo valor.

        Args:
            key: Chave do contador
            ttl: Tempo de vida em segundos

        Returns:
            Novo valor do contador
        """
        ...

    @abstractmethod
    async def get_counter(self, key: str) -> int:
        """Obtém o valor atual do contador.

        Args:
            key: Chave do contador

        Returns:
            Valor atual do contador
        """
        ...


class MemoryRateLimiterBackend(RateLimiterBackend):
    """Backend de rate limiter em memória (para desenvolvimento/testes).

    Armazena todos os dados de rate limit na memória do processo.
    Nota: Este backend não é compartilhado entre múltiplos processos.
    """

    def __init__(self) -> None:
        """Inicializa o backend em memória."""
        self._buckets: dict[str, dict[str, Any]] = {}
        self._counters: dict[str, tuple[int, float]] = {}  # (value, expiry)

    async def get_token_bucket(self, key: str) -> dict[str, Any] | None:
        """Obtém bucket de tokens da memória."""
        bucket = self._buckets.get(key)
        if bucket:
            # Check if expired
            expiry = bucket.get("expiry", 0)
            if time.time() > expiry:
                del self._buckets[key]
                return None
        return bucket

    async def set_token_bucket(self, key: str, bucket: dict[str, Any], ttl: int) -> None:
        """Define bucket de tokens na memória com TTL."""
        bucket["expiry"] = time.time() + ttl
        self._buckets[key] = bucket

    async def increment_counter(self, key: str, ttl: int) -> int:
        """Incrementa contador na memória."""
        now = time.time()
        current, expiry = self._counters.get(key, (0, 0))

        if now > expiry:
            # Reset expired counter
            current = 0
            expiry = now + ttl

        current += 1
        self._counters[key] = (current, expiry)
        return current

    async def get_counter(self, key: str) -> int:
        """Obtém valor do contador da memória."""
        now = time.time()
        current, expiry = self._counters.get(key, (0, 0))

        if now > expiry:
            return 0
        return current


class RedisRateLimiterBackend(RateLimiterBackend):
    """Backend de rate limiter baseado em Redis (para produção).

    Usa Redis para rate limiting distribuído entre múltiplos servidores.
    """

    def __init__(self, redis_url: str | None = None) -> None:
        """Inicializa o backend Redis.

        Args:
            redis_url: URL de conexão do Redis
        """
        self._redis_url = redis_url or settings.redis_url
        self._redis: Any = None
        self._initialized = False

    async def _get_redis(self) -> Any:
        """Obtém ou cria conexão com Redis."""
        if not self._initialized:
            try:
                import redis.asyncio as redis

                self._redis = redis.from_url(self._redis_url, decode_responses=True)
                self._initialized = True
            except ImportError:
                logger.error("redis package not installed")
                raise RuntimeError("Redis package not installed") from None
            except Exception as e:
                logger.error("redis_connection_error", error=str(e))
                raise
        return self._redis

    async def get_token_bucket(self, key: str) -> dict[str, Any] | None:
        """Obtém bucket de tokens do Redis."""
        try:
            redis = await self._get_redis()
            data = await redis.hgetall(f"rl:b:{key}")
            if data:
                return {
                    "tokens": float(data.get("tokens", 0)),
                    "last_update": float(data.get("last_update", 0)),
                }
            return None
        except Exception as e:
            logger.warning("redis_get_bucket_error", error=str(e))
            return None

    async def set_token_bucket(self, key: str, bucket: dict[str, Any], ttl: int) -> None:
        """Define bucket de tokens no Redis com TTL."""
        try:
            redis = await self._get_redis()
            await redis.hset(f"rl:b:{key}", mapping={
                "tokens": bucket["tokens"],
                "last_update": bucket["last_update"],
            })
            await redis.expire(f"rl:b:{key}", ttl)
        except Exception as e:
            logger.warning("redis_set_bucket_error", error=str(e))

    async def increment_counter(self, key: str, ttl: int) -> int:
        """Incrementa contador no Redis."""
        try:
            redis = await self._get_redis()
            pipe = redis.pipeline()
            pipe.incr(f"rl:c:{key}")
            pipe.expire(f"rl:c:{key}", ttl)
            results = await pipe.execute()
            return results[0]
        except Exception as e:
            logger.warning("redis_incr_error", error=str(e))
            return 1

    async def get_counter(self, key: str) -> int:
        """Obtém valor do contador do Redis."""
        try:
            redis = await self._get_redis()
            value = await redis.get(f"rl:c:{key}")
            return int(value) if value else 0
        except Exception as e:
            logger.warning("redis_get_counter_error", error=str(e))
            return 0


class TokenBucketRateLimiter:
    """Implementação de rate limiter com Token Bucket.

    Implementa o algoritmo Token Bucket para rate limiting com:
    - Taxa configurável (tokens por segundo)
    - Capacidade de burst (tamanho do bucket)
    - Identificação por cliente via chave

    Example:
        limiter = TokenBucketRateLimiter(
            rate=1.0,  # 1 token por segundo
            capacity=60,  # burst de 60 requisições
        )

        # Verifica se a requisição é permitida
        is_allowed = await limiter.is_allowed("client_123")
    """

    def __init__(
        self,
        rate: float = 1.0,
        capacity: int = 60,
        backend: RateLimiterBackend | None = None,
        key_prefix: str = "rl",
    ) -> None:
        """Inicializa o rate limiter com Token Bucket.

        Args:
            rate: Tokens adicionados por segundo
            capacity: Máximo de tokens (capacidade de burst)
            backend: Backend de armazenamento (padrão: memória)
            key_prefix: Prefixo para chaves de rate limit
        """
        self.rate = rate
        self.capacity = capacity
        self.backend = backend or MemoryRateLimiterBackend()
        self.key_prefix = key_prefix
        self._ttl = int((capacity / rate) * 2) if rate > 0 else 3600  # 2x refill time

    def _make_key(self, identifier: str) -> str:
        """Cria chave de rate limit a partir do identificador.

        Args:
            identifier: Identificador do cliente (IP, hash da chave de API, etc.)

        Returns:
            String de chave hasheada
        """
        # Hash the identifier to avoid storing raw IPs/keys
        hashed = hashlib.sha256(f"{self.key_prefix}:{identifier}".encode()).hexdigest()[:16]
        return f"{self.key_prefix}:{hashed}"

    async def is_allowed(self, identifier: str, tokens: int = 1) -> tuple[bool, dict[str, Any]]:
        """Verifica se uma requisição é permitida sob o rate limit.

        Args:
            identifier: Identificador do cliente
            tokens: Número de tokens para consumir (padrão: 1)

        Returns:
            Tupla de (is_allowed, rate_limit_info)
            rate_limit_info contém: limit, remaining, reset_after, retry_after
        """
        key = self._make_key(identifier)
        now = time.time()

        # Get or create bucket
        bucket = await self.backend.get_token_bucket(key)

        if bucket is None:
            # New bucket - start full
            bucket = {
                "tokens": self.capacity - tokens,
                "last_update": now,
            }
            await self.backend.set_token_bucket(key, bucket, self._ttl)

            remaining = self.capacity - tokens
            return True, {
                "limit": self.capacity,
                "remaining": max(0, remaining),
                "reset_after": int(self.capacity / self.rate) if self.rate > 0 else 0,
                "retry_after": 0,
            }

        # Calculate tokens to add based on time passed
        elapsed = now - bucket["last_update"]
        tokens_to_add = elapsed * self.rate
        current_tokens = min(self.capacity, bucket["tokens"] + tokens_to_add)

        # Check if we have enough tokens
        if current_tokens >= tokens:
            # Consume tokens
            bucket["tokens"] = current_tokens - tokens
            bucket["last_update"] = now
            await self.backend.set_token_bucket(key, bucket, self._ttl)

            remaining = int(bucket["tokens"])
            return True, {
                "limit": self.capacity,
                "remaining": max(0, remaining),
                "reset_after": int((self.capacity - remaining) / self.rate) if self.rate > 0 else 0,
                "retry_after": 0,
            }

        # Rate limit exceeded
        deficit = tokens - current_tokens
        retry_after = int(deficit / self.rate) if self.rate > 0 else 60

        # Update bucket (no tokens consumed)
        bucket["tokens"] = current_tokens
        bucket["last_update"] = now
        await self.backend.set_token_bucket(key, bucket, self._ttl)

        return False, {
            "limit": self.capacity,
            "remaining": 0,
            "reset_after": int(self.capacity / self.rate) if self.rate > 0 else 0,
            "retry_after": retry_after,
        }

    async def get_rate_limit_info(self, identifier: str) -> dict[str, Any]:
        """Obtém o status atual do rate limit para um identificador.

        Args:
            identifier: Identificador do cliente

        Returns:
            Informação de rate limit sem consumir tokens
        """
        key = self._make_key(identifier)
        now = time.time()

        bucket = await self.backend.get_token_bucket(key)

        if bucket is None:
            return {
                "limit": self.capacity,
                "remaining": self.capacity,
                "reset_after": 0,
                "retry_after": 0,
            }

        # Calculate current tokens
        elapsed = now - bucket["last_update"]
        tokens_to_add = elapsed * self.rate
        current_tokens = min(self.capacity, bucket["tokens"] + tokens_to_add)

        return {
            "limit": self.capacity,
            "remaining": int(current_tokens),
            "reset_after": int((self.capacity - current_tokens) / self.rate) if self.rate > 0 else 0,
            "retry_after": 0,
        }

    async def reset(self, identifier: str) -> None:
        """Reseta o rate limit para um identificador.

        Args:
            identifier: Identificador do cliente para resetar
        """
        key = self._make_key(identifier)
        # Create empty bucket that will expire
        await self.backend.set_token_bucket(key, {"tokens": self.capacity, "last_update": 0}, 1)


# Pre-configured rate limiters for different use cases

class RateLimiters:
    """Container para rate limiters pré-configurados."""

    def __init__(self) -> None:
        """Inicializa rate limiters com backends apropriados."""
        # Choose backend based on Redis availability
        if settings.redis_enabled:
            try:
                self.backend: RateLimiterBackend = RedisRateLimiterBackend()
                logger.info("rate_limiter_using_redis_backend")
            except Exception as e:
                logger.warning("redis_backend_failed", error=str(e))
                self.backend = MemoryRateLimiterBackend()
        else:
            self.backend = MemoryRateLimiterBackend()
            logger.info("rate_limiter_using_memory_backend")

        # General API rate limiter: 60 requests per minute
        self.general = TokenBucketRateLimiter(
            rate=1.0,  # 1 token per second
            capacity=60,  # 60 burst
            backend=self.backend,
            key_prefix="rl:api",
        )

        # Auth-specific rate limiter: 5 requests per minute (brute force protection)
        self.auth = TokenBucketRateLimiter(
            rate=0.083,  # 5 tokens per minute (5/60)
            capacity=5,  # 5 burst
            backend=self.backend,
            key_prefix="rl:auth",
        )

        # Analyze endpoints rate limiter: 60 requests per minute
        self.analyze = TokenBucketRateLimiter(
            rate=1.0,  # 1 token per second
            capacity=60,  # 60 burst
            backend=self.backend,
            key_prefix="rl:analyze",
        )

        # Health check rate limiter: 10 requests per minute
        self.health = TokenBucketRateLimiter(
            rate=0.167,  # 10 tokens per minute (10/60)
            capacity=10,
            backend=self.backend,
            key_prefix="rl:health",
        )


# Global rate limiters instance
_rate_limiters: RateLimiters | None = None


def get_rate_limiters() -> RateLimiters:
    """Obtém ou cria a instância global de rate limiters.

    Returns:
        Instância de RateLimiters
    """
    global _rate_limiters
    if _rate_limiters is None:
        _rate_limiters = RateLimiters()
    return _rate_limiters


def create_rate_limiter(
    requests_per_minute: int = 60,
    burst: int | None = None,
    backend: RateLimiterBackend | None = None,
) -> TokenBucketRateLimiter:
    """Cria um rate limiter customizado.

    Args:
        requests_per_minute: Número de requisições permitidas por minuto
        burst: Capacidade de burst (padrão: requests_per_minute)
        backend: Backend customizado (padrão: memória)

    Returns:
        TokenBucketRateLimiter configurado
    """
    burst = burst or requests_per_minute
    rate = requests_per_minute / 60.0

    return TokenBucketRateLimiter(
        rate=rate,
        capacity=burst,
        backend=backend or MemoryRateLimiterBackend(),
    )


async def check_rate_limit(
    identifier: str,
    limiter_type: str = "general",
) -> tuple[bool, dict[str, Any]]:
    """Verifica o rate limit para um identificador.

    Args:
        identifier: Identificador do cliente (IP, chave de API, etc.)
        limiter_type: Tipo de limiter a usar (general, auth, analyze, health)

    Returns:
        Tupla de (is_allowed, rate_limit_info) onde:
        - is_allowed: True se a requisição pode prosseguir, False se rate limit excedido
        - rate_limit_info: Dict com limit, remaining, reset_after, retry_after
    """
    limiters = get_rate_limiters()

    limiter_map = {
        "general": limiters.general,
        "auth": limiters.auth,
        "analyze": limiters.analyze,
        "health": limiters.health,
    }

    limiter = limiter_map.get(limiter_type, limiters.general)
    return await limiter.is_allowed(identifier)
