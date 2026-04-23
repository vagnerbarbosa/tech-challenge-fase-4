"""Modelos de contexto de segurança.

Fornece modelos Pydantic para contexto de segurança e autenticação.
"""

from typing import Any

from pydantic import BaseModel, Field


class SecurityContext(BaseModel):
    """Contexto de segurança para autenticação e autorização de requisições.

    Contém todas as informações relacionadas à segurança de uma requisição,
    incluindo hash da chave de API, roles, endereço IP e status de autenticação.
    """

    request_id: str = Field(
        ...,
        description="Identificador único para a requisição",
    )
    api_key_hash: str | None = Field(
        default=None,
        description="Hash SHA256 da chave de API (nunca armazenar chave em texto puro)",
    )
    roles: list[str] = Field(
        default_factory=list,
        description="Lista de roles atribuídas à requisição",
    )
    ip_address: str | None = Field(
        default=None,
        description="Endereço IP do cliente",
    )
    is_authenticated: bool = Field(
        default=False,
        description="Se a requisição está autenticada",
    )

    model_config = {
        "frozen": True,  # Immutable for security
    }

    def has_role(self, role: str) -> bool:
        """Verifica se o contexto de segurança possui uma role específica.

        Args:
            role: Role para verificar

        Returns:
            True se a role está presente
        """
        return role in self.roles

    def to_log_safe_dict(self) -> dict[str, Any]:
        """Retorna uma versão segura para logs do contexto.

        Mascara campos sensíveis para logging seguro.

        Returns:
            Dicionário com dados sensíveis mascarados
        """
        return {
            "request_id": self.request_id,
            "api_key_hash": self.api_key_hash[:16] + "..." if self.api_key_hash else None,
            "roles": self.roles,
            "ip_address": self._mask_ip(self.ip_address) if self.ip_address else None,
            "is_authenticated": self.is_authenticated,
        }

    @staticmethod
    def _mask_ip(ip: str) -> str:
        """Mascara endereço IP para privacidade.

        Args:
            ip: Endereço IP para mascarar

        Returns:
            IP mascarado (último octeto oculto)
        """
        if ":" in ip:  # IPv6
            parts = ip.split(":")
            return ":".join(parts[:4]) + ":****"
        else:  # IPv4
            parts = ip.split(".")
            return ".".join(parts[:3]) + ".***"

    @classmethod
    def anonymous(cls, request_id: str) -> "SecurityContext":
        """Cria um contexto de segurança anônimo.

        Args:
            request_id: Identificador único da requisição

        Returns:
            Contexto de segurança anônimo
        """
        return cls(
            request_id=request_id,
            is_authenticated=False,
        )
