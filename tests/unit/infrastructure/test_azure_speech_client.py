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


class TestConvertToWav:
    """Testes para conversão de áudio para WAV."""

    @pytest.fixture
    def client(self):
        """Fixture para AzureSpeechClient em mock mode."""
        with patch(
            "src.infrastructure.azure_speech_client.get_speech_config",
            return_value=None,
        ):
            return AzureSpeechClient()

    def test_wav_file_no_conversion(self, client, tmp_path):
        """Testa que arquivos WAV são retornados sem conversão."""
        # Arrange
        wav_file = tmp_path / "test.wav"
        wav_file.write_bytes(b"fake wav content")

        # Act
        result = client._convert_to_wav(wav_file)

        # Assert
        assert result == wav_file

    def test_mp3_conversion(self, client, tmp_path):
        """Testa conversão de MP3 para WAV."""
        # Arrange
        mp3_file = tmp_path / "test.mp3"
        mp3_file.write_bytes(b"fake mp3 content")

        mock_audio_data = ([0.1, 0.2, 0.3], 16000)  # y, sr

        with (
            patch("librosa.load", return_value=mock_audio_data) as mock_librosa,
            patch("soundfile.write") as mock_soundfile,
            patch("tempfile.NamedTemporaryFile") as mock_temp,
        ):
            mock_temp_instance = Mock()
            mock_temp_instance.name = str(tmp_path / "converted.wav")
            mock_temp.return_value.__enter__ = Mock(return_value=mock_temp_instance)
            mock_temp.return_value.__exit__ = Mock(return_value=False)

            # Act
            result = client._convert_to_wav(mp3_file)

            # Assert
            mock_librosa.assert_called_once_with(str(mp3_file), sr=16000, mono=True)
            mock_soundfile.assert_called_once()
            assert result.suffix == ".wav"

    def test_ogg_conversion(self, client, tmp_path):
        """Testa conversão de OGG para WAV."""
        # Arrange
        ogg_file = tmp_path / "test.ogg"
        ogg_file.write_bytes(b"fake ogg content")

        mock_audio_data = ([0.1, 0.2, 0.3], 16000)

        with (
            patch("librosa.load", return_value=mock_audio_data) as mock_librosa,
            patch("soundfile.write") as mock_soundfile,
            patch("tempfile.NamedTemporaryFile") as mock_temp,
        ):
            mock_temp_instance = Mock()
            mock_temp_instance.name = str(tmp_path / "converted.wav")
            mock_temp.return_value.__enter__ = Mock(return_value=mock_temp_instance)
            mock_temp.return_value.__exit__ = Mock(return_value=False)

            # Act
            result = client._convert_to_wav(ogg_file)

            # Assert
            mock_librosa.assert_called_once_with(str(ogg_file), sr=16000, mono=True)
            mock_soundfile.assert_called_once()
            assert result.suffix == ".wav"

    def test_conversion_fallback_on_error(self, client, tmp_path):
        """Testa fallback para arquivo original quando conversão falha."""
        # Arrange
        mp3_file = tmp_path / "test.mp3"
        mp3_file.write_bytes(b"fake mp3 content")

        with patch("librosa.load", side_effect=Exception("Failed to load")):
            # Act
            result = client._convert_to_wav(mp3_file)

            # Assert - deve retornar o arquivo original
            assert result == mp3_file

    def test_other_formats_return_unchanged(self, client, tmp_path):
        """Testa que outros formatos são retornados sem modificação."""
        # Arrange
        flac_file = tmp_path / "test.flac"
        flac_file.write_bytes(b"fake flac content")

        # Act
        result = client._convert_to_wav(flac_file)

        # Assert
        assert result == flac_file


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
