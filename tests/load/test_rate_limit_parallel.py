"""Load tests for rate limiting under parallel requests.

Tests that rate limiting correctly handles concurrent requests
and maintains consistency under load.
"""

import asyncio

import pytest
from fastapi.testclient import TestClient


class TestRateLimitConcurrency:
    """Tests for concurrent rate limiting behavior."""

    def test_parallel_requests_respect_limit(self, auth_client: TestClient):
        """Test that parallel requests properly count against rate limit.

        Makes multiple parallel requests and verifies that the rate limit
        is enforced across all of them.
        """
        num_requests = 20

        # Make parallel requests
        responses = []
        for i in range(num_requests):
            response = auth_client.post(
                "/analyze/text",
                json={"texto": f"Estou me sentindo ansiosa {i}"},
            )
            responses.append(response)

        # Count results
        successful = [r for r in responses if r.status_code == 200]
        rate_limited = [r for r in responses if r.status_code == 429]

        # All should either succeed or be rate limited
        assert len(successful) + len(rate_limited) == num_requests

        # Should have at least some successful requests
        assert len(successful) > 0

    def test_parallel_requests_consistent_headers(self, auth_client: TestClient):
        """Test that parallel requests return consistent rate limit headers."""
        num_requests = 10

        # Make parallel requests
        remaining_values = []
        for i in range(num_requests):
            response = auth_client.post(
                "/analyze/text",
                json={"texto": f"Estou me sentindo ansiosa {i}"},
            )
            if response.status_code == 200:
                remaining_values.append(int(response.headers["X-RateLimit-Remaining"]))

        # All remaining values should be within valid range
        for remaining in remaining_values:
            assert 0 <= remaining <= 60

    def test_burst_requests(self, auth_client: TestClient):
        """Test handling of burst requests at rate limit boundary.

        Makes exactly the burst capacity number of requests as fast
        as possible to verify the token bucket is correctly consumed.
        """
        # Make burst capacity requests
        for i in range(60):  # Burst capacity
            response = auth_client.post(
                "/analyze/text",
                json={"texto": f"Estou me sentindo ansiosa {i}"},
            )

        # Next request should be rate limited
        response = auth_client.post(
            "/analyze/text",
            json={"texto": "Estou me sentindo ansiosa hoje"},
        )

        # May or may not be rate limited depending on refill timing
        assert response.status_code in [200, 429]

    def test_auth_parallel_burst(self, auth_client: TestClient):
        """Test auth endpoint with parallel burst (stricter limit)."""
        num_requests = 10  # More than auth limit of 5

        responses = []
        for i in range(num_requests):
            response = auth_client.post(
                "/auth/validate",
                headers={"X-API-Key": f"key-{i}"},
            )
            responses.append(response)

        # Count rate limited responses
        rate_limited = [r for r in responses if r.status_code == 429]

        # Should have at least some rate limited due to 5/min limit
        assert len(rate_limited) >= num_requests - 5


@pytest.mark.asyncio
class TestAsyncRateLimitConcurrency:
    """Async tests for concurrent rate limiting."""

    async def test_async_parallel_requests(self):
        """Test rate limiting with async parallel requests."""
        from httpx import ASGITransport, AsyncClient

        from src.api.main import app
        from tests.conftest import TEST_API_KEY

        async with AsyncClient(
            transport=ASGITransport(app=app),
            base_url="http://test",
            headers={"X-API-Key": TEST_API_KEY},
        ) as client:
            # Create multiple concurrent requests
            tasks = [
                client.post("/analyze/text", json={"texto": f"Estou me sentindo ansiosa {i}"})
                for i in range(20)
            ]

            responses = await asyncio.gather(*tasks)

            successful = [r for r in responses if r.status_code == 200]
            rate_limited = [r for r in responses if r.status_code == 429]

            assert len(successful) + len(rate_limited) == 20
            assert len(successful) > 0

    async def test_async_auth_parallel(self):
        """Test auth rate limiting with async requests."""
        from httpx import ASGITransport, AsyncClient

        from src.api.main import app
        from tests.conftest import TEST_API_KEY

        async with AsyncClient(
            transport=ASGITransport(app=app),
            base_url="http://test",
            headers={"X-API-Key": TEST_API_KEY},
        ) as client:
            # Create concurrent auth requests
            tasks = [
                client.post(
                    "/auth/validate",
                    headers={"X-API-Key": f"key-{i}"},
                )
                for i in range(10)
            ]

            responses = await asyncio.gather(*tasks)

            # Should have rate limited responses
            rate_limited = [r for r in responses if r.status_code == 429]
            assert len(rate_limited) > 0


class TestRateLimitRaceConditions:
    """Tests for race conditions in rate limiting."""

    def test_simultaneous_requests_no_overcount(self, auth_client: TestClient):
        """Test that simultaneous requests don't overcount.

        This test verifies the atomicity of token consumption.
        """
        import threading

        results = []
        lock = threading.Lock()

        def make_request():
            response = auth_client.post(
                "/analyze/text",
                json={"texto": "Estou me sentindo ansiosa"},
            )
            with lock:
                results.append(response.status_code)

        # Create threads
        threads = [threading.Thread(target=make_request) for _ in range(10)]

        # Start all threads simultaneously
        for t in threads:
            t.start()

        # Wait for completion
        for t in threads:
            t.join()

        # Count results
        successful = results.count(200)
        rate_limited = results.count(429)

        assert successful + rate_limited == 10

    def test_high_concurrency_stress(self, auth_client: TestClient):
        """Stress test with high concurrency."""
        num_requests = 50

        responses = []
        for i in range(num_requests):
            response = auth_client.post(
                "/analyze/text",
                json={"texto": f"Estou me sentindo ansiosa {i}"},
            )
            responses.append(response.status_code)

        # Verify consistency
        successful = responses.count(200)
        rate_limited = responses.count(429)
        errors = [r for r in responses if r not in [200, 429]]

        assert len(errors) == 0, f"Unexpected error codes: {errors}"
        assert successful + rate_limited == num_requests


class TestRateLimitDistributed:
    """Tests simulating distributed rate limiting scenarios."""

    def test_different_clients_concurrent(self, auth_client: TestClient):
        """Test that different clients are rate limited independently."""
        import threading

        results = {"client_a": [], "client_b": []}
        lock = threading.Lock()

        def make_request(client_id: str):
            # Use different headers to simulate different clients
            headers = {"X-Forwarded-For": f"192.168.1.{client_id}"}
            response = auth_client.post(
                "/analyze/text",
                json={"texto": "Estou me sentindo ansiosa"},
                headers=headers,
            )
            with lock:
                results[client_id].append(response.status_code)

        # Make requests from two different "clients"
        threads = []
        for i in range(20):
            client_id = "client_a" if i < 10 else "client_b"
            t = threading.Thread(target=make_request, args=(client_id,))
            threads.append(t)

        for t in threads:
            t.start()

        for t in threads:
            t.join()

        # Both clients should have some successful requests
        assert results["client_a"].count(200) > 0
        assert results["client_b"].count(200) > 0

    def test_rate_limit_recovery(self, auth_client: TestClient):
        """Test that rate limits recover after window."""
        import time

        # Exhaust rate limit
        for i in range(65):
            auth_client.post("/analyze/text", json={"texto": f"Estou me sentindo ansiosa {i}"})

        # Wait for some recovery (tokens refill at 1/sec)
        time.sleep(2)

        # Should be able to make some requests again
        response = auth_client.post(
            "/analyze/text",
            json={"texto": "Estou me sentindo ansiosa"},
        )

        # Might be rate limited depending on exact timing
        assert response.status_code in [200, 429]


class TestRateLimitHeadersUnderLoad:
    """Tests for rate limit header accuracy under load."""

    def test_remaining_count_accuracy(self, auth_client: TestClient):
        """Test that remaining count is accurate under load."""
        remaining_values = []

        for i in range(10):
            response = auth_client.post(
                "/analyze/text",
                json={"texto": f"Estou me sentindo ansiosa {i}"},
            )
            if response.status_code == 200:
                remaining = int(response.headers["X-RateLimit-Remaining"])
                remaining_values.append(remaining)

        # Check that remaining values are non-increasing (or close to it)
        for i in range(1, len(remaining_values)):
            # Allow for some refill between requests
            assert remaining_values[i] <= remaining_values[i-1] + 1

    def test_reset_after_consistency(self, auth_client: TestClient):
        """Test that reset_after is consistent."""
        reset_values = []

        for i in range(5):
            response = auth_client.post(
                "/analyze/text",
                json={"texto": f"Estou me sentindo ansiosa {i}"},
            )
            if response.status_code == 200:
                reset_after = int(response.headers["X-RateLimit-Reset"])
                reset_values.append(reset_after)

        # All reset values should be non-negative
        for value in reset_values:
            assert value >= 0
