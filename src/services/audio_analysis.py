"""Serviço de análise de áudio com Azure Speech e prosódica.

Este serviço combina:
- Transcrição via Azure Speech Services
- Análise prosódica (pitch, energia, pausas) via librosa
- Detecção de risco baseada em palavras-chave
"""

import asyncio
from dataclasses import dataclass
from pathlib import Path
from time import perf_counter
from typing import Any

import librosa
import numpy as np
from structlog import get_logger

from src.core.config import get_settings
from src.core.security.log_sanitizer import PatientIdHasher
from src.infrastructure.azure_speech_client import AzureSpeechClient
from src.services.risk_detector import calculate_risk

logger = get_logger()


@dataclass
class ProsodicFeatures:
    """Features prosódicas extraídas do áudio."""

    voz_tremida: bool
    pausas_suspeitas: int
    entonacao: str
    variacao_pitch: float
    variacao_energia: float
    duracao_segundos: float


class ProsodicFeatureExtractor:
    """Extrai features prosódicas para análise de risco usando librosa."""

    # Thresholds para classificação
    VOICE_TREMOR_THRESHOLD = 50.0  # Hz (pitch std)
    AGITATED_THRESHOLD = 0.15      # RMS std
    HESITANT_THRESHOLD = 0.08      # RMS std
    CALM_MAX_MEAN = 0.05           # RMS mean

    def __init__(self, sample_rate: int = 16000):
        self.sample_rate = sample_rate

    async def extract(self, audio_path: Path) -> ProsodicFeatures:
        """Extrai features prosódicas do arquivo de áudio.

        Args:
            audio_path: Caminho para o arquivo de áudio

        Returns:
            ProsodicFeatures com análise do áudio
        """
        try:
            # Carrega áudio
            y, sr = librosa.load(str(audio_path), sr=self.sample_rate, mono=True)
            duracao = librosa.get_duration(y=y, sr=sr)

            # Extrai pitch (F0)
            pitches, magnitudes = librosa.piptrack(y=y, sr=sr)
            pitch_mask = magnitudes > np.median(magnitudes)
            pitch_values = pitches[pitch_mask]

            # Variação de pitch (indicativo de tremor na voz)
            pitch_variation = float(np.std(pitch_values) if len(pitch_values) > 0 else 0)
            voz_tremida = bool(pitch_variation > self.VOICE_TREMOR_THRESHOLD)

            # Energia (volume)
            rms = librosa.feature.rms(y=y)[0]
            energy_variation = np.std(rms)
            energy_mean = np.mean(rms)

            # Entonação baseada na variação de energia
            if energy_variation > self.AGITATED_THRESHOLD:
                entonacao = "agitado"
            elif energy_variation > self.HESITANT_THRESHOLD:
                entonacao = "hesitante"
            elif energy_mean < self.CALM_MAX_MEAN:
                entonacao = "calmo"
            else:
                entonacao = "normal"

            # Pausas (silêncios)
            intervals = librosa.effects.split(y, top_db=20)
            pauses = max(0, len(intervals) - 1)

            return ProsodicFeatures(
                voz_tremida=voz_tremida,
                pausas_suspeitas=pauses,
                entonacao=entonacao,
                variacao_pitch=pitch_variation,
                variacao_energia=energy_variation,
                duracao_segundos=duracao,
            )

        except Exception as e:
            logger.error("prosodic_extraction_failed", error=str(e))
            # Retorna valores padrão em caso de erro
            return ProsodicFeatures(
                voz_tremida=False,
                pausas_suspeitas=0,
                entonacao="normal",
                variacao_pitch=0.0,
                variacao_energia=0.0,
                duracao_segundos=0.0,
            )


class AudioAnalysisService:
    """Serviço principal de análise de áudio."""

    def __init__(self) -> None:
        self.speech_client = AzureSpeechClient()
        self.prosodic_extractor = ProsodicFeatureExtractor()
        self.settings = get_settings()

    async def analyze(
        self,
        audio_path: Path,
        patient_id: str | None = None,
    ) -> dict[str, Any]:
        """Analisa arquivo de áudio completo.

        Fluxo:
        1. Extrai features prosódicas (librosa)
        2. Transcreve áudio (Azure Speech)
        3. Analisa sentimento e risco na transcrição
        4. Combina resultados

        Args:
            audio_path: Caminho para o arquivo de áudio
            patient_id: ID opcional do paciente

        Returns:
            Dict com análise completa
        """
        start_time = perf_counter()

        logger.info(
            "audio_analysis_started",
            audio_file=str(audio_path),
            patient_id=PatientIdHasher.hash(patient_id),
        )

        try:
            # 1. Extrai features prosódicas e transcrição em paralelo
            prosodic_task = self.prosodic_extractor.extract(audio_path)
            transcribe_task = self.speech_client.transcribe_with_retry(audio_path)

            # Executa em paralelo
            prosodic_features, transcribe_result = await asyncio.gather(
                prosodic_task,
                transcribe_task,
            )

            transcricao = transcribe_result.get("transcricao", "")

            # 2. Analisa risco na transcrição
            if transcricao:
                risk_scores = calculate_risk(
                    transcricao,
                    sentiment="negativo",
                    confidence_scores={"negativo": 0.7, "positivo": 0.1, "neutro": 0.2},
                )
                sentimento = risk_scores.get("sentimento", "negativo")

                # Ajusta risco baseado em features prosódicas
                risco_violencia = self._adjust_risk(
                    risk_scores.get("risco_violencia", "baixo"),
                    prosodic_features,
                    "violencia",
                )
                risco_saude_mental = self._adjust_risk(
                    risk_scores.get("risco_saude_mental", "baixo"),
                    prosodic_features,
                    "saude_mental",
                )
            else:
                sentimento = "neutro"
                risco_violencia = "baixo"
                risco_saude_mental = "baixo"

            duration = perf_counter() - start_time

            # 3. Monta resultado
            result = {
                "transcricao": transcricao,
                "idioma_detectado": transcribe_result.get("idioma_detectado", "pt-BR"),
                "sentimento": sentimento,
                "entonação": prosodic_features.entonacao,
                "voz_tremida": prosodic_features.voz_tremida,
                "pausas_suspeitas": prosodic_features.pausas_suspeitas,
                "duracao_segundos": prosodic_features.duracao_segundos,
                "risco_violencia": risco_violencia,
                "risco_saude_mental": risco_saude_mental,
            }

            logger.info(
                "audio_analysis_completed",
                duration_seconds=duration,
                transcription_length=len(transcricao),
                risco_violencia=risco_violencia,
                risco_saude_mental=risco_saude_mental,
                voz_tremida=prosodic_features.voz_tremida,
            )

            return result

        except Exception as e:
            logger.error("audio_analysis_failed", error=str(e))
            raise

    def _adjust_risk(
        self,
        base_risk: str,
        features: ProsodicFeatures,
        risk_type: str,
    ) -> str:
        """Ajusta nível de risco baseado em features prosódicas.

        Args:
            base_risk: Risco base da análise de texto
            features: Features prosódicas
            risk_type: Tipo de risco (violencia ou saude_mental)

        Returns:
            Risco ajustado (baixo, medio, alto)
        """
        risk_levels = ["baixo", "medio", "alto"]
        base_index = risk_levels.index(base_risk)

        # Fatores que aumentam o risco
        risk_factors = 0

        if features.voz_tremida:
            risk_factors += 1  # Tremor na voz = possível ansiedade/stress

        if features.pausas_suspeitas > 5:
            risk_factors += 1  # Muitas pausas = hesitação

        if features.entonacao == "hesitante":
            risk_factors += 1

        # Ajusta risco (não pode ultrapassar "alto")
        adjusted_index = min(base_index + risk_factors, 2)
        return risk_levels[adjusted_index]


# Instância singleton
audio_analysis_service = AudioAnalysisService()
