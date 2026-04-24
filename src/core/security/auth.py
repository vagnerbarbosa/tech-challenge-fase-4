"""Utilitários de autenticação e autorização.

Fornece validação de chaves de API, RBAC (Controle de Acesso Baseado em Roles)
e proteção contra BOLA (Broken Object Level Authorization).

Implementa:
- T014: APIKeyValidator para autenticação por chave de API
- T015: RBACValidator para controle de acesso baseado em roles
- T017: BOLAProtector para autorização em nível de objeto
"""

from __future__ import annotations

import hashlib
import json
import os
import secrets
import stat
import uuid
from pathlib import Path

from src.core.config import SecurityConfig
from src.core.exceptions import AuthenticationException, ForbiddenException
from src.core.security.models import SecurityContext


class GeneratedAPIKeyStore:
    """Armazena e gerencia chaves de API geradas dinamicamente.

    Armazena chaves em arquivo JSON com permissões restritas (0o600).
    Cria o arquivo automaticamente se não existir.
    """

    def __init__(self, storage_path: str = "data/generated_api_keys.json"):
        """Inicializa o store com caminho do arquivo.

        Args:
            storage_path: Caminho para o arquivo de armazenamento
        """
        self._storage_path = Path(storage_path)
        self._ensure_storage_exists()

    def _ensure_storage_exists(self) -> None:
        """Cria diretório e arquivo se não existirem."""
        self._storage_path.parent.mkdir(parents=True, exist_ok=True)
        if not self._storage_path.exists():
            self._storage_path.write_text("{}")
            os.chmod(self._storage_path, stat.S_IRUSR | stat.S_IWUSR)

    def add_key(self, api_key: str, description: str | None = None) -> str:
        """Adiciona uma nova chave ao store.

        Args:
            api_key: A chave de API completa
            description: Descrição opcional

        Returns:
            O key_id da chave armazenada
        """
        raw_key = api_key.replace("ak_", "")
        key_id = raw_key[:16]

        keys = self._load_keys()
        keys[key_id] = {
            "api_key": api_key,
            "description": description,
            "created_at": str(uuid.uuid4()),
        }
        self._save_keys(keys)

        return key_id

    def validate(self, api_key: str | None) -> bool:
        """Valida se uma chave existe no store.

        Args:
            api_key: A chave de API para validar

        Returns:
            True se a chave existe, False caso contrário
        """
        if not api_key:
            return False

        raw_key = api_key.replace("ak_", "")
        key_id = raw_key[:16]

        keys = self._load_keys()
        return key_id in keys and keys[key_id].get("api_key") == api_key

    def _load_keys(self) -> dict:
        """Carrega as chaves do arquivo."""
        try:
            return json.loads(self._storage_path.read_text())
        except (FileNotFoundError, json.JSONDecodeError):
            return {}

    def _save_keys(self, keys: dict) -> None:
        """Salva as chaves no arquivo."""
        self._storage_path.write_text(json.dumps(keys, indent=2))
        os.chmod(self._storage_path, stat.S_IRUSR | stat.S_IWUSR)


class APIKeyValidator:
    """Valida chaves de API e cria contextos de segurança.

    Implementa validação segura de chaves de API:
    - Comparação em tempo constante para prevenir ataques de timing
    - Hash SHA256 para armazenamento
    - Atribuição de roles baseada no ambiente e chave

    Attributes:
        config: Configuração de segurança com configurações da chave de API
    """

    def __init__(self, config: SecurityConfig) -> None:
        """Inicializa o validador com configuração de segurança.

        Args:
            config: Configuração de segurança contendo a chave de API
        """
        self.config = config
        self._generated_keys = GeneratedAPIKeyStore()

    def validate(self, api_key: str | None) -> bool:
        """Valida uma chave de API contra a chave configurada ou chaves geradas.

        Usa comparação em tempo constante para prevenir ataques de timing.
        Também verifica chaves geradas dinamicamente via /admin/api-keys.

        Args:
            api_key: A chave de API para validar

        Returns:
            True se a chave é válida, False caso contrário
        """
        if api_key is None:
            return False

        # Strip whitespace and check empty
        key = api_key.strip()
        if not key:
            return False

        # Check master API key (constant-time comparison)
        if secrets.compare_digest(key, self.config.api_key):
            return True

        # Check generated API keys
        return self._generated_keys.validate(key)

    def get_security_context(
        self,
        api_key: str | None,
        request_id: str | None = None,
        ip_address: str | None = None,
    ) -> SecurityContext:
        """Cria contexto de segurança a partir da chave de API.

        Valida a chave de API e retorna um contexto de segurança
        com as roles apropriadas atribuídas.

        Args:
            api_key: A chave de API para validar
            request_id: Identificador único para a requisição
            ip_address: Endereço IP do cliente

        Returns:
            SecurityContext com informações de autenticação e roles

        Raises:
            AuthenticationException: Se a chave de API for inválida
        """
        if not self.validate(api_key):
            raise AuthenticationException(
                message="API key inválida ou ausente",
                details={"header": self.config.api_key_header},
            )

        # Generate request ID if not provided
        if request_id is None:
            request_id = str(uuid.uuid4())

        # Hash the API key for storage (not the plain key)
        # api_key is guaranteed to be str here because validate() passed
        assert api_key is not None, "api_key must be str after validation"
        api_key_hash = self._hash_api_key(api_key)

        # Determine roles based on environment and key
        roles = self._determine_roles(api_key)

        return SecurityContext(
            request_id=request_id,
            api_key_hash=api_key_hash,
            roles=roles,
            ip_address=ip_address,
            is_authenticated=True,
        )

    def _hash_api_key(self, api_key: str) -> str:
        """Hash da chave de API usando PBKDF2.

        Usa PBKDF2-HMAC-SHA256 que é computacionalmente mais custoso
        que SHA256 simples, adequado para proteção de API keys.

        Args:
            api_key: A chave de API para fazer hash

        Returns:
            Hash PBKDF2 como string hexadecimal
        """
        # Use PBKDF2 with 100k iterations for API key hashing
        # Provides better protection than simple SHA256
        salt = self.config.environment.encode("utf-8")
        return hashlib.pbkdf2_hmac(
            "sha256",
            api_key.encode("utf-8"),
            salt,
            100000,  # 100k iterations
        ).hex()

    def _determine_roles(self, api_key: str) -> tuple[str, ...]:
        """Determina as roles baseadas na chave de API e ambiente.

        Chaves contendo "admin" no nome recebem role admin em qualquer ambiente.
        Em desenvolvimento, todas as chaves recebem role admin para conveniência.

        Args:
            api_key: A chave de API validada

        Returns:
            Tuple de strings de roles (imutável)
        """
        roles: list[str] = ["read"]  # Default role

        # All valid keys get write access
        roles.append("write")

        # Keys with "admin" in name get admin role (in any environment)
        if "admin" in api_key.lower():
            roles.append("admin")
        elif self.config.environment == "development":
            # In development, grant admin to all keys for convenience
            roles.append("admin")

        return tuple(roles)


class RBACValidator:
    """Validador de Controle de Acesso Baseado em Roles (RBAC).

    Valida que usuários têm as roles necessárias para acessar recursos.
    Implementa o padrão RBAC padrão com suporte a hierarquia de roles.

    Roles:
        - read: Pode ler dados
        - write: Pode criar e modificar dados
        - admin: Acesso total ao sistema
    """

    # Role hierarchy - higher roles include lower permissions
    ROLE_HIERARCHY: dict[str, int] = {
        "read": 1,
        "write": 2,
        "admin": 3,
    }

    def has_role(self, ctx: SecurityContext, role: str) -> bool:
        """Verifica se o contexto de segurança possui uma role específica.

        Args:
            ctx: Contexto de segurança para verificar
            role: Role a verificar

        Returns:
            True se o contexto possui a role
        """
        return role in ctx.roles

    def has_any_role(self, ctx: SecurityContext, roles: list[str]) -> bool:
        """Verifica se o contexto de segurança possui alguma das roles especificadas.

        Args:
            ctx: Contexto de segurança para verificar
            roles: Lista de roles para verificar

        Returns:
            True se o contexto possui alguma das roles
        """
        return any(role in ctx.roles for role in roles)

    def has_all_roles(self, ctx: SecurityContext, roles: list[str]) -> bool:
        """Verifica se o contexto de segurança possui todas as roles especificadas.

        Args:
            ctx: Contexto de segurança para verificar
            roles: Lista de roles para verificar

        Returns:
            True se o contexto possui todas as roles
        """
        return all(role in ctx.roles for role in roles)

    def require_role(self, ctx: SecurityContext, role: str) -> None:
        """Exige uma role específica, lança exceção se não tiver.

        Args:
            ctx: Contexto de segurança para verificar
            role: Role obrigatória

        Raises:
            ForbiddenException: Se o contexto não possuir a role
        """
        if not self.has_role(ctx, role):
            raise ForbiddenException(
                message=f"Acesso negado: role '{role}' necessária",
                details={
                    "required_role": role,
                    "user_roles": ctx.roles,
                },
            )

    def require_any_role(self, ctx: SecurityContext, roles: list[str]) -> None:
        """Exige qualquer uma das roles especificadas.

        Args:
            ctx: Contexto de segurança para verificar
            roles: Lista de roles aceitáveis

        Raises:
            ForbiddenException: Se o contexto não possuir nenhuma das roles
        """
        if not self.has_any_role(ctx, roles):
            raise ForbiddenException(
                message=f"Acesso negado: uma das roles {roles} é necessária",
                details={
                    "required_roles": roles,
                    "user_roles": ctx.roles,
                },
            )

    def has_permission_level(
        self,
        ctx: SecurityContext,
        min_level: int,
    ) -> bool:
        """Verifica se o usuário tem pelo menos o nível de permissão especificado.

        Usa a hierarquia de roles para determinar o nível efetivo de permissão.

        Args:
            ctx: Contexto de segurança
            min_level: Nível mínimo de permissão requerido

        Returns:
            True se o usuário tem nível de permissão suficiente
        """
        user_level = max(
            (self.ROLE_HIERARCHY.get(role, 0) for role in ctx.roles),
            default=0,
        )
        return user_level >= min_level


class BOLAProtector:
    """Protetor contra Broken Object Level Authorization (BOLA).

    Previne que usuários acessem recursos que não lhes pertencem (OWASP API1).
    Verifica que o usuário autenticado é o proprietário do recurso solicitado.

    Attributes:
        bypass_roles: Roles que podem ignorar verificações de propriedade (ex: admin)
    """

    BYPASS_ROLES: set[str] = {"admin"}

    def verify_ownership(
        self,
        ctx: SecurityContext,
        resource_owner_id: str | None,
        resource_id: str | None = None,
    ) -> None:
        """Verifica se o usuário é o proprietário do recurso ou tem privilégios de ignorar verificação.

        Args:
            ctx: Contexto de segurança do usuário solicitante
            resource_owner_id: ID do proprietário do recurso (geralmente api_key_hash)
            resource_id: Identificador opcional do recurso para mensagens de erro

        Raises:
            AuthenticationException: Se o usuário não estiver autenticado
            ForbiddenException: Se o usuário não for o proprietário e não tiver role de ignorar
        """
        # Check authentication
        if not ctx.is_authenticated:
            raise AuthenticationException(
                message="Autenticação necessária para acessar este recurso",
                details={"resource_id": resource_id},
            )

        # Check if user has bypass role (admin)
        if self._has_bypass_role(ctx):
            return

        # Check if user context has api_key_hash
        if not ctx.api_key_hash:
            raise AuthenticationException(
                message="Contexto de segurança inválido: api_key_hash ausente",
            )

        # Public resources (no owner) are accessible
        if resource_owner_id is None:
            return

        # Verify ownership using constant-time comparison
        if not secrets.compare_digest(ctx.api_key_hash, resource_owner_id):
            resource_info = f" ({resource_id})" if resource_id else ""
            raise ForbiddenException(
                message=f"Acesso negado: você não tem permissão para este recurso{resource_info}",
                details={
                    "reason": "resource_ownership_mismatch",
                    "resource_id": resource_id,
                },
            )

    def _has_bypass_role(self, ctx: SecurityContext) -> bool:
        """Verifica se o usuário tem uma role que ignora verificações de propriedade.

        Args:
            ctx: Contexto de segurança para verificar

        Returns:
            True se o usuário pode ignorar verificações de propriedade
        """
        return any(role in self.BYPASS_ROLES for role in ctx.roles)

    def can_access(
        self,
        ctx: SecurityContext,
        resource_owner_id: str | None,
    ) -> bool:
        """Verifica se o usuário pode acessar o recurso sem lançar exceções.

        Args:
            ctx: Contexto de segurança
            resource_owner_id: ID do proprietário do recurso

        Returns:
            True se o usuário pode acessar o recurso
        """
        try:
            self.verify_ownership(ctx, resource_owner_id)
            return True
        except (AuthenticationException, ForbiddenException):
            return False


# Singleton instances for dependency injection
_api_key_validator: APIKeyValidator | None = None
_rbac_validator: RBACValidator | None = None
_bola_protector: BOLAProtector | None = None


def get_api_key_validator(config: SecurityConfig | None = None) -> APIKeyValidator:
    """Obtém ou cria o singleton do validador de chaves de API.

    Args:
        config: Configuração de segurança opcional

    Returns:
        Instância de APIKeyValidator
    """
    global _api_key_validator
    if _api_key_validator is None:
        if config is None:
            from src.core.config import settings
            config = settings.security_config
        _api_key_validator = APIKeyValidator(config)
    return _api_key_validator


def get_rbac_validator() -> RBACValidator:
    """Obtém ou cria o singleton do validador RBAC.

    Returns:
        Instância de RBACValidator
    """
    global _rbac_validator
    if _rbac_validator is None:
        _rbac_validator = RBACValidator()
    return _rbac_validator


def get_bola_protector() -> BOLAProtector:
    """Obtém ou cria o singleton do protetor BOLA.

    Returns:
        Instância de BOLAProtector
    """
    global _bola_protector
    if _bola_protector is None:
        _bola_protector = BOLAProtector()
    return _bola_protector
