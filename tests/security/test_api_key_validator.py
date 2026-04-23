"""Unit tests for API Key validator.

T011: Unit test test_api_key_validator.py - validação de key válida/inválida/vazia
"""


import pytest

from src.core.config import SecurityConfig
from src.core.exceptions import AuthenticationException, ForbiddenException
from src.core.security.auth import APIKeyValidator, BOLAProtector, RBACValidator
from src.core.security.models import SecurityContext


class TestAPIKeyValidator:
    """Test cases for APIKeyValidator."""

    def test_validate_valid_key(self) -> None:
        """Test validation with valid API key."""
        config = SecurityConfig(
            api_key="test-api-key-123",
            api_key_header="X-API-Key",
        )
        validator = APIKeyValidator(config)

        result = validator.validate("test-api-key-123")

        assert result is True

    def test_validate_invalid_key(self) -> None:
        """Test validation with invalid API key."""
        config = SecurityConfig(
            api_key="test-api-key-123",
            api_key_header="X-API-Key",
        )
        validator = APIKeyValidator(config)

        result = validator.validate("wrong-key")

        assert result is False

    def test_validate_empty_key(self) -> None:
        """Test validation with empty API key."""
        config = SecurityConfig(
            api_key="test-api-key-123",
            api_key_header="X-API-Key",
        )
        validator = APIKeyValidator(config)

        result = validator.validate("")

        assert result is False

    def test_validate_none_key(self) -> None:
        """Test validation with None API key."""
        config = SecurityConfig(
            api_key="test-api-key-123",
            api_key_header="X-API-Key",
        )
        validator = APIKeyValidator(config)

        result = validator.validate(None)  # type: ignore[arg-type]

        assert result is False

    def test_validate_whitespace_key(self) -> None:
        """Test validation with whitespace-only API key."""
        config = SecurityConfig(
            api_key="test-api-key-123",
            api_key_header="X-API-Key",
        )
        validator = APIKeyValidator(config)

        result = validator.validate("   ")

        assert result is False

    def test_get_security_context_valid(self) -> None:
        """Test getting security context with valid key."""
        config = SecurityConfig(
            api_key="test-api-key-123",
            api_key_header="X-API-Key",
            environment="production",
        )
        validator = APIKeyValidator(config)

        ctx = validator.get_security_context(
            api_key="test-api-key-123",
            request_id="req-123",
            ip_address="192.168.1.1",
        )

        assert isinstance(ctx, SecurityContext)
        assert ctx.is_authenticated is True
        assert ctx.request_id == "req-123"
        assert "read" in ctx.roles
        assert ctx.ip_address == "192.168.1.1"

    def test_get_security_context_invalid(self) -> None:
        """Test getting security context with invalid key raises exception."""
        config = SecurityConfig(
            api_key="test-api-key-123",
            api_key_header="X-API-Key",
        )
        validator = APIKeyValidator(config)

        with pytest.raises(AuthenticationException) as exc_info:
            validator.get_security_context(
                api_key="wrong-key",
                request_id="req-123",
                ip_address="192.168.1.1",
            )

        assert exc_info.value.status_code == 401

    def test_get_security_context_dev_mode(self) -> None:
        """Test that development mode allows default key."""
        config = SecurityConfig(
            api_key="dev-key",
            api_key_header="X-API-Key",
            environment="development",
        )
        validator = APIKeyValidator(config)

        ctx = validator.get_security_context(
            api_key="dev-key",
            request_id="req-123",
            ip_address="127.0.0.1",
        )

        assert ctx.is_authenticated is True
        assert "admin" in ctx.roles

    def test_api_key_hash_not_stored_plain(self) -> None:
        """Verify that plain API key is not stored in security context."""
        config = SecurityConfig(
            api_key="secret-key-123",
            api_key_header="X-API-Key",
        )
        validator = APIKeyValidator(config)

        ctx = validator.get_security_context(
            api_key="secret-key-123",
            request_id="req-123",
            ip_address="192.168.1.1",
        )

        # Should store hash, not plain key
        assert ctx.api_key_hash is not None
        assert ctx.api_key_hash != "secret-key-123"
        # Should be a SHA256 hash (64 hex chars)
        assert len(ctx.api_key_hash) == 64


class TestRBACValidator:
    """Test cases for RBACValidator."""

    def test_has_role_true(self) -> None:
        """Test role check when role is present."""
        validator = RBACValidator()
        ctx = SecurityContext(
            request_id="req-123",
            roles=["read", "write"],
            is_authenticated=True,
        )

        result = validator.has_role(ctx, "read")

        assert result is True

    def test_has_role_false(self) -> None:
        """Test role check when role is not present."""
        validator = RBACValidator()
        ctx = SecurityContext(
            request_id="req-123",
            roles=["read"],
            is_authenticated=True,
        )

        result = validator.has_role(ctx, "admin")

        assert result is False

    def test_require_role_success(self) -> None:
        """Test require_role when user has the role."""
        validator = RBACValidator()
        ctx = SecurityContext(
            request_id="req-123",
            roles=["read", "write"],
            is_authenticated=True,
        )

        # Should not raise
        validator.require_role(ctx, "write")

    def test_require_role_failure(self) -> None:
        """Test require_role when user doesn't have the role."""
        validator = RBACValidator()
        ctx = SecurityContext(
            request_id="req-123",
            roles=["read"],
            is_authenticated=True,
        )

        with pytest.raises(ForbiddenException) as exc_info:
            validator.require_role(ctx, "admin")

        assert exc_info.value.status_code == 403

    def test_has_any_role_true(self) -> None:
        """Test has_any_role when user has at least one role."""
        validator = RBACValidator()
        ctx = SecurityContext(
            request_id="req-123",
            roles=["read", "write"],
            is_authenticated=True,
        )

        result = validator.has_any_role(ctx, ["admin", "write"])

        assert result is True

    def test_has_any_role_false(self) -> None:
        """Test has_any_role when user has none of the roles."""
        validator = RBACValidator()
        ctx = SecurityContext(
            request_id="req-123",
            roles=["read"],
            is_authenticated=True,
        )

        result = validator.has_any_role(ctx, ["admin", "write"])

        assert result is False

    def test_roles_from_api_key(self) -> None:
        """Test that different API keys get appropriate roles."""
        config = SecurityConfig(
            api_key="admin-key",
            api_key_header="X-API-Key",
            environment="production",
        )
        validator = APIKeyValidator(config)

        # In production, only admin key gets admin role
        ctx = validator.get_security_context(
            api_key="admin-key",
            request_id="req-123",
            ip_address="192.168.1.1",
        )

        assert "admin" in ctx.roles


class TestBOLAProtector:
    """Test cases for BOLAProtector."""

    def test_verify_ownership_match(self) -> None:
        """Test ownership verification when user owns the resource."""
        protector = BOLAProtector()
        ctx = SecurityContext(
            request_id="req-123",
            api_key_hash="hash123",
            is_authenticated=True,
        )

        # Should not raise when user owns the resource
        protector.verify_ownership(
            ctx,
            resource_owner_id="hash123",
            resource_id="resource-1",
        )

    def test_verify_ownership_mismatch(self) -> None:
        """Test ownership verification when user doesn't own the resource."""
        protector = BOLAProtector()
        ctx = SecurityContext(
            request_id="req-123",
            api_key_hash="hash123",
            is_authenticated=True,
        )

        with pytest.raises(ForbiddenException) as exc_info:
            protector.verify_ownership(
                ctx,
                resource_owner_id="different-hash",
                resource_id="resource-1",
            )

        assert exc_info.value.status_code == 403
        assert "resource-1" in str(exc_info.value.message)

    def test_verify_ownership_unauthenticated(self) -> None:
        """Test ownership verification for unauthenticated user."""
        protector = BOLAProtector()
        ctx = SecurityContext.anonymous(request_id="req-123")

        with pytest.raises(AuthenticationException) as exc_info:
            protector.verify_ownership(
                ctx,
                resource_owner_id="any-hash",
                resource_id="resource-1",
            )

        assert exc_info.value.status_code == 401

    def test_verify_ownership_admin_bypass(self) -> None:
        """Test that admin can access any resource."""
        protector = BOLAProtector()
        ctx = SecurityContext(
            request_id="req-123",
            api_key_hash="admin-hash",
            roles=["admin"],
            is_authenticated=True,
        )

        # Admin should be able to access any resource
        protector.verify_ownership(
            ctx,
            resource_owner_id="different-hash",
            resource_id="resource-1",
        )

    def test_verify_ownership_with_none_owner(self) -> None:
        """Test ownership verification with None owner (public resource)."""
        protector = BOLAProtector()
        ctx = SecurityContext(
            request_id="req-123",
            api_key_hash="hash123",
            is_authenticated=True,
        )

        # Should not raise for public resources
        protector.verify_ownership(
            ctx,
            resource_owner_id=None,
            resource_id="public-resource",
        )


class TestSecurityIntegration:
    """Integration tests for security components working together."""

    def test_full_auth_flow_success(self) -> None:
        """Test complete authentication flow with valid credentials."""
        config = SecurityConfig(
            api_key="valid-key",
            api_key_header="X-API-Key",
            environment="production",
        )
        auth_validator = APIKeyValidator(config)
        rbac_validator = RBACValidator()
        bola_protector = BOLAProtector()

        # Step 1: Validate API key
        ctx = auth_validator.get_security_context(
            api_key="valid-key",
            request_id="req-123",
            ip_address="192.168.1.1",
        )

        # Step 2: Check role
        assert rbac_validator.has_role(ctx, "read")

        # Step 3: Verify ownership
        bola_protector.verify_ownership(
            ctx,
            resource_owner_id=ctx.api_key_hash,
            resource_id="my-resource",
        )

    def test_full_auth_flow_bola_violation(self) -> None:
        """Test complete flow detecting BOLA violation."""
        config = SecurityConfig(
            api_key="user1-key",
            api_key_header="X-API-Key",
        )
        auth_validator = APIKeyValidator(config)
        bola_protector = BOLAProtector()

        # User 1 authenticates
        ctx = auth_validator.get_security_context(
            api_key="user1-key",
            request_id="req-123",
            ip_address="192.168.1.1",
        )

        # But tries to access User 2's resource
        with pytest.raises(ForbiddenException):
            bola_protector.verify_ownership(
                ctx,
                resource_owner_id="user2-hash",  # Different user's resource
                resource_id="user2-private-data",
            )
