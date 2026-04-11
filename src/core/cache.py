"""Implementação de cache em memória com TTL para resultados de análise."""

import hashlib
from datetime import datetime, timedelta
from typing import Any


class AnalysisCache:
    """Cache em memória thread-safe para resultados de análise de texto.

    Este cache armazena resultados de análise com TTL (time-to-live) para evitar
    reprocessamento do mesmo texto e otimizar o uso da API Azure.
    """

    def __init__(self, ttl_minutes: int = 60) -> None:
        """Inicializa o cache com TTL especificado.

        Args:
            ttl_minutes: Tempo de vida em minutos (padrão: 60)
        """
        self._cache: dict[str, Any] = {}
        self._timestamps: dict[str, datetime] = {}
        self._ttl = timedelta(minutes=ttl_minutes)

    def _generate_key(self, text: str) -> str:
        """Gera chave de cache a partir do conteúdo do texto.

        Usa hash SHA256 do texto normalizado para criar chaves únicas.

        Args:
            text: Texto de entrada

        Returns:
            String da chave de cache
        """
        normalized = text.strip().lower()
        return hashlib.sha256(normalized.encode()).hexdigest()[:32]

    def get(self, text: str) -> Any | None:
        """Recupera resultado do cache se válido.

        Args:
            text: Texto de entrada para buscar

        Returns:
            Resultado cacheado ou None se não encontrado/expirado
        """
        key = self._generate_key(text)

        if key not in self._cache:
            return None

        # Verifica se expirou
        if datetime.now() - self._timestamps[key] >= self._ttl:
            # Remove entrada expirada
            del self._cache[key]
            del self._timestamps[key]
            return None

        return self._cache[key]

    def set(self, text: str, value: Any) -> None:
        """Armazena resultado no cache.

        Args:
            text: Texto de entrada (usado como chave)
            value: Resultado a ser cacheado
        """
        key = self._generate_key(text)
        self._cache[key] = value
        self._timestamps[key] = datetime.now()

    def clear_expired(self) -> int:
        """Remove todas as entradas expiradas.

        Returns:
            Número de entradas removidas
        """
        now = datetime.now()
        expired_keys = [
            key for key, ts in self._timestamps.items()
            if now - ts >= self._ttl
        ]

        for key in expired_keys:
            del self._cache[key]
            del self._timestamps[key]

        return len(expired_keys)

    def clear_all(self) -> None:
        """Limpa todas as entradas do cache."""
        self._cache.clear()
        self._timestamps.clear()

    def get_stats(self) -> dict[str, Any]:
        """Obtém estatísticas do cache.

        Returns:
            Dicionário com estatísticas do cache
        """
        self.clear_expired()  # Limpa primeiro
        return {
            "entries": len(self._cache),
            "ttl_minutes": self._ttl.total_seconds() / 60,
        }


# Instância global do cache
_analysis_cache: AnalysisCache | None = None


def get_cache() -> AnalysisCache:
    """Obtém ou cria instância global do cache.

    Returns:
        Instância de AnalysisCache
    """
    global _analysis_cache
    if _analysis_cache is None:
        _analysis_cache = AnalysisCache()
    return _analysis_cache
