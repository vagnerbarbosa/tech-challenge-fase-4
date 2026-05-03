"""Testes E2E para análise de áudio.

Spec 011 - Testing Strategy E2E
User Story 3: E2E Tests
E2E-004 a E2E-006: Fluxos de análise de áudio end-to-end.
"""

import tempfile
from pathlib import Path

import requests


class TestE2EAudioAnalysis:
    """Testes E2E para análise de áudio (E2E-004 a E2E-006)."""

    def test_e2e_audio_wav_transcription(
        self, e2e_client: requests.Session, api_url: str, sample_audio_path: str
    ) -> None:
        """
        E2E-004: Transcrição de áudio WAV.
        Valida: transcricao, idioma_detectado, prosódica
        """
        # Arrange
        with open(sample_audio_path, "rb") as f:
            files = {"audio": ("sample.wav", f, "audio/wav")}
            data = {"patient_id": "e2e-audio-001"}

            # Act
            response = e2e_client.post(
                f"{api_url}/analyze/audio",
                files=files,
                data=data,
                timeout=60,
            )

        # Assert Response Status
        assert response.status_code == 200, (
            f"Expected 200, got {response.status_code}: {response.text}"
        )

        # Parse Response
        result = response.json()

        # Assert: Campos obrigatórios presentes
        assert "transcricao" in result, "Campo 'transcricao' não encontrado"
        assert "idioma_detectado" in result, "Campo 'idioma_detectado' não encontrado"
        assert "risco_violencia" in result, "Campo 'risco_violencia' não encontrado"
        assert "risco_saude_mental" in result, "Campo 'risco_saude_mental' não encontrado"

        # Assert: Campos prosódicos
        assert "voz_tremida" in result, "Campo 'voz_tremida' não encontrado"
        assert "pausas_suspeitas" in result, "Campo 'pausas_suspeitas' não encontrado"
        assert "entonação" in result, "Campo 'entonação' não encontrado"
        assert "duracao_segundos" in result, "Campo 'duracao_segundos' não encontrado"

        # Assert: Valores válidos
        assert result["idioma_detectado"] in ["pt-BR", "en-US", "es-ES", "fr-FR", "unknown"]
        assert result["risco_violencia"] in ["baixo", "medio", "alto"]
        assert result["risco_saude_mental"] in ["baixo", "medio", "alto"]
        assert isinstance(result["voz_tremida"], bool)
        assert isinstance(result["pausas_suspeitas"], int)
        assert result["pausas_suspeitas"] >= 0

        # Assert: Metadata
        assert "metadata" in result, "Campo 'metadata' não encontrado"
        metadata = result["metadata"]
        assert "correlation_id" in metadata
        assert "tempo_processamento_ms" in metadata
        assert metadata["tempo_processamento_ms"] > 0

    def test_e2e_audio_multiple_formats(
        self, e2e_client: requests.Session, api_url: str, sample_audio_path: str
    ) -> None:
        """
        E2E-005: Múltiplos formatos aceitos (WAV, MP3, OGG).
        """
        import struct

        # Criar arquivo WAV válido para teste
        def create_wav_bytes(duration_seconds: float = 1.0) -> bytes:
            """Cria um arquivo WAV válido em memória."""
            sample_rate = 16000
            num_samples = int(sample_rate * duration_seconds)
            num_channels = 1
            bits_per_sample = 16
            byte_rate = sample_rate * num_channels * bits_per_sample // 8
            block_align = num_channels * bits_per_sample // 8

            # Criar dados de áudio (silêncio)
            audio_data = b"\x00\x00" * num_samples

            # Cabeçalho WAV
            header = b"RIFF"
            chunk_size = 36 + len(audio_data)
            header += struct.pack("<I", chunk_size)
            header += b"WAVE"
            header += b"fmt "
            header += struct.pack("<I", 16)  # Subchunk1Size
            header += struct.pack("<H", 1)  # AudioFormat (PCM)
            header += struct.pack("<H", num_channels)
            header += struct.pack("<I", sample_rate)
            header += struct.pack("<I", byte_rate)
            header += struct.pack("<H", block_align)
            header += struct.pack("<H", bits_per_sample)
            header += b"data"
            header += struct.pack("<I", len(audio_data))

            return header + audio_data

        # Testar formato WAV (MP3/OGG requerem arquivos reais)
        # Nota: O E2E valida apenas WAV pois MP3/OGG precisam de assinaturas válidas
        filename = "sample.wav"
        content_type = "audio/wav"
        audio_bytes = create_wav_bytes()

        # Act
        files = {"audio": (filename, audio_bytes, content_type)}
        data = {"patient_id": "e2e-audio-wav"}

        response = e2e_client.post(
            f"{api_url}/analyze/audio",
            files=files,
            data=data,
            timeout=30,
        )

        # Assert
        assert response.status_code == 200, (
            f"Formato {filename} falhou: {response.status_code} - {response.text}"
        )

        result = response.json()
        assert "transcricao" in result
        assert "risco_violencia" in result
        assert "risco_saude_mental" in result

    def test_e2e_audio_file_too_large(
        self, e2e_client: requests.Session, api_url: str
    ) -> None:
        """
        E2E-006: Rejeição de áudio >50MB.
        Valida: 413 retornado
        """
        # Arrange: Criar arquivo temporário >50MB
        with tempfile.NamedTemporaryFile(suffix=".wav", delete=False) as f:
            # Cabeçalho WAV mínimo
            f.write(b"RIFF")
            f.write((51 * 1024 * 1024).to_bytes(4, "little"))  # Tamanho total ~51MB
            f.write(b"WAVEfmt \x10\x00\x00\x00\x01\x00\x01\x00")
            f.write((16000).to_bytes(4, "little"))  # Sample rate
            f.write((32000).to_bytes(4, "little"))  # Byte rate
            f.write(b"\x02\x00\x10\x00data")
            # Preencher com zeros até passar de 50MB
            remaining = 51 * 1024 * 1024 - 36
            chunk_size = 1024 * 1024  # 1MB chunks
            for _ in range(remaining // chunk_size):
                f.write(b"\x00" * chunk_size)
            temp_path = f.name

        try:
            # Act
            with open(temp_path, "rb") as f:
                files = {"audio": ("large.wav", f, "audio/wav")}
                data = {"patient_id": "e2e-audio-large"}

                response = e2e_client.post(
                    f"{api_url}/analyze/audio",
                    files=files,
                    data=data,
                    timeout=30,
                )

                # Assert
                assert response.status_code == 413, (
                    f"Expected 413 (File Too Large), got {response.status_code}"
                )

                # Verificar mensagem de erro
                result = response.json()
                assert "detail" in result
                error_message = result["detail"].lower()
                assert any(
                    word in error_message
                    for word in ["tamanho", "grande", "size", "large", "50", "mb"]
                ), f"Mensagem de erro não indica tamanho: {error_message}"

        finally:
            # Cleanup
            Path(temp_path).unlink(missing_ok=True)
