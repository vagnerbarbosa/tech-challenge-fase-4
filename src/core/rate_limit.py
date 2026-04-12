"""Rate limiting e gestão de quotas Azure Free Tier.

Protege contra exceder limites do Azure Free Tier.
Implementação simples usando arquivo para persistência.
"""

import json
import time
from datetime import UTC, datetime
from pathlib import Path
from typing import Any, Optional

from structlog import get_logger

from src.core.exceptions import RateLimitException

logger = get_logger()

# Rate limits para Azure Free Tier
RATE_LIMITS = {
    "text": {"daily": 160, "monthly": 5000},
    "audio": {"daily_minutes": 10, "monthly_minutes": 300},
    "vision": {"daily": 160, "monthly": 5000},
}

# Arquivo para persistência de quota (simples, mas funcional)
QUOTA_FILE = Path("/tmp/azure_quota_state.json")


class QuotaManager:
    """Gerencia quotas do Azure Free Tier com persistência simples."""

    _instance: Optional["QuotaManager"] = None

    def __new__(cls) -> "QuotaManager":
        """Singleton pattern."""
        if cls._instance is None:
            cls._instance = super().__new__(cls)
            cls._instance._init_state()
        return cls._instance

    def _init_state(self) -> None:
        """Inicializa estado de quota."""
        self._state = self._load_state()
        self._last_save = time.time()

    def _load_state(self) -> dict[str, Any]:
        """Carrega estado de quota do arquivo."""
        try:
            if QUOTA_FILE.exists():
                with open(QUOTA_FILE) as f:
                    result: dict[str, Any] = json.load(f)
                    return result
        except Exception as e:
            logger.warning("quota_load_error", error=str(e))
        return {"daily": {}, "monthly": {}}

    def _save_state(self) -> None:
        """Salva estado de quota no arquivo."""
        try:
            with open(QUOTA_FILE, "w") as f:
                json.dump(self._state, f)
        except Exception as e:
            logger.warning("quota_save_error", error=str(e))

    def _get_day_key(self) -> str:
        """Retorna chave para o dia atual."""
        return datetime.now(UTC).strftime("%Y-%m-%d")

    def _get_month_key(self) -> str:
        """Retorna chave para o mês atual."""
        return datetime.now(UTC).strftime("%Y-%m-%Y")

    def check_and_increment(
        self, service: str, daily_limit: int, monthly_limit: int, increment: int = 1
    ) -> dict[str, Any]:
        """Verifica e incrementa uso da quota.

        Args:
            service: Nome do serviço (text, audio, vision)
            daily_limit: Limite diário
            monthly_limit: Limite mensal
            increment: Valor a incrementar (1 para requests, minutos para áudio)

        Returns:
            Dict com quota_restante, quota_usada, limites

        Raises:
            RateLimitException: Se quota excedida
        """
        day_key = self._get_day_key()
        month_key = self._get_month_key()

        # Inicializa se necessário
        if service not in self._state["daily"]:
            self._state["daily"][service] = {}
        if service not in self._state["monthly"]:
            self._state["monthly"][service] = {}

        # Reseta contadores se mudou dia/mês
        if day_key not in self._state["daily"][service]:
            self._state["daily"][service] = {day_key: 0}
        if month_key not in self._state["monthly"][service]:
            self._state["monthly"][service] = {month_key: 0}

        # Pega uso atual
        daily_used = self._state["daily"][service].get(day_key, 0)
        monthly_used = self._state["monthly"][service].get(month_key, 0)

        # Verifica limites
        if daily_used + increment > daily_limit:
            logger.warning(
                "daily_quota_exceeded",
                service=service,
                used=daily_used,
                limit=daily_limit,
            )
            raise RateLimitException(
                service=service,
                message=f"Quota diária excedida para {service}. Limite: {daily_limit}",
                retry_after=86400,  # 24 horas
            )

        if monthly_used + increment > monthly_limit:
            logger.warning(
                "monthly_quota_exceeded",
                service=service,
                used=monthly_used,
                limit=monthly_limit,
            )
            raise RateLimitException(
                service=service,
                message=f"Quota mensal excedida para {service}. Limite: {monthly_limit}",
                retry_after=86400 * 30,  # ~30 dias
            )

        # Incrementa
        self._state["daily"][service][day_key] = daily_used + increment
        self._state["monthly"][service][month_key] = monthly_used + increment

        # Salva periodicamente (a cada 60 segundos)
        if time.time() - self._last_save > 60:
            self._save_state()
            self._last_save = time.time()

        daily_remaining = daily_limit - daily_used - increment
        monthly_remaining = monthly_limit - monthly_used - increment

        return {
            "service": service,
            "daily_used": daily_used + increment,
            "daily_limit": daily_limit,
            "daily_remaining": max(0, daily_remaining),
            "monthly_used": monthly_used + increment,
            "monthly_limit": monthly_limit,
            "monthly_remaining": max(0, monthly_remaining),
        }

    def get_quota_status(self, service: str) -> dict[str, Any]:
        """Retorna status atual da quota."""
        day_key = self._get_day_key()
        month_key = self._get_month_key()

        daily_used = self._state.get("daily", {}).get(service, {}).get(day_key, 0)
        monthly_used = self._state.get("monthly", {}).get(service, {}).get(month_key, 0)

        limits = RATE_LIMITS.get(service, {"daily": 160, "monthly": 5000})

        return {
            "service": service,
            "daily_used": daily_used,
            "daily_limit": limits.get("daily", limits.get("daily_minutes", 10)),
            "daily_remaining": limits.get("daily", limits.get("daily_minutes", 10))
            - daily_used,
            "monthly_used": monthly_used,
            "monthly_limit": limits.get("monthly", limits.get("monthly_minutes", 300)),
            "monthly_remaining": limits.get("monthly", limits.get("monthly_minutes", 300))
            - monthly_used,
        }


def check_rate_limit(service: str, daily_limit: int, monthly_limit: int) -> int:
    """Verifica se rate limit foi excedido (função legada).

    Args:
        service: Nome do serviço (text, audio, vision)
        daily_limit: Limite diário
        monthly_limit: Limite mensal

    Returns:
        Quota restante diária
    """
    manager = QuotaManager()
    status = manager.get_quota_status(service)
    daily_remaining: int = status["daily_remaining"]
    return daily_remaining


def check_and_increment_quota(
    service: str, daily_limit: int, monthly_limit: int, increment: int = 1
) -> dict[str, Any]:
    """Verifica e incrementa uso da quota.

    Args:
        service: Nome do serviço
        daily_limit: Limite diário
        monthly_limit: Limite mensal
        increment: Valor a incrementar

    Returns:
        Dict com status da quota
    """
    manager = QuotaManager()
    return manager.check_and_increment(service, daily_limit, monthly_limit, increment)


def get_quota_status(service: str) -> dict[str, Any]:
    """Retorna status atual da quota para um serviço."""
    manager = QuotaManager()
    return manager.get_quota_status(service)
