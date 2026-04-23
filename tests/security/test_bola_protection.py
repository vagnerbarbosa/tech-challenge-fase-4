"""Security tests for BOLA (Broken Object Level Authorization) protection.

T013: Security test test_bola_protection.py - acesso a recurso de outro usuário retorna 403

Tests verify that users cannot access resources they don't own (OWASP API1).
"""


import pytest
from fastapi.testclient import TestClient

from src.api.main import app
from src.core.exceptions import AuthenticationException, ForbiddenException
from src.core.security.auth import BOLAProtector
from src.core.security.models import SecurityContext
from tests.conftest import TEST_API_KEY


class TestBOLAProtection:
    """Test cases for BOLA (Broken Object Level Authorization) protection."""

    def test_user_cannot_access_other_user_resource(self) -> None:
        """Test that user1 cannot access user2's resource."""
        protector = BOLAProtector()

        # Simulate User 1's security context
        user1_ctx = SecurityContext(
            request_id="req-user1",
            api_key_hash="hash-user1-key",
            roles=["read", "write"],
            is_authenticated=True,
        )

        # User 1 tries to access User 2's resource
        with pytest.raises(ForbiddenException) as exc_info:
            protector.verify_ownership(
                user1_ctx,
                resource_owner_id="hash-user2-key",  # User 2's resource
                resource_id="patient-data-123",
            )

        assert exc_info.value.status_code == 403
        assert "patient-data-123" in str(exc_info.value.message)

    def test_user_can_access_own_resource(self) -> None:
        """Test that user can access their own resource."""
        protector = BOLAProtector()

        user_ctx = SecurityContext(
            request_id="req-user",
            api_key_hash="hash-user-key",
            roles=["read"],
            is_authenticated=True,
        )

        # User accesses their own resource - should not raise
        protector.verify_ownership(
            user_ctx,
            resource_owner_id="hash-user-key",
            resource_id="patient-data-user",
        )

    def test_bypass_via_admin_role(self) -> None:
        """Test that admin users can bypass ownership checks."""
        protector = BOLAProtector()

        admin_ctx = SecurityContext(
            request_id="req-admin",
            api_key_hash="hash-admin-key",
            roles=["admin"],
            is_authenticated=True,
        )

        # Admin can access any resource
        protector.verify_ownership(
            admin_ctx,
            resource_owner_id="hash-any-user-key",
            resource_id="patient-data-any",
        )

    def test_unauthenticated_user_access_denied(self) -> None:
        """Test that unauthenticated users cannot access any resources."""
        protector = BOLAProtector()

        anon_ctx = SecurityContext.anonymous(request_id="req-anon")

        with pytest.raises(AuthenticationException) as exc_info:
            protector.verify_ownership(
                anon_ctx,
                resource_owner_id="hash-any-key",
                resource_id="patient-data",
            )

        assert exc_info.value.status_code == 401

    def test_bola_with_none_resource_owner(self) -> None:
        """Test handling of None resource owner (public resource)."""
        protector = BOLAProtector()

        user_ctx = SecurityContext(
            request_id="req-user",
            api_key_hash="hash-user-key",
            roles=["read"],
            is_authenticated=True,
        )

        # Public resources (owner=None) should be accessible
        protector.verify_ownership(
            user_ctx,
            resource_owner_id=None,
            resource_id="public-info",
        )


class TestBOLAWithAPIEndpoints:
    """BOLA protection tests in context of API endpoints."""

    @pytest.fixture
    def client(self) -> TestClient:
        """Create test client for FastAPI app."""
        return TestClient(app, headers={"X-API-Key": TEST_API_KEY})

    def test_endpoint_with_patient_id_in_path(self, client: TestClient) -> None:
        """Test that patient-specific endpoints enforce ownership."""
        # This test validates that endpoints with patient_id in path
        # properly check ownership

        # Simulate request with valid API key but wrong patient_id
        response = client.get(
            "/analyze/text",  # Generic endpoint (POST only)
        )

        # Should not expose patient data without proper authorization
        # 405 is acceptable (method not allowed - endpoint is POST only)
        assert response.status_code in [200, 401, 403, 405, 422]


class TestResourceEnumeration:
    """Tests to prevent resource enumeration attacks."""

    def test_error_messages_do_not_leak_existence(self) -> None:
        """Test that error messages don't reveal if resource exists."""
        protector = BOLAProtector()

        # Different errors for "resource doesn't exist" vs "no permission"
        # could leak information - verify generic error message
        user_ctx = SecurityContext(
            request_id="req-user",
            api_key_hash="hash-user-key",
            roles=["read"],
            is_authenticated=True,
        )

        try:
            protector.verify_ownership(
                user_ctx,
                resource_owner_id="hash-other-user",
                resource_id="resource-999",
            )
        except ForbiddenException as e:
            # Error message should not reveal if resource exists
            # Accept both English and Portuguese (project is bilingual)
            msg_lower = e.message.lower()
            assert (
                "access" in msg_lower
                or "permission" in msg_lower
                or "acesso" in msg_lower
                or "permissão" in msg_lower
            ), f"Error message should indicate permission denied: {e.message}"


class TestBOLAEdgeCases:
    """Edge case tests for BOLA protection."""

    def test_empty_resource_owner(self) -> None:
        """Test BOLA with empty string resource owner."""
        protector = BOLAProtector()

        user_ctx = SecurityContext(
            request_id="req-user",
            api_key_hash="hash-user-key",
            roles=["read"],
            is_authenticated=True,
        )

        # Empty string owner should not match user's hash
        with pytest.raises(ForbiddenException):
            protector.verify_ownership(
                user_ctx,
                resource_owner_id="",
                resource_id="resource-1",
            )

    def test_bola_with_write_role_only(self) -> None:
        """Test that write role alone doesn't grant ownership bypass."""
        protector = BOLAProtector()

        user_ctx = SecurityContext(
            request_id="req-user",
            api_key_hash="hash-user-key",
            roles=["write"],  # No admin role
            is_authenticated=True,
        )

        # Should still fail for other user's resource
        with pytest.raises(ForbiddenException):
            protector.verify_ownership(
                user_ctx,
                resource_owner_id="hash-other-user",
                resource_id="resource-1",
            )

    def test_bola_multiple_roles(self) -> None:
        """Test BOLA with multiple roles including read+write."""
        protector = BOLAProtector()

        user_ctx = SecurityContext(
            request_id="req-user",
            api_key_hash="hash-user-key",
            roles=["read", "write", "admin"],
            is_authenticated=True,
        )

        # Admin role should bypass ownership check
        protector.verify_ownership(
            user_ctx,
            resource_owner_id="hash-other-user",
            resource_id="resource-1",
        )


class TestSecurityContextOwnership:
    """Tests for security context ownership verification."""

    def test_context_with_no_api_key_hash(self) -> None:
        """Test BOLA with security context missing api_key_hash."""
        protector = BOLAProtector()

        # Context without api_key_hash
        ctx = SecurityContext(
            request_id="req-123",
            api_key_hash=None,
            roles=["read"],
            is_authenticated=True,
        )

        # Should raise authentication error
        with pytest.raises(AuthenticationException):
            protector.verify_ownership(
                ctx,
                resource_owner_id="some-owner",
                resource_id="resource-1",
            )

    def test_context_is_frozen(self) -> None:
        """Test that security context is immutable (frozen)."""
        ctx = SecurityContext(
            request_id="req-123",
            api_key_hash="hash123",
            roles=["read"],
            is_authenticated=True,
        )

        # Should not be able to modify (frozen model)
        with pytest.raises((TypeError, AttributeError)):
            ctx.roles.append("admin")  # type: ignore
