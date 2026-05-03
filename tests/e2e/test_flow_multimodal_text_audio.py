"""Testes E2E para fluxo multimodal texto+áudio.

Spec 011 - Testing Strategy E2E
User Story 3: E2E Tests
E2E-007: Fusão multimodal texto+áudio.
"""

import requests


class TestE2EMultimodal:
    """Testes E2E para fluxo multimodal (E2E-007)."""

    def test_e2e_multimodal_text_audio(
        self, e2e_client: requests.Session, api_url: str, sample_audio_path: str
    ) -> None:
        """
        E2E-007: Fusão multimodal texto+áudio.
        Valida: fusão com confiança, metadados
        """
        # Arrange
        texto = (
            "Estou me sentindo muito ansiosa e com medo constante. "
            "Não sei mais o que fazer com a situação."
        )
        patient_id = "e2e-multimodal-001"

        # Act: Enviar requisição multipart com texto e áudio
        with open(sample_audio_path, "rb") as audio_file:
            data = {
                "texto": texto,
                "patient_id": patient_id,
            }
            files = {
                "audio": ("sample.wav", audio_file, "audio/wav"),
            }

            response = e2e_client.post(
                f"{api_url}/analyze/multimodal",
                data=data,
                files=files,
                timeout=90,  # Timeout maior para processamento multimodal
            )

        # Assert Response Status
        assert response.status_code == 200, (
            f"Expected 200, got {response.status_code}: {response.text}"
        )

        # Parse Response
        result = response.json()

        # Assert: Estrutura completa presente
        assert "fusao" in result, "Campo 'fusao' não encontrado"
        assert "texto" in result, "Campo 'texto' não encontrado (resultado individual)"
        assert "audio" in result, "Campo 'audio' não encontrado (resultado individual)"
        assert "metadata" in result, "Campo 'metadata' não encontrado"

        # Assert: Validação da fusão
        fusao = result["fusao"]
        assert "risco_violencia" in fusao, "Campo 'risco_violencia' não encontrado na fusão"
        assert "risco_saude_mental" in fusao, "Campo 'risco_saude_mental' não encontrado na fusão"
        assert "confianca" in fusao, "Campo 'confianca' não encontrado na fusão"
        assert "alerta" in fusao, "Campo 'alerta' não encontrado na fusão"

        # Assert: Valores da fusão são válidos
        assert fusao["risco_violencia"] in ["baixo", "medio", "alto"]
        assert fusao["risco_saude_mental"] in ["baixo", "medio", "alto"]
        assert 0.0 <= fusao["confianca"] <= 1.0, (
            f"Confiança deve estar entre 0.0 e 1.0, got {fusao['confianca']}"
        )
        assert isinstance(fusao["alerta"], bool)

        # Assert: Resultados individuais presentes
        assert result["texto"]["sentimento"] in ["positivo", "negativo", "neutro", "misto"]
        assert "score" in result["texto"]
        assert -1.0 <= result["texto"]["score"] <= 1.0

        assert "transcricao" in result["audio"]
        assert "idioma_detectado" in result["audio"]
        assert "voz_tremida" in result["audio"]

        # Assert: Metadata
        metadata = result["metadata"]
        assert "correlation_id" in metadata
        assert "tempo_processamento_ms" in metadata
        assert metadata["tempo_processamento_ms"] > 0
        assert metadata["tempo_processamento_ms"] < 90000, (
            "Processamento deve levar menos que 90s"
        )

        # Assert: Modalidades processadas
        assert "modalidades_processadas" in metadata
        modalities = metadata["modalidades_processadas"]
        assert isinstance(modalities, list)
        assert "texto" in modalities
        assert "audio" in modalities
