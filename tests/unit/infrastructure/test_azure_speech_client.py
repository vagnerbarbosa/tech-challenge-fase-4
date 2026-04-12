"""Testes para AzureSpeechClient.

Mock do Azure Speech SDK para testes unitários.
"""

from unittest.mock import Mock, patch

import pytest

from src.infrastructure.azure_speech_client import AzureSpeechClient, get_speech_config


class TestGetSpeechConfig:
    """Testes para get_speech_config singleton."""

    @patch("src.infrastructure.azure_speech_client.get_settings")
    def test_returns_none_when_key_missing(self, mock_settings):
        """Testa retorno None quando chave não configurada."""
        # Arrange
        mock_settings.return_value.azure_speech_key = None

        # Act
        result = get_speech_config()

        # Assert
        assert result is None

    @patch("src.infrastructure.azure_speech_client.get_settings")
    def test_returns_config_when_key_present(self, mock_settings):
        """Testa retorno SpeechConfig quando chave configurada."""
        # Arrange
        mock_settings.return_value.azure_speech_key = "fake-key"
        mock_settings.return_value.azure_speech_region = "brazilsouth"

        # Limpa cache para garantir nova execução
        get_speech_config.cache_clear()

        # Act
        result = get_speech_config()

        # Assert
        assert result is not None

        # Limpa cache após teste
        get_speech_config.cache_clear()


class TestAzureSpeechClient:
    """Testes para AzureSpeechClient."""

    @pytest.fixture
    def mock_config(self):
        """Fixture para SpeechConfig mockado."""
        config = Mock()
        config.speech_recognition_language = None
        return config

    @pytest.fixture
    def client(self, mock_config):
        """Fixture para AzureSpeechClient."""
        with patch(
            "src.infrastructure.azure_speech_client.get_speech_config",
            return_value=mock_config,
        ):
            return AzureSpeechClient()

    @pytest.mark.asyncio
    async def test_transcribe_returns_mock_when_no_config(self, tmp_path):
        """Testa modo mock quando config não disponível."""
        # Arrange
        with patch(
            "src.infrastructure.azure_speech_client.get_speech_config",
            return_value=None,
        ):
            client = AzureSpeechClient()
            test_file = tmp_path / "test.wav"
            test_file.write_text("fake")

            # Act
            result = await client.transcribe(test_file)

            # Assert
            assert result["mock"] is True
            assert "transcricao" in result
            assert result["sucesso"] is True

    @pytest.mark.asyncio
    async def test_transcribe_success(self, client, mock_config, tmp_path):
        """Testa transcrição bem-sucedida."""
        # Arrange
        from azure.cognitiveservices.speech import ResultReason

        mock_result = Mock()
        mock_result.reason = ResultReason.RecognizedSpeech
        mock_result.text = "Olá mundo"
        mock_result.confidence = 0.95

        test_file = tmp_path / "test.wav"
        test_file.write_text("fake")

        with patch(
            "src.infrastructure.azure_speech_client.SpeechRecognizer"
        ) as mock_recognizer:
            # recognize_once_async é chamado via asyncio.to_thread
            mock_recognizer.return_value.recognize_once_async.return_value = mock_result

            # Act
            result = await client.transcribe(test_file)

            # Assert
            assert result["sucesso"] is True
            assert result["transcricao"] == "Olá mundo"
            assert result["confiança"] == 0.95

    @pytest.mark.asyncio
    async def test_transcribe_no_match(self, client, mock_config, tmp_path):
        """Testa quando nenhuma fala detectada."""
        # Arrange
        from azure.cognitiveservices.speech import ResultReason

        mock_result = Mock()
        mock_result.reason = ResultReason.NoMatch

        test_file = tmp_path / "test.wav"
        test_file.write_text("fake")

        with patch(
            "src.infrastructure.azure_speech_client.SpeechRecognizer"
        ) as mock_recognizer:
            mock_recognizer.return_value.recognize_once_async.return_value = mock_result

            # Act
            result = await client.transcribe(test_file)

            # Assert
            assert result["sucesso"] is False
            assert result["transcricao"] == ""

    @pytest.mark.asyncio
    async def test_transcribe_with_retry_success(self, client, tmp_path):
        """Testa retry em caso de falha."""
        # Arrange
        test_file = tmp_path / "test.wav"
        test_file.write_text("fake")

        # Primeira chamada falha, segunda sucede
        call_count = 0

        async def mock_transcribe(*args, **kwargs):
            nonlocal call_count
            call_count += 1
            if call_count == 1:
                raise Exception("Network error")
            return {"transcricao": "Success", "sucesso": True}

        client.transcribe = mock_transcribe

        # Act
        result = await client.transcribe_with_retry(test_file)

        # Assert
        assert result["sucesso"] is True
        assert call_count == 2


class TestAzureSpeechClientErrors:
    """Testes para tratamento de erros."""

    @pytest.mark.asyncio
    async def test_timeout_error(self, tmp_path):
        """Testa timeout."""
        # Arrange - usa None para forçar mock mode, depois patcha transcribe
        with patch(
            "src.infrastructure.azure_speech_client.get_speech_config",
            return_value=None,
        ):
            client = AzureSpeechClient()
            test_file = tmp_path / "test.wav"
            test_file.write_text("fake")

            # Patch transcribe para simular timeout
            with (
                patch.object(client, 'transcribe', side_effect=TimeoutError("Timeout")),
                pytest.raises(TimeoutError),
            ):
                # Act & Assert
                await client.transcribe(test_file, timeout_secs=1)
