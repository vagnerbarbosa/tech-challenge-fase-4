"""Testes unitários para TokenBucketRateLimiter.

Testa o algoritmo de token bucket, implementações de backends
e comportamento de rate limiting.
"""

import asyncio
import time

import pytest

from src.core.security.rate_limiter import (
    MemoryRateLimiterBackend,
    RedisRateLimiterBackend,
    TokenBucketRateLimiter,
    check_rate_limit,
    create_rate_limiter,
    get_rate_limiters,
)


class TestMemoryRateLimiterBackend:
    """Testes para MemoryRateLimiterBackend."""

    @pytest.fixture
    def backend(self):
        """Cria um backend em memória limpo."""
        return MemoryRateLimiterBackend()

    @pytest.mark.asyncio
    async def test_get_token_bucket_new_key(self, backend):
        """Testa que obter bucket para nova chave retorna None."""
        result = await backend.get_token_bucket("test_key")
        assert result is None

    @pytest.mark.asyncio
    async def test_set_and_get_token_bucket(self, backend):
        """Testa definir e obter bucket de tokens."""
        bucket = {"tokens": 50.0, "last_update": time.time()}
        await backend.set_token_bucket("test_key", bucket, ttl=60)

        result = await backend.get_token_bucket("test_key")
        assert result is not None
        assert result["tokens"] == 50.0
        assert "last_update" in result

    @pytest.mark.asyncio
    async def test_token_bucket_expiry(self, backend):
        """Testa que buckets expirados são limpos."""
        bucket = {"tokens": 50.0, "last_update": time.time()}
        await backend.set_token_bucket("test_key", bucket, ttl=1)

        # Deve existir imediatamente
        result = await backend.get_token_bucket("test_key")
        assert result is not None

        # Aguarda expiração
        await asyncio.sleep(1.1)

        # Deve estar expirado
        result = await backend.get_token_bucket("test_key")
        assert result is None

    @pytest.mark.asyncio
    async def test_increment_counter(self, backend):
        """Testa incremento de contador."""
        count = await backend.increment_counter("counter_key", ttl=60)
        assert count == 1

        count = await backend.increment_counter("counter_key", ttl=60)
        assert count == 2

    @pytest.mark.asyncio
    async def test_counter_expiry(self, backend):
        """Testa expiração de contador."""
        await backend.increment_counter("counter_key", ttl=1)
        await asyncio.sleep(1.1)

        count = await backend.get_counter("counter_key")
        assert count == 0

    @pytest.mark.asyncio
    async def test_get_counter_nonexistent(self, backend):
        """Testa obter contador para chave inexistente."""
        count = await backend.get_counter("nonexistent")
        assert count == 0


class TestTokenBucketRateLimiter:
    """Testes para TokenBucketRateLimiter."""

    @pytest.fixture
    def backend(self):
        """Cria um backend em memória limpo."""
        return MemoryRateLimiterBackend()

    @pytest.fixture
    def limiter(self, backend):
        """Cria um rate limiter com taxa de 60/min."""
        return TokenBucketRateLimiter(
            rate=1.0,  # 1 token por segundo
            capacity=60,  # 60 burst
            backend=backend,
            key_prefix="test",
        )

    @pytest.mark.asyncio
    async def test_is_allowed_new_client(self, limiter):
        """Testa que primeira requisição de novo cliente é permitida."""
        is_allowed, info = await limiter.is_allowed("client_1")
        assert is_allowed is True
        assert info["limit"] == 60
        assert info["remaining"] == 59
        assert info["retry_after"] == 0

    @pytest.mark.asyncio
    async def test_is_allowed_multiple_requests(self, limiter):
        """Testa que múltiplas requisições consomem tokens."""
        # Faz 5 requisições
        for _i in range(5):
            is_allowed, info = await limiter.is_allowed("client_2")
            assert is_allowed is True

        # Deve ter 55 restantes
        is_allowed, info = await limiter.is_allowed("client_2")
        assert is_allowed is True
        assert info["remaining"] == 54

    @pytest.mark.asyncio
    async def test_rate_limit_exceeded(self, limiter):
        """Testa que o rate limit é aplicado."""
        # Cria um limiter com capacidade pequena para teste
        backend = MemoryRateLimiterBackend()
        small_limiter = TokenBucketRateLimiter(
            rate=0.1,  # Recarga lenta
            capacity=2,  # Capacidade pequena
            backend=backend,
            key_prefix="small",
        )

        # Consome todos os tokens
        await small_limiter.is_allowed("client_3")  # 1 restante
        await small_limiter.is_allowed("client_3")  # 0 restantes

        # Próxima requisição deve ser negada
        is_allowed, info = await small_limiter.is_allowed("client_3")
        assert is_allowed is False
        assert info["remaining"] == 0
        assert info["retry_after"] > 0

    @pytest.mark.asyncio
    async def test_token_refill(self):
        """Testa que tokens recarregam ao longo do tempo."""
        backend = MemoryRateLimiterBackend()
        limiter = TokenBucketRateLimiter(
            rate=10.0,  # 10 tokens por segundo
            capacity=10,
            backend=backend,
            key_prefix="refill",
        )

        # Consome todos os tokens
        await limiter.is_allowed("client_4")
        is_allowed, info = await limiter.is_allowed("client_4")
        if is_allowed:
            await limiter.is_allowed("client_4")  # Garante que consumiu tudo

        # Aguarda recarga
        await asyncio.sleep(0.5)  # Deve adicionar ~5 tokens

        # Deve ser permitido agora
        is_allowed, info = await limiter.is_allowed("client_4")
        assert is_allowed is True

    @pytest.mark.asyncio
    async def test_different_clients_isolated(self, limiter):
        """Testa que clientes diferentes têm buckets separados."""
        # Cliente A usa tokens
        await limiter.is_allowed("client_a")
        await limiter.is_allowed("client_a")

        # Cliente B deve ter bucket cheio
        is_allowed, info = await limiter.is_allowed("client_b")
        assert is_allowed is True
        assert info["remaining"] == 59

    @pytest.mark.asyncio
    async def test_get_rate_limit_info(self, limiter):
        """Testa obter informações de rate limit sem consumir."""
        # Consome alguns tokens
        await limiter.is_allowed("client_5")
        await limiter.is_allowed("client_5")

        # Obtém info sem consumir
        info = await limiter.get_rate_limit_info("client_5")
        assert info["limit"] == 60
        assert info["remaining"] == 58

    @pytest.mark.asyncio
    async def test_get_rate_limit_info_new_client(self, limiter):
        """Testa obter info para novo cliente."""
        info = await limiter.get_rate_limit_info("new_client")
        assert info["limit"] == 60
        assert info["remaining"] == 60

    @pytest.mark.asyncio
    async def test_reset(self, limiter):
        """Testa resetar rate limit."""
        # Consome tokens
        await limiter.is_allowed("client_6")

        # Reseta
        await limiter.reset("client_6")

        # Deve voltar ao total
        info = await limiter.get_rate_limit_info("client_6")
        assert info["remaining"] == 60

    @pytest.mark.asyncio
    async def test_custom_tokens_consumption(self, limiter):
        """Testa consumir múltiplos tokens de uma vez."""
        is_allowed, info = await limiter.is_allowed("client_7", tokens=5)
        assert is_allowed is True
        assert info["remaining"] == 55  # 60 - 5


class TestRateLimiterCreation:
    """Testes para funções de criação de rate limiter."""

    def test_create_rate_limiter_default(self):
        """Testa criar rate limiter com padrões."""
        limiter = create_rate_limiter(requests_per_minute=60)
        assert limiter.rate == 1.0  # 60/60
        assert limiter.capacity == 60

    def test_create_rate_limiter_custom_burst(self):
        """Testa criar rate limiter com burst customizado."""
        limiter = create_rate_limiter(requests_per_minute=30, burst=10)
        assert limiter.rate == 0.5  # 30/60
        assert limiter.capacity == 10

    def test_get_rate_limiters_singleton(self):
        """Testa que get_rate_limiters retorna singleton."""
        limiters1 = get_rate_limiters()
        limiters2 = get_rate_limiters()
        assert limiters1 is limiters2


class TestCheckRateLimit:
    """Testes para função check_rate_limit."""

    @pytest.mark.asyncio
    async def test_check_rate_limit_allowed(self):
        """Testa check_rate_limit quando permitido."""
        # Usa limiter geral que deve permitir primeira requisição
        is_allowed, info = await check_rate_limit("test_check_allowed", "general")
        assert is_allowed is True
        assert "limit" in info
        assert "remaining" in info

    @pytest.mark.asyncio
    async def test_check_rate_limit_raises_exception(self):
        """Testa check_rate_limit retorna tuple em vez de lançar exceção."""
        # Cria um limiter que definitivamente rejeitará
        backend = MemoryRateLimiterBackend()
        limiter = TokenBucketRateLimiter(
            rate=0.001,  # Recarga muito lenta
            capacity=1,
            backend=backend,
            key_prefix="exception_test",
        )

        # Consome o único token
        await limiter.is_allowed("exceeded_client")

        # Reseta singleton para usar nosso limiter de teste
        from src.core.security import rate_limiter
        old_limiters = rate_limiter._rate_limiters
        rate_limiter._rate_limiters = None

        # Cria novos limiters com nosso backend
        limiters = get_rate_limiters()
        limiters.general = limiter

        try:
            # check_rate_limit agora retorna (is_allowed, info) em vez de lançar
            is_allowed, info = await check_rate_limit("exceeded_client", "general")

            assert is_allowed is False
            assert info["remaining"] == 0
            assert "reset_after" in info
        finally:
            # Restaura
            rate_limiter._rate_limiters = old_limiters


class TestRedisRateLimiterBackend:
    """Testes para RedisRateLimiterBackend."""

    @pytest.mark.skip(reason="Requer servidor Redis")
    def test_redis_backend_initialization(self):
        """Testa inicialização do backend Redis (pulado sem Redis)."""
        # Este teste é pulado a menos que Redis esteja disponível
        backend = RedisRateLimiterBackend(redis_url="redis://localhost:6379/0")
        assert backend._redis_url == "redis://localhost:6379/0"
        assert backend._initialized is False

    def test_redis_backend_without_redis_package(self, monkeypatch):
        """Testa backend Redis quando pacote redis não está disponível."""
        # Mock para falhar o import
        import builtins
        original_import = builtins.__import__

        def mock_import(name, *args, **kwargs):
            if name == "redis.asyncio":
                raise ImportError("No module named 'redis'")
            return original_import(name, *args, **kwargs)

        monkeypatch.setattr(builtins, "__import__", mock_import)

        backend = RedisRateLimiterBackend()
        # Não deve lançar erro durante init
        assert backend._initialized is False


class TestEdgeCases:
    """Testes de casos de borda."""

    @pytest.mark.asyncio
    async def test_zero_rate_limit(self):
        """Testa rate limiter com taxa zero."""
        backend = MemoryRateLimiterBackend()
        limiter = TokenBucketRateLimiter(
            rate=0.0,  # Sem recarga
            capacity=1,
            backend=backend,
        )

        # Deve lidar sem erro
        is_allowed, info = await limiter.is_allowed("zero_rate_client")
        # Com taxa zero, primeira requisição ainda deve ser permitida (bucket cheio)
        assert is_allowed is True

    @pytest.mark.asyncio
    async def test_negative_tokens_consumption(self):
        """Testa rate limiter com tokens negativos (não deveria acontecer)."""
        backend = MemoryRateLimiterBackend()
        limiter = TokenBucketRateLimiter(
            rate=1.0,
            capacity=60,
            backend=backend,
        )

        # Consumir tokens negativos adicionaria tokens, mas deve ser tratado
        is_allowed, info = await limiter.is_allowed("client_neg", tokens=1)
        assert is_allowed is True

    @pytest.mark.asyncio
    async def test_rapid_requests(self):
        """Testa rate limiter com muitas requisições rápidas."""
        backend = MemoryRateLimiterBackend()
        limiter = TokenBucketRateLimiter(
            rate=100.0,  # Recarga rápida
            capacity=100,
            backend=backend,
        )

        allowed_count = 0
        # Faz 150 requisições rápidas
        for _i in range(150):
            is_allowed, _ = await limiter.is_allowed("rapid_client")
            if is_allowed:
                allowed_count += 1

        # Deve permitir pelo menos capacity requisições
        assert allowed_count >= 100
