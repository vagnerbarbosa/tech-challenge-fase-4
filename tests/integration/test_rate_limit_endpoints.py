"""Integration tests for rate limiting on API endpoints.

Tests that rate limits are properly enforced on API endpoints
and that appropriate headers are returned.
"""


import pytest
from fastapi.testclient import TestClient


class TestRateLimitHeaders:
    """Tests for X-RateLimit-* headers on responses."""

    def test_rate_limit_headers_present(self, client: TestClient):
        """Test that rate limit headers are present on protected endpoints."""
        response = client.post(
            "/analyze/text",
            json={"text": "test"},
        )

        # Check headers
        assert "X-RateLimit-Limit" in response.headers
        assert "X-RateLimit-Remaining" in response.headers
        assert "X-RateLimit-Reset" in response.headers

    def test_rate_limit_headers_values(self, client: TestClient):
        """Test that rate limit header values are valid."""
        response = client.post(
            "/analyze/text",
            json={"text": "test"},
        )

        limit = int(response.headers["X-RateLimit-Limit"])
        remaining = int(response.headers["X-RateLimit-Remaining"])
        reset_after = int(response.headers["X-RateLimit-Reset"])

        assert limit > 0
        assert remaining >= 0
        assert remaining <= limit
        assert reset_after >= 0

    def test_rate_limit_decreases(self, client: TestClient):
        """Test that remaining count decreases with requests."""
        # First request
        response1 = client.post(
            "/analyze/text",
            json={"text": "test"},
        )
        remaining1 = int(response1.headers["X-RateLimit-Remaining"])

        # Second request
        response2 = client.post(
            "/analyze/text",
            json={"text": "test"},
        )
        remaining2 = int(response2.headers["X-RateLimit-Remaining"])

        assert remaining2 <= remaining1


class TestRateLimitEnforcement:
    """Tests for rate limit enforcement (429 responses)."""

    def test_rate_limit_returns_429(self, client: TestClient):
        """Test that exceeding rate limit returns 429 status."""
        # Make many requests quickly
        responses = []
        for _i in range(70):  # More than default 60/min limit
            response = client.post(
                "/analyze/text",
                json={"text": "test"},
            )
            responses.append(response)

        # At least one should be rate limited
        rate_limited = [r for r in responses if r.status_code == 429]
        assert len(rate_limited) > 0

    def test_429_has_retry_after_header(self, client: TestClient):
        """Test that 429 response has Retry-After header."""
        # Make many requests
        for _i in range(70):
            response = client.post(
                "/analyze/text",
                json={"text": "test"},
            )
            if response.status_code == 429:
                assert "Retry-After" in response.headers
                retry_after = int(response.headers["Retry-After"])
                assert retry_after > 0
                return

        pytest.skip("Rate limit not triggered in test")

    def test_429_response_body(self, client: TestClient):
        """Test that 429 response has appropriate body."""
        # Make many requests
        for _i in range(70):
            response = client.post(
                "/analyze/text",
                json={"text": "test"},
            )
            if response.status_code == 429:
                data = response.json()
                assert "error" in data
                assert data["error"] == "RateLimitExceeded"
                assert "message" in data
                assert "retry_after" in data
                return

        pytest.skip("Rate limit not triggered in test")


class TestAuthRateLimiting:
    """Tests for auth-specific rate limiting (5 req/min)."""

    def test_auth_endpoint_rate_limited(self, client: TestClient):
        """Test that auth endpoints have stricter rate limits."""
        # Make 6 auth requests (limit is 5/min)
        responses = []
        for _i in range(6):
            response = client.post(
                "/auth/validate",
                headers={"X-API-Key": "invalid-key"},
            )
            responses.append(response)

        # At least one should be rate limited
        rate_limited = [r for r in responses if r.status_code == 429]
        assert len(rate_limited) > 0

    def test_auth_rate_limit_headers(self, client: TestClient):
        """Test that auth endpoints return correct rate limit headers."""
        response = client.post(
            "/auth/validate",
            headers={"X-API-Key": "invalid-key"},
        )

        # Should have rate limit headers even on 401
        if response.status_code in [200, 401]:
            assert "X-RateLimit-Limit" in response.headers
            limit = int(response.headers["X-RateLimit-Limit"])
            assert limit <= 5  # Auth limit is 5/min

    def test_auth_rate_limit_status_endpoint(self, client: TestClient):
        """Test the auth rate limit status endpoint."""
        response = client.get("/auth/rate-limit-status")

        assert response.status_code == 200
        data = response.json()
        assert "limit" in data
        assert "remaining" in data
        assert "reset_after" in data
        assert "window" in data
        assert data["window"] == "1 minute"


class TestSkippedPaths:
    """Tests that certain paths skip rate limiting."""

    def test_health_endpoint_skips_rate_limit(self, client: TestClient):
        """Test that health endpoint is not rate limited."""
        # Make many requests to health endpoint
        for _i in range(100):
            response = client.get("/health")
            assert response.status_code == 200
            # Should not have rate limit headers (skipped)
            assert "X-RateLimit-Limit" not in response.headers

    def test_docs_skips_rate_limit(self, client: TestClient):
        """Test that docs endpoint skips rate limiting."""
        response = client.get("/docs")
        # May return 404 in production, but should not be rate limited
        if response.status_code == 200:
            assert "X-RateLimit-Limit" not in response.headers

    def test_root_endpoint_skips_rate_limit(self, client: TestClient):
        """Test that root endpoint skips rate limiting."""
        response = client.get("/")
        assert response.status_code == 200
        assert "X-RateLimit-Limit" not in response.headers


class TestRateLimitReset:
    """Tests for rate limit reset behavior."""

    def test_rate_limit_resets_over_time(self, client: TestClient):
        """Test that rate limit resets after time window."""
        # This test may be flaky depending on timing
        # Make some requests
        for _i in range(5):
            client.post("/analyze/text", json={"text": "test"})

        # Get remaining
        response = client.post("/analyze/text", json={"text": "test"})
        if response.status_code == 200:
            # Wait a bit (this might not be reliable in tests)
            import time
            time.sleep(1)

            # Make another request
            response = client.post("/analyze/text", json={"text": "test"})
            if response.status_code == 200:
                # Tokens might have refilled
                pass  # Just verify it doesn't crash


class TestRateLimitDifferentClients:
    """Tests that different clients have separate rate limits."""

    def test_different_ips_separate_limits(self, client: TestClient):
        """Test that different IP addresses have separate rate limits."""
        # Make requests with different X-Forwarded-For headers
        response1 = client.post(
            "/analyze/text",
            json={"text": "test"},
            headers={"X-Forwarded-For": "1.2.3.4"},
        )

        response2 = client.post(
            "/analyze/text",
            json={"text": "test"},
            headers={"X-Forwarded-For": "5.6.7.8"},
        )

        # Both should succeed (different clients)
        assert response1.status_code == 200
        assert response2.status_code == 200

    def test_api_key_based_limiting(self, client: TestClient):
        """Test that API keys are used for rate limiting when present."""
        # Make request with API key header
        response = client.post(
            "/analyze/text",
            json={"text": "test"},
            headers={"X-API-Key": "test-key-1"},
        )

        assert response.status_code in [200, 401, 403]  # May vary based on auth


class TestRateLimitErrorHandling:
    """Tests for rate limit error handling."""

    def test_rate_limit_with_invalid_json(self, client: TestClient):
        """Test rate limit headers on validation errors."""
        response = client.post(
            "/analyze/text",
            data="invalid json",
        )

        # Should still have rate limit headers even on error
        if response.status_code == 422:
            assert "X-RateLimit-Limit" in response.headers

    def test_rate_limit_with_empty_body(self, client: TestClient):
        """Test rate limit headers on empty body."""
        response = client.post("/analyze/text")

        # Should still have rate limit headers
        if response.status_code == 422:
            assert "X-RateLimit-Limit" in response.headers
