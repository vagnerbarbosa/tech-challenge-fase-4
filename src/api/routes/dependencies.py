"""Dependências FastAPI para injeção de recursos.

Gerencia singletons como TempFileManager para uso em rotas.
"""

from src.core.temp_file_manager import TempFileManager


# Singleton para TempFileManager
_temp_manager: TempFileManager | None = None


def get_temp_manager() -> TempFileManager:
    """Retorna instância singleton do TempFileManager.

    Returns:
        TempFileManager singleton
    """
    global _temp_manager
    if _temp_manager is None:
        _temp_manager = TempFileManager()
    return _temp_manager
