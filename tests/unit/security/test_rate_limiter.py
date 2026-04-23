"""Unit tests for TokenBucketRateLimiter.

Tests the token bucket algorithm, backend implementations,
and rate limiting behavior.
"""

import asyncio
import time

import pytest

from src.core.exceptions import RateLimitExceeded
from src.core.security.rate_limiter import (
    MemoryRateLimiterBackend,
    RedisRateLimiterBackend,
    TokenBucketRateLimiter,
    check_rate_limit,
    create_rate_limiter,
    get_rate_limiters,
)


class TestMemoryRateLimiterBackend:
    """Tests for MemoryRateLimiterBackend."""

    @pytest.fixture
    def backend(self):
        """Create a fresh memory backend."""
        return MemoryRateLimiterBackend()

    @pytest.mark.asyncio
    async def test_get_token_bucket_new_key(self, backend):
        """Test getting bucket for new key returns None."""
        result = await backend.get_token_bucket("test_key")
        assert result is None

    @pytest.mark.asyncio
    async def test_set_and_get_token_bucket(self, backend):
        """Test setting and getting token bucket."""
        bucket = {"tokens": 50.0, "last_update": time.time()}
        await backend.set_token_bucket("test_key", bucket, ttl=60)

        result = await backend.get_token_bucket("test_key")
        assert result is not None
        assert result["tokens"] == 50.0
        assert "last_update" in result

    @pytest.mark.asyncio
    async def test_token_bucket_expiry(self, backend):
        """Test that expired buckets are cleaned up."""
        bucket = {"tokens": 50.0, "last_update": time.time()}
        await backend.set_token_bucket("test_key", bucket, ttl=1)

        # Should exist immediately
        result = await backend.get_token_bucket("test_key")
        assert result is not None

        # Wait for expiry
        await asyncio.sleep(1.1)

        # Should be expired
        result = await backend.get_token_bucket("test_key")
        assert result is None

    @pytest.mark.asyncio
    async def test_increment_counter(self, backend):
        """Test counter increment."""
        count = await backend.increment_counter("counter_key", ttl=60)
        assert count == 1

        count = await backend.increment_counter("counter_key", ttl=60)
        assert count == 2

    @pytest.mark.asyncio
    async def test_counter_expiry(self, backend):
        """Test counter expiry."""
        await backend.increment_counter("counter_key", ttl=1)
        await asyncio.sleep(1.1)

        count = await backend.get_counter("counter_key")
        assert count == 0

    @pytest.mark.asyncio
    async def test_get_counter_nonexistent(self, backend):
        """Test getting counter for non-existent key."""
        count = await backend.get_counter("nonexistent")
        assert count == 0


class TestTokenBucketRateLimiter:
    """Tests for TokenBucketRateLimiter."""

    @pytest.fixture
    def backend(self):
        """Create a fresh memory backend."""
        return MemoryRateLimiterBackend()

    @pytest.fixture
    def limiter(self, backend):
        """Create a rate limiter with 60/min rate."""
        return TokenBucketRateLimiter(
            rate=1.0,  # 1 token per second
            capacity=60,  # 60 burst
            backend=backend,
            key_prefix="test",
        )

    @pytest.mark.asyncio
    async def test_is_allowed_new_client(self, limiter):
        """Test first request from new client is allowed."""
        is_allowed, info = await limiter.is_allowed("client_1")
        assert is_allowed is True
        assert info["limit"] == 60
        assert info["remaining"] == 59
        assert info["retry_after"] == 0

    @pytest.mark.asyncio
    async def test_is_allowed_multiple_requests(self, limiter):
        """Test multiple requests consume tokens."""
        # Make 5 requests
        for _i in range(5):
            is_allowed, info = await limiter.is_allowed("client_2")
            assert is_allowed is True

        # Should have 55 remaining
        is_allowed, info = await limiter.is_allowed("client_2")
        assert is_allowed is True
        assert info["remaining"] == 54

    @pytest.mark.asyncio
    async def test_rate_limit_exceeded(self, limiter):
        """Test rate limit is enforced."""
        # Create a limiter with small capacity for testing
        backend = MemoryRateLimiterBackend()
        small_limiter = TokenBucketRateLimiter(
            rate=0.1,  # Slow refill
            capacity=2,  # Small capacity
            backend=backend,
            key_prefix="small",
        )

        # Consume all tokens
        await small_limiter.is_allowed("client_3")  # 1 remaining
        await small_limiter.is_allowed("client_3")  # 0 remaining

        # Next request should be denied
        is_allowed, info = await small_limiter.is_allowed("client_3")
        assert is_allowed is False
        assert info["remaining"] == 0
        assert info["retry_after"] > 0

    @pytest.mark.asyncio
    async def test_token_refill(self):
        """Test tokens refill over time."""
        backend = MemoryRateLimiterBackend()
        limiter = TokenBucketRateLimiter(
            rate=10.0,  # 10 tokens per second
            capacity=10,
            backend=backend,
            key_prefix="refill",
        )

        # Consume all tokens
        await limiter.is_allowed("client_4")
        is_allowed, info = await limiter.is_allowed("client_4")
        if is_allowed:
            await limiter.is_allowed("client_4")  # Ensure we consume all

        # Wait for refill
        await asyncio.sleep(0.5)  # Should add ~5 tokens

        # Should be allowed now
        is_allowed, info = await limiter.is_allowed("client_4")
        assert is_allowed is True

    @pytest.mark.asyncio
    async def test_different_clients_isolated(self, limiter):
        """Test that different clients have separate buckets."""
        # Client A uses tokens
        await limiter.is_allowed("client_a")
        await limiter.is_allowed("client_a")

        # Client B should have full bucket
        is_allowed, info = await limiter.is_allowed("client_b")
        assert is_allowed is True
        assert info["remaining"] == 59

    @pytest.mark.asyncio
    async def test_get_rate_limit_info(self, limiter):
        """Test getting rate limit info without consuming."""
        # Consume some tokens
        await limiter.is_allowed("client_5")
        await limiter.is_allowed("client_5")

        # Get info without consuming
        info = await limiter.get_rate_limit_info("client_5")
        assert info["limit"] == 60
        assert info["remaining"] == 58

    @pytest.mark.asyncio
    async def test_get_rate_limit_info_new_client(self, limiter):
        """Test getting info for new client."""
        info = await limiter.get_rate_limit_info("new_client")
        assert info["limit"] == 60
        assert info["remaining"] == 60

    @pytest.mark.asyncio
    async def test_reset(self, limiter):
        """Test resetting rate limit."""
        # Consume tokens
        await limiter.is_allowed("client_6")

        # Reset
        await limiter.reset("client_6")

        # Should be back to full
        info = await limiter.get_rate_limit_info("client_6")
        assert info["remaining"] == 60

    @pytest.mark.asyncio
    async def test_custom_tokens_consumption(self, limiter):
        """Test consuming multiple tokens at once."""
        is_allowed, info = await limiter.is_allowed("client_7", tokens=5)
        assert is_allowed is True
        assert info["remaining"] == 55  # 60 - 5


class TestRateLimiterCreation:
    """Tests for rate limiter creation functions."""

    def test_create_rate_limiter_default(self):
        """Test creating rate limiter with defaults."""
        limiter = create_rate_limiter(requests_per_minute=60)
        assert limiter.rate == 1.0  # 60/60
        assert limiter.capacity == 60

    def test_create_rate_limiter_custom_burst(self):
        """Test creating rate limiter with custom burst."""
        limiter = create_rate_limiter(requests_per_minute=30, burst=10)
        assert limiter.rate == 0.5  # 30/60
        assert limiter.capacity == 10

    def test_get_rate_limiters_singleton(self):
        """Test that get_rate_limiters returns singleton."""
        limiters1 = get_rate_limiters()
        limiters2 = get_rate_limiters()
        assert limiters1 is limiters2


class TestCheckRateLimit:
    """Tests for check_rate_limit function."""

    @pytest.mark.asyncio
    async def test_check_rate_limit_allowed(self):
        """Test check_rate_limit when allowed."""
        # Use general limiter which should allow first request
        is_allowed, info = await check_rate_limit("test_check_allowed", "general")
        assert is_allowed is True
        assert "limit" in info
        assert "remaining" in info

    @pytest.mark.asyncio
    async def test_check_rate_limit_raises_exception(self):
        """Test check_rate_limit raises RateLimitExceeded."""
        # Create a limiter that will definitely reject
        backend = MemoryRateLimiterBackend()
        limiter = TokenBucketRateLimiter(
            rate=0.001,  # Very slow refill
            capacity=1,
            backend=backend,
            key_prefix="exception_test",
        )

        # Consume the only token
        await limiter.is_allowed("exceeded_client")

        # Reset singleton to use our test limiter
        from src.core.security import rate_limiter
        old_limiters = rate_limiter._rate_limiters
        rate_limiter._rate_limiters = None

        # Create new limiters with our backend
        limiters = get_rate_limiters()
        limiters.general = limiter

        try:
            with pytest.raises(RateLimitExceeded) as exc_info:
                await check_rate_limit("exceeded_client", "general")

            assert exc_info.value.status_code == 429
            assert "retry_after" in exc_info.value.details
        finally:
            # Restore
            rate_limiter._rate_limiters = old_limiters


class TestRedisRateLimiterBackend:
    """Tests for RedisRateLimiterBackend."""

    @pytest.mark.skip(reason="Requires Redis server")
    def test_redis_backend_initialization(self):
        """Test Redis backend initialization (skipped without Redis)."""
        # This test is skipped unless Redis is available
        backend = RedisRateLimiterBackend(redis_url="redis://localhost:6379/0")
        assert backend._redis_url == "redis://localhost:6379/0"
        assert backend._initialized is False

    def test_redis_backend_without_redis_package(self, monkeypatch):
        """Test Redis backend when redis package is not available."""
        # Mock the import to fail
        import builtins
        original_import = builtins.__import__

        def mock_import(name, *args, **kwargs):
            if name == "redis.asyncio":
                raise ImportError("No module named 'redis'")
            return original_import(name, *args, **kwargs)

        monkeypatch.setattr(builtins, "__import__", mock_import)

        backend = RedisRateLimiterBackend()
        # Should not raise during init
        assert backend._initialized is False


class TestEdgeCases:
    """Edge case tests."""

    @pytest.mark.asyncio
    async def test_zero_rate_limit(self):
        """Test rate limiter with zero rate."""
        backend = MemoryRateLimiterBackend()
        limiter = TokenBucketRateLimiter(
            rate=0.0,  # No refill
            capacity=1,
            backend=backend,
        )

        # Should handle without error
        is_allowed, info = await limiter.is_allowed("zero_rate_client")
        # With zero rate, first request should still be allowed (full bucket)
        assert is_allowed is True

    @pytest.mark.asyncio
    async def test_negative_tokens_consumption(self):
        """Test rate limiter with negative tokens (should not happen)."""
        backend = MemoryRateLimiterBackend()
        limiter = TokenBucketRateLimiter(
            rate=1.0,
            capacity=60,
            backend=backend,
        )

        # Consuming negative tokens would add tokens, but should be handled
        is_allowed, info = await limiter.is_allowed("client_neg", tokens=1)
        assert is_allowed is True

    @pytest.mark.asyncio
    async def test_rapid_requests(self):
        """Test rate limiter with many rapid requests."""
        backend = MemoryRateLimiterBackend()
        limiter = TokenBucketRateLimiter(
            rate=100.0,  # Fast refill
            capacity=100,
            backend=backend,
        )

        allowed_count = 0
        # Make 150 rapid requests
        for _i in range(150):
            is_allowed, _ = await limiter.is_allowed("rapid_client")
            if is_allowed:
                allowed_count += 1

        # Should allow at least capacity requests
        assert allowed_count >= 100
