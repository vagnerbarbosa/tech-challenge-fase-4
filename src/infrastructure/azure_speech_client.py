"""Cliente Azure Speech Services para transcrição de áudio."""

import asyncio
import tempfile
from functools import lru_cache
from pathlib import Path
from typing import Any

import azure.cognitiveservices.speech as speechsdk
import librosa
import soundfile as sf
from azure.cognitiveservices.speech import (
    PropertyId,
    ResultReason,
    SpeechConfig,
    SpeechRecognizer,
)
from structlog import get_logger

from src.core.config import get_settings
from src.core.exceptions import (
    AzureAuthenticationError,
    AzureQuotaExceededError,
    AzureServiceError,
)

logger = get_logger()

# Idiomas suportados para auto-detecção
DEFAULT_SUPPORTED_LANGUAGES = ["pt-BR", "en-US", "es-ES", "fr-FR", "de-DE", "it-IT"]


@lru_cache
def get_speech_config() -> SpeechConfig | None:
    """Retorna configuração singleton do Azure Speech.

    Returns:
        SpeechConfig configurada ou None se credenciais não disponíveis
    """
    settings = get_settings()

    # Verifica se a chave é válida (não vazia, não é fake/mock)
    if not settings.azure_speech_key or settings.azure_speech_key in (
        "fake-key-for-local-dev",
        "mock",
        "test",
        "",
    ):
        logger.warning("azure_speech_key não configurada, usando modo mock")
        return None

    return SpeechConfig(
        subscription=settings.azure_speech_key,
        region=settings.azure_speech_region,
    )


class AzureSpeechClient:
    """Cliente para Azure Speech Services.

    Responsável por:
    - Transcrição de áudio (Speech-to-Text)
    - Detecção de idioma automática
    - Configuração de timeout e retry
    """

    def __init__(self) -> None:
        self.config = get_speech_config()
        self.settings = get_settings()
        self.mock_mode = self.config is None

    def _convert_to_wav(self, audio_path: Path) -> Path:
        """Converte áudio para WAV (PCM) compatível com Azure Speech.

        Args:
            audio_path: Caminho para o arquivo de áudio original

        Returns:
            Path para arquivo WAV temporário
        """
        import time

        suffix = audio_path.suffix.lower()

        # Se já for WAV, retorna o mesmo arquivo
        if suffix == ".wav":
            return audio_path

        # Para MP3 e OGG, converte para WAV
        if suffix in (".mp3", ".ogg"):
            try:
                start_time = time.perf_counter()

                # Carrega com librosa (suporta MP3 e OGG)
                y, sr = librosa.load(str(audio_path), sr=16000, mono=True)
                load_time = time.perf_counter() - start_time

                # Cria arquivo WAV temporário
                with tempfile.NamedTemporaryFile(
                    suffix=".wav", delete=False, mode="wb"
                ) as temp_wav:
                    # Salva como WAV PCM
                    sf.write(temp_wav.name, y, sr, subtype="PCM_16")
                    wav_path = temp_wav.name

                total_time = time.perf_counter() - start_time

                logger.info(
                    "audio_converted_to_wav",
                    original=str(audio_path),
                    wav_file=wav_path,
                    duration=len(y) / sr,
                    load_time_ms=int(load_time * 1000),
                    total_time_ms=int(total_time * 1000),
                )

                return Path(wav_path)

            except Exception as e:
                logger.error(
                    "audio_conversion_failed",
                    original=str(audio_path),
                    error=str(e),
                )
                # Retorna o arquivo original se a conversão falhar
                return audio_path

        # Para outros formatos, tenta o arquivo original
        return audio_path

    async def transcribe(
        self,
        audio_path: Path,
        language: str | None = None,
        timeout_secs: int = 60,
        auto_detect_languages: list[str] | None = None,
    ) -> dict[str, Any]:
        """Transcreve arquivo de áudio usando Azure Speech.

        Args:
            audio_path: Caminho para o arquivo de áudio
            language: Código do idioma (deprecated, use auto_detect_languages)
            timeout_secs: Timeout em segundos
            auto_detect_languages: Lista de idiomas candidatos para auto-detecção.
                Se None, usa DEFAULT_SUPPORTED_LANGUAGES.

        Returns:
            Dict com transcricao, confiança, idioma_detectado

        Raises:
            AzureAuthenticationError: Se credenciais inválidas
            AzureQuotaExceededError: Se quota excedida
            AzureServiceError: Se erro no serviço Azure
            TimeoutError: Se timeout excedido
        """
        # Mock mode: retorna transcrição simulada
        if self.mock_mode:
            logger.info("azure_speech_mock_mode", audio_file=str(audio_path))
            detected_lang = language if language else auto_detect_languages[0] if auto_detect_languages else "pt-BR"
            return {
                "transcricao": "[MOCK] Transcrição simulada para desenvolvimento",
                "confianca": 0.85,
                "idioma_detectado": detected_lang,
                "sucesso": True,
                "mock": True,
            }

        # Converte para WAV se necessário (MP3/OGG)
        wav_path = self._convert_to_wav(audio_path)
        temp_wav_created = wav_path != audio_path
        recognizer: SpeechRecognizer | None = None

        try:
            # Configura idioma (self.config não é None aqui pois mock_mode é False)
            assert self.config is not None  # noqa: S101

            # Cria audio config
            audio_config = speechsdk.audio.AudioConfig(filename=str(wav_path))

            # Determina modo: idioma fixo ou auto-detecção
            use_auto_detect = language is None
            detected_language: str = "pt-BR"  # default

            if use_auto_detect:
                # Usa auto-detecção de idioma com SpeechRecognizer + auto_detect_config
                languages = auto_detect_languages or DEFAULT_SUPPORTED_LANGUAGES
                auto_detect_config = speechsdk.languageconfig.AutoDetectSourceLanguageConfig(
                    languages=languages
                )

                # SpeechRecognizer com auto-detecção
                recognizer = SpeechRecognizer(
                    speech_config=self.config,
                    audio_config=audio_config,
                    auto_detect_source_language_config=auto_detect_config,
                )

                logger.info(
                    "azure_speech_transcribe_auto_detect_started",
                    audio_file=str(audio_path),
                    candidate_languages=languages,
                )

                def _recognize_auto() -> speechsdk.SpeechRecognitionResult:
                    assert recognizer is not None  # noqa: S101
                    future: speechsdk.ResultFuture = recognizer.recognize_once_async()
                    result: speechsdk.SpeechRecognitionResult = future.get()
                    return result

                result = await asyncio.wait_for(
                    asyncio.to_thread(_recognize_auto),
                    timeout=timeout_secs,
                )

                # Extrai idioma detectado das propriedades do resultado
                if result.reason == ResultReason.RecognizedSpeech:
                    detected_language = result.properties.get(
                        PropertyId.SpeechServiceConnection_AutoDetectSourceLanguageResult,
                        "pt-BR"
                    )
                    logger.info(
                        "azure_speech_auto_detect_success",
                        detected_language=detected_language,
                        text_length=len(result.text),
                    )

            else:
                # Modo legado: idioma fixo (para compatibilidade)
                # language não é None aqui pois use_auto_detect = (language is None)
                assert language is not None  # noqa: S101
                self.config.speech_recognition_language = language
                detected_language = language

                recognizer = SpeechRecognizer(
                    speech_config=self.config,
                    audio_config=audio_config,
                )

                logger.info(
                    "azure_speech_transcribe_started",
                    audio_file=str(audio_path),
                    language=language,
                )

                def _recognize() -> speechsdk.SpeechRecognitionResult:
                    assert recognizer is not None  # noqa: S101
                    future: speechsdk.ResultFuture = recognizer.recognize_once_async()
                    result: speechsdk.SpeechRecognitionResult = future.get()
                    return result

                result = await asyncio.wait_for(
                    asyncio.to_thread(_recognize),
                    timeout=timeout_secs,
                )

            # Processa resultado (comum para ambos os modos)
            if result.reason == ResultReason.RecognizedSpeech:
                logger.info(
                    "azure_speech_transcribe_success",
                    text_length=len(result.text),
                    confidence=result.confidence,
                    detected_language=detected_language,
                )
                return {
                    "transcricao": result.text,
                    "confianca": result.confidence,
                    "idioma_detectado": detected_language,
                    "sucesso": True,
                }

            elif result.reason == ResultReason.NoMatch:
                logger.warning(
                    "azure_speech_no_match",
                    detected_language=detected_language,
                )
                return {
                    "transcricao": "",
                    "confianca": 0.0,
                    "idioma_detectado": detected_language,
                    "sucesso": False,
                    "erro": "Nenhuma fala detectada no áudio",
                }

            elif result.reason == ResultReason.Canceled:
                cancellation_details = result.cancellation_details
                error_msg = f"Transcrição cancelada: {cancellation_details.reason}"
                logger.error(
                    "azure_speech_canceled",
                    reason=cancellation_details.reason,
                    error_details=cancellation_details.error_details,
                )

                if "Authentication" in str(cancellation_details.error_details):
                    raise AzureAuthenticationError("Credenciais Azure Speech inválidas")

                raise AzureServiceError(error_msg)

            else:
                logger.error("azure_speech_unknown_reason", reason=str(result.reason))
                raise AzureServiceError(f"Erro desconhecido: {result.reason}")

        except TimeoutError:
            logger.error("azure_speech_timeout", timeout=timeout_secs)
            raise TimeoutError(f"Tempo limite excedido ({timeout_secs}s)") from None

        except Exception as e:
            logger.error("azure_speech_error", error=str(e))
            raise

        finally:
            # Cleanup
            if recognizer is not None:
                recognizer = None

            # Remove arquivo WAV temporário se foi criado
            if temp_wav_created and wav_path.exists():
                try:
                    wav_path.unlink()
                    logger.debug("temp_wav_cleaned", temp_path=str(wav_path))
                except Exception as e:
                    logger.warning("temp_wav_cleanup_failed", error=str(e))

    async def transcribe_with_retry(
        self,
        audio_path: Path,
        language: str | None = None,
        max_retries: int = 2,
        auto_detect_languages: list[str] | None = None,
    ) -> dict[str, Any]:
        """Transcreve com retry automático em caso de falha.

        Args:
            audio_path: Caminho para o arquivo de áudio
            language: Código do idioma (None para auto-detect)
            max_retries: Número máximo de tentativas
            auto_detect_languages: Lista de idiomas candidatos para auto-detecção

        Returns:
            Resultado da transcrição
        """
        for attempt in range(max_retries + 1):
            try:
                return await self.transcribe(
                    audio_path,
                    language=language,
                    auto_detect_languages=auto_detect_languages,
                )
            except AzureQuotaExceededError:
                raise  # Não retry em quota excedida
            except AzureAuthenticationError:
                raise  # Não retry em auth error
            except Exception as e:
                if attempt == max_retries:
                    raise
                logger.warning(
                    "azure_speech_retry",
                    attempt=attempt + 1,
                    max_retries=max_retries,
                    error=str(e),
                )
                await asyncio.sleep(1 * (attempt + 1))  # Backoff exponencial

        return {"transcricao": "", "sucesso": False, "erro": "Max retries exceeded"}
