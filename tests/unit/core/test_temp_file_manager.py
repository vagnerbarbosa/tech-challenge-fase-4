"""Testes para TempFileManager.

LGPD Compliance: Verifica cleanup automático de arquivos temporários.
"""

from pathlib import Path
from unittest.mock import AsyncMock, Mock, patch

import pytest

from src.core.temp_file_manager import TempFileManager, temp_file_manager


class TestTempFileManager:
    """Test suite para TempFileManager."""

    @pytest.fixture(autouse=True)
    def reset_singleton(self):
        """Reseta singleton entre testes."""
        TempFileManager._instance = None
        TempFileManager._temp_files.clear()
        yield
        TempFileManager._instance = None
        TempFileManager._temp_files.clear()

    @pytest.fixture
    def temp_manager(self):
        """Fixture para TempFileManager."""
        return TempFileManager()

    @pytest.mark.asyncio
    async def test_save_temp_creates_file(self, temp_manager, tmp_path):
        """Testa se save_temp cria arquivo temporário."""
        # Arrange
        mock_upload = Mock()
        mock_upload.filename = "test.wav"
        mock_upload.read = AsyncMock(return_value=b"fake audio content")

        # Act
        result_path = await temp_manager.save_temp(mock_upload)

        # Assert
        assert result_path.exists()
        assert result_path.suffix == ".wav"
        assert result_path in TempFileManager._temp_files

    @pytest.mark.asyncio
    async def test_cleanup_removes_file(self, temp_manager, tmp_path):
        """Testa se cleanup remove arquivo."""
        # Arrange
        mock_upload = Mock()
        mock_upload.filename = "test.wav"
        mock_upload.read = AsyncMock(return_value=b"fake audio content")

        result_path = await temp_manager.save_temp(mock_upload)
        assert result_path.exists()

        # Act
        temp_manager.cleanup(result_path)

        # Assert
        assert not result_path.exists()
        assert result_path not in TempFileManager._temp_files

    @pytest.mark.asyncio
    async def test_cleanup_missing_file_no_error(self, temp_manager):
        """Testa se cleanup não falha com arquivo inexistente."""
        # Arrange
        fake_path = Path("/tmp/nonexistent_file.wav")

        # Act & Assert (não deve lançar exceção)
        temp_manager.cleanup(fake_path)

    def test_singleton_pattern(self):
        """Testa se singleton retorna mesma instância."""
        # Act
        instance1 = TempFileManager()
        instance2 = TempFileManager()

        # Assert
        assert instance1 is instance2

    def test_get_pending_count(self, temp_manager):
        """Testa contagem de arquivos pendentes."""
        # Arrange
        TempFileManager._temp_files.add(Path("/tmp/fake1.wav"))
        TempFileManager._temp_files.add(Path("/tmp/fake2.wav"))

        # Act
        count = temp_manager.get_pending_count()

        # Assert
        assert count == 2

    def test_cleanup_all_removes_all_files(self, temp_manager, tmp_path):
        """Testa se cleanup_all remove todos os arquivos."""
        # Arrange
        file1 = tmp_path / "test1.wav"
        file2 = tmp_path / "test2.wav"
        file1.write_text("content1")
        file2.write_text("content2")

        TempFileManager._temp_files.add(file1)
        TempFileManager._temp_files.add(file2)

        # Act
        TempFileManager._cleanup_all()

        # Assert
        assert not file1.exists()
        assert not file2.exists()
        assert len(TempFileManager._temp_files) == 0


class TestTempFileManagerGlobal:
    """Testes para instância global temp_file_manager."""

    def test_global_instance_is_singleton(self):
        """Testa se instância global é singleton."""
        from src.core.temp_file_manager import TempFileManager

        # Cria nova instância e verifica se é a mesma
        instance = TempFileManager()
        assert temp_file_manager is instance
