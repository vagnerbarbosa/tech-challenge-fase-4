"""Implementação de cache em memória com TTL para resultados de análise."""

import hashlib
from datetime import datetime, timedelta
from pathlib import Path
from typing import Any


class AnalysisCache:
    """Cache em memória thread-safe para resultados de análise.

    Este cache armazena resultados de análise com TTL (time-to-live) para evitar
    reprocessamento de textos, arquivos de áudio e vídeo idênticos.
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

        Alias para _generate_key_from_text para compatibilidade com testes.
        """
        return self._generate_key_from_text(text)

    def _generate_key_from_text(self, text: str) -> str:
        """Gera chave de cache a partir do conteúdo do texto."""
        normalized = text.strip().lower()
        return hashlib.sha256(normalized.encode()).hexdigest()[:32]

    def _generate_key_from_file(self, file_path: Path) -> str:
        """Gera chave de cache a partir do conteúdo do arquivo."""
        chunk_size = 64 * 1024
        hasher = hashlib.sha256()

        with open(file_path, "rb") as f:
            chunk = f.read(chunk_size)
            hasher.update(chunk)
            file_size = file_path.stat().st_size
            hasher.update(str(file_size).encode())

        return hasher.hexdigest()[:32]

    def get(self, key_input: str | Path) -> Any | None:
        """Recupera resultado do cache se válido.

        Args:
            key_input: Texto ou caminho de arquivo para buscar

        Returns:
            Resultado cacheado ou None se não encontrado/expirado
        """
        if isinstance(key_input, Path):
            key = self._generate_key_from_file(key_input)
        else:
            key = self._generate_key_from_text(key_input)

        if key not in self._cache:
            return None

        # Verifica se expirou
        if datetime.now() - self._timestamps[key] >= self._ttl:
            del self._cache[key]
            del self._timestamps[key]
            return None

        return self._cache[key]

    def set(self, key_input: str | Path, value: Any) -> None:
        """Armazena resultado no cache.

        Args:
            key_input: Texto ou caminho de arquivo (usado como chave)
            value: Resultado a ser cacheado
        """
        if isinstance(key_input, Path):
            key = self._generate_key_from_file(key_input)
        else:
            key = self._generate_key_from_text(key_input)

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
        self.clear_expired()
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
