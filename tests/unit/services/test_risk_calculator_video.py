"""Testes unitários para risk_calculator_video.

Testes para a calculadora de risco de vídeo.
"""

import sys
from pathlib import Path

# Adicionar src ao path
sys.path.insert(0, str(Path(__file__).parent.parent.parent.parent / "src"))

from src.services.risk_calculator_video import _combine_risk_levels, calculate_video_risk


class TestCombineRiskLevels:
    """Testes para a função _combine_risk_levels."""

    def test_alto_takes_priority_over_medio(self):
        """Risco alto deve ter prioridade sobre médio."""
        assert _combine_risk_levels("alto", "medio") == "alto"
        assert _combine_risk_levels("medio", "alto") == "alto"

    def test_alto_takes_priority_over_baixo(self):
        """Risco alto deve ter prioridade sobre baixo."""
        assert _combine_risk_levels("alto", "baixo") == "alto"
        assert _combine_risk_levels("baixo", "alto") == "alto"

    def test_medio_takes_priority_over_baixo(self):
        """Risco médio deve ter prioridade sobre baixo."""
        assert _combine_risk_levels("medio", "baixo") == "medio"
        assert _combine_risk_levels("baixo", "medio") == "medio"

    def test_same_levels_return_same(self):
        """Mesmos níveis devem retornar o mesmo valor."""
        assert _combine_risk_levels("alto", "alto") == "alto"
        assert _combine_risk_levels("medio", "medio") == "medio"
        assert _combine_risk_levels("baixo", "baixo") == "baixo"

    def test_unknown_uses_fallback(self):
        """Valores desconhecidos usam fallback para baixo."""
        assert _combine_risk_levels("unknown", "baixo") == "baixo"
        assert _combine_risk_levels("baixo", "unknown") == "baixo"


class TestCalculateVideoRisk:
    """Testes para a função calculate_video_risk."""

    def test_empty_detections_returns_low_risk(self):
        """Lista vazia de detecções retorna risco baixo."""
        result = calculate_video_risk([])

        assert result["risco_violencia"] == "baixo"
        assert result["risco_saude_mental"] == "baixo"
        assert result["alertas"] == []
        assert result["deteccoes"] == []

    def test_person_detection_no_risk(self):
        """Detecção de pessoa não gera risco."""
        detections = [
            {"classe": "person", "confianca": 0.9, "frame": 1}
        ]

        result = calculate_video_risk(detections)

        assert result["risco_violencia"] == "baixo"
        assert result["risco_saude_mental"] == "baixo"
        assert len(result["alertas"]) == 0

    def test_sangramento_alto_confidence(self):
        """Sangramento com alta confiança gera risco alto."""
        detections = [
            {"classe": "sangramento", "confianca": 0.85, "frame": 5}
        ]

        result = calculate_video_risk(detections)

        assert result["risco_saude_mental"] == "alto"
        assert len(result["alertas"]) == 1
        assert result["alertas"][0]["tipo"] == "sangramento_detectado"
        assert result["alertas"][0]["severidade"] == "alta"

    def test_sangramento_media_confidence(self):
        """Sangramento com média confiança gera risco médio."""
        detections = [
            {"classe": "sangramento", "confianca": 0.6, "frame": 3}
        ]

        result = calculate_video_risk(detections)

        assert result["risco_saude_mental"] == "medio"
        assert len(result["alertas"]) == 1
        assert result["alertas"][0]["severidade"] == "media"

    def test_sangramento_baixa_confidence_no_risk(self):
        """Sangramento com baixa confiança não gera risco."""
        detections = [
            {"classe": "sangramento", "confianca": 0.3, "frame": 2}
        ]

        result = calculate_video_risk(detections)

        assert result["risco_saude_mental"] == "baixo"
        assert len(result["alertas"]) == 0

    def test_scissors_high_confidence(self):
        """Tesoura com alta confiança gera alerta."""
        detections = [
            {"classe": "scissors", "confianca": 0.75, "frame": 10}
        ]

        result = calculate_video_risk(detections)

        assert result["risco_violencia"] == "medio"
        assert len(result["alertas"]) == 1
        assert result["alertas"][0]["tipo"] == "objeto_perigoso"

    def test_knife_high_confidence(self):
        """Faca com alta confiança gera alerta."""
        detections = [
            {"classe": "knife", "confianca": 0.8, "frame": 15}
        ]

        result = calculate_video_risk(detections)

        assert result["risco_violencia"] == "medio"
        assert len(result["alertas"]) == 1
        assert "fac" in result["alertas"][0]["descricao"].lower() or "knife" in result["alertas"][0]["descricao"].lower()

    def test_knife_blade_detection(self):
        """Lâmina de faca também é detectada."""
        detections = [
            {"classe": "knife_blade", "confianca": 0.9, "frame": 20}
        ]

        result = calculate_video_risk(detections)

        assert result["risco_violencia"] == "medio"

    def test_dangerous_object_low_confidence_no_alert(self):
        """Objeto perigoso com baixa confiança não gera alerta."""
        detections = [
            {"classe": "knife", "confianca": 0.5, "frame": 1}
        ]

        result = calculate_video_risk(detections)

        assert result["risco_violencia"] == "baixo"
        assert len(result["alertas"]) == 0

    def test_multiple_dangerous_objects_elevates_risk(self):
        """Múltiplos objetos perigosos elevam risco para alto."""
        detections = [
            {"classe": "knife", "confianca": 0.8, "frame": 1},
            {"classe": "scissors", "confianca": 0.75, "frame": 2},
            {"classe": "knife", "confianca": 0.85, "frame": 3},
        ]

        result = calculate_video_risk(detections)

        assert result["risco_violencia"] == "alto"
        assert len([a for a in result["alertas"] if a["tipo"] == "multiplos_objetos_perigosos"]) == 1

    def test_sangramento_and_dangerous_objects(self):
        """Combinação de sangramento e objetos perigosos."""
        detections = [
            {"classe": "sangramento", "confianca": 0.9, "frame": 5},
            {"classe": "knife", "confianca": 0.8, "frame": 10},
        ]

        result = calculate_video_risk(detections)

        assert result["risco_violencia"] == "medio"
        assert result["risco_saude_mental"] == "alto"
        assert len(result["alertas"]) == 2

    def test_posture_analysis_integration(self):
        """Integração com análise de postura."""
        detections = [
            {"classe": "person", "confianca": 0.9, "frame": 1}
        ]
        posture = {
            "risco_violencia": "alto",
            "risco_saude_mental": "medio",
            "alertas": [
                {"tipo": "postura_defensiva", "severidade": "alta", "descricao": "Postura defensiva detectada"}
            ],
            "indicadores": ["postura_defensiva", "agitacao"]
        }

        result = calculate_video_risk(detections, posture)

        assert result["risco_violencia"] == "alto"
        assert result["risco_saude_mental"] == "medio"
        # Alertas de postura devem estar presentes
        assert len([a for a in result["alertas"] if a.get("origem") == "postura"]) == 1
        # Detecções virtuais de postura devem estar presentes
        assert len([d for d in result["deteccoes"] if d.get("origem") == "analise_postura"]) == 2

    def test_posture_elevates_existing_risk(self):
        """Postura pode elevar risco existente."""
        detections = [
            {"classe": "scissors", "confianca": 0.75, "frame": 1}
        ]
        posture = {
            "risco_violencia": "alto",
            "risco_saude_mental": "alto",
            "alertas": [],
            "indicadores": []
        }

        result = calculate_video_risk(detections, posture)

        assert result["risco_violencia"] == "alto"
        assert result["risco_saude_mental"] == "alto"

    def test_class_case_insensitive(self):
        """Classe deve ser case insensitive."""
        detections = [
            {"classe": "SANGramento", "confianca": 0.9, "frame": 1},
            {"classe": "SCISSORS", "confianca": 0.8, "frame": 2},
        ]

        result = calculate_video_risk(detections)

        assert result["risco_saude_mental"] == "alto"
        assert result["risco_violencia"] == "medio"

    def test_frame_reference_in_alerts(self):
        """Alertas devem conter referência ao frame."""
        detections = [
            {"classe": "sangramento", "confianca": 0.9, "frame": 42}
        ]

        result = calculate_video_risk(detections)

        assert result["alertas"][0]["frame_referencia"] == 42

    def test_detection_copy_with_posture(self):
        """Detecções originais devem ser preservadas com postura."""
        detections = [
            {"classe": "person", "confianca": 0.9, "frame": 1}
        ]
        posture = {
            "risco_violencia": "medio",
            "risco_saude_mental": "baixo",
            "alertas": [],
            "indicadores": ["rigidez"]
        }

        result = calculate_video_risk(detections, posture)

        # Deve conter detecção original + indicador de postura
        assert len(result["deteccoes"]) == 2
        assert result["deteccoes"][0]["classe"] == "person"
        assert result["deteccoes"][1]["classe"] == "postura_rigidez"
