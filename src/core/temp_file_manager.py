"""Gerenciador de arquivos temporários para LGPD compliance.

Este módulo garante que arquivos temporários sejam automaticamente
removidos após o processamento, conforme requisito LGPD do projeto.
"""

import atexit
import hashlib
import tempfile
from pathlib import Path
from typing import Optional

import aiofiles  # type: ignore[import-untyped]
from fastapi import UploadFile
from structlog import get_logger

logger = get_logger()


class TempFileManager:
    """Gerencia arquivos temporários com auto-cleanup.

    Garante conformidade com LGPD removendo arquivos temporários
    após o processamento, mesmo em caso de erros.
    """

    _instance: Optional["TempFileManager"] = None
    _temp_files: set[Path] = set()

    def __new__(cls) -> "TempFileManager":
        """Singleton pattern para garantir única instância."""
        if cls._instance is None:
            cls._instance = super().__new__(cls)
            atexit.register(cls._cleanup_all)
        return cls._instance

    async def save_temp(
        self, upload: UploadFile, patient_id: str | None = None
    ) -> Path:
        """Salva arquivo temporariamente.

        Args:
            upload: Arquivo do FastAPI UploadFile
            patient_id: ID opcional do paciente (será hasheado no nome)

        Returns:
            Caminho do arquivo temporário salvo
        """
        suffix = Path(upload.filename or "temp").suffix

        # Gera prefixo com hash do patient_id se fornecido (LGPD compliance)
        prefix = "health_"
        if patient_id:
            # Hash SHA256 truncado para identificar sem expor dados
            patient_hash = hashlib.sha256(patient_id.encode()).hexdigest()[:8]
            prefix = f"health_{patient_hash}_"

        # Cria arquivo temporário com prefixo identificável
        with tempfile.NamedTemporaryFile(
            delete=False, suffix=suffix, prefix=prefix
        ) as tmp:
            tmp_path = Path(tmp.name)

        # Salva conteúdo de forma assíncrona
        async with aiofiles.open(tmp_path, "wb") as f:
            content = await upload.read()
            await f.write(content)

        # Registra para cleanup
        self._temp_files.add(tmp_path)

        logger.debug(
            "temp_file_saved",
            path=str(tmp_path),
            size_bytes=len(content),
            original_filename=upload.filename,
            patient_id_hash=patient_id[:4] + "..." if patient_id else None,
        )

        return tmp_path

    def cleanup(self, file_path: Path) -> None:
        """Remove arquivo específico.

        Args:
            file_path: Caminho do arquivo a remover
        """
        try:
            file_path.unlink(missing_ok=True)
            self._temp_files.discard(file_path)
            logger.debug("temp_file_cleaned", path=str(file_path))
        except Exception as e:
            logger.warning("temp_file_cleanup_error", path=str(file_path), error=str(e))

    @classmethod
    def _cleanup_all(cls) -> None:
        """Remove todos os arquivos temporários pendentes.

        Chamado automaticamente no shutdown do processo.
        """
        for file_path in list(cls._temp_files):
            try:
                file_path.unlink(missing_ok=True)
                logger.debug("temp_file_cleanup_shutdown", path=str(file_path))
            except Exception:
                pass  # Ignora erros no shutdown
        cls._temp_files.clear()

    def get_pending_count(self) -> int:
        """Retorna número de arquivos pendentes de cleanup."""
        return len(self._temp_files)


# Instância singleton
temp_file_manager = TempFileManager()
