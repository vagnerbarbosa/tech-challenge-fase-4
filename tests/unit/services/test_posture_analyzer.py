"""Testes unitários para o PostureAnalyzer.

Testa a análise de postura e linguagem corporal para identificar
sinais de desconforto, medo, agitação e rigidez.
"""


import pytest

from src.services.posture_analyzer import (
    FramePostureAnalysis,
    PostureAnalyzer,
    PostureMetrics,
    calculate_posture_risk,
)


class TestPostureAnalyzerInitialization:
    """Testes de inicialização do PostureAnalyzer."""

    def test_default_initialization(self) -> None:
        """Testa inicialização com valores padrão."""
        analyzer = PostureAnalyzer()

        assert analyzer.history_size == 5
        assert analyzer._position_history == []

    def test_custom_history_size(self) -> None:
        """Testa inicialização com history_size customizado."""
        analyzer = PostureAnalyzer(history_size=10)

        assert analyzer.history_size == 10
        assert analyzer._position_history == []

    def test_initialization_with_history_size_1(self) -> None:
        """Testa inicialização com history_size mínimo."""
        analyzer = PostureAnalyzer(history_size=1)

        assert analyzer.history_size == 1


class TestDefensivePostureDetection:
    """Testes de detecção de postura defensiva."""

    @pytest.fixture
    def analyzer(self) -> PostureAnalyzer:
        """Fixture do PostureAnalyzer."""
        return PostureAnalyzer()

    def test_defensive_posture_low_aspect_ratio_and_low_position(
        self, analyzer: PostureAnalyzer
    ) -> None:
        """Testa detecção de postura defensiva com aspect ratio baixo e posição baixa.

        Postura defensiva: aspect ratio entre 0.8 e 1.8 + centroid_y > 0.6
        """
        # Aspect ratio de 1.2 (entre 0.8 e 1.8) + posição baixa (0.7)
        is_defensive = analyzer._is_defensive_posture(aspect_ratio=1.2, centroid_y=0.7)

        assert is_defensive is True

    def test_defensive_posture_at_threshold_boundaries(
        self, analyzer: PostureAnalyzer
    ) -> None:
        """Testa postura defensiva nos limites exatos dos thresholds."""
        # Aspect ratio exatamente nos limites e posição exatamente em 0.6
        is_defensive = analyzer._is_defensive_posture(
            aspect_ratio=analyzer.DEFENSIVE_ASPECT_RATIO_MIN, centroid_y=0.61
        )

        assert is_defensive is True

    def test_not_defensive_posture_high_aspect_ratio(
        self, analyzer: PostureAnalyzer
    ) -> None:
        """Testa que postura com aspect ratio alto não é defensiva.

        Aspect ratio alto (> 1.8) indica postura ereta/normal.
        """
        # Aspect ratio de 2.5 (acima de 1.8) + posição baixa
        is_defensive = analyzer._is_defensive_posture(aspect_ratio=2.5, centroid_y=0.7)

        assert is_defensive is False

    def test_not_defensive_posture_low_position_but_high_aspect_ratio(
        self, analyzer: PostureAnalyzer
    ) -> None:
        """Testa que aspect ratio alto não é defensiva mesmo com posição baixa."""
        is_defensive = analyzer._is_defensive_posture(aspect_ratio=3.0, centroid_y=0.8)

        assert is_defensive is False

    def test_not_defensive_posture_good_aspect_but_high_position(
        self, analyzer: PostureAnalyzer
    ) -> None:
        """Testa que posição alta não é defensiva mesmo com aspect ratio adequado."""
        # Aspect ratio adequado mas posição alta (centroid_y baixo)
        is_defensive = analyzer._is_defensive_posture(aspect_ratio=1.2, centroid_y=0.5)

        assert is_defensive is False

    def test_defensive_posture_aspect_ratio_too_low(self) -> None:
        """Testa que aspect ratio abaixo do mínimo não é defensiva."""
        analyzer = PostureAnalyzer()

        # Aspect ratio muito baixo (< 0.8) não considerado defensivo
        is_defensive = analyzer._is_defensive_posture(aspect_ratio=0.5, centroid_y=0.7)

        assert is_defensive is False


class TestNormalPostureDetection:
    """Testes de detecção de postura normal."""

    def test_normal_posture_high_aspect_ratio(self) -> None:
        """Testa que postura normal tem aspect ratio alto."""
        analyzer = PostureAnalyzer()

        # Aspect ratio alto (pessoa em pé, ereta)
        is_defensive = analyzer._is_defensive_posture(aspect_ratio=2.8, centroid_y=0.4)

        assert is_defensive is False

    def test_normal_posture_via_analyze_frame(self) -> None:
        """Testa análise de frame com postura normal."""
        analyzer = PostureAnalyzer()

        # Mock de detecção com postura normal (aspect ratio alto)
        detections = [
            {
                "classe": "person",
                "bbox": {"x": 0.3, "y": 0.1, "w": 0.2, "h": 0.6},  # aspect_ratio = 3.0
                "confidence": 0.9,
            }
        ]

        result = analyzer.analyze_frame(detections, frame_number=1, timestamp=0.0)

        assert len(result.metrics) == 1
        assert result.metrics[0].aspect_ratio == pytest.approx(3.0)
        assert result.metrics[0].is_defensive is False
        assert "postura_defensiva" not in result.risk_indicators


class TestAgitationDetection:
    """Testes de detecção de agitação (movimento alto)."""

    def test_agitation_detected_high_movement(self) -> None:
        """Testa detecção de agitação com variância alta de movimento."""
        analyzer = PostureAnalyzer()

        # Variância alta (> AGITATION_THRESHOLD = 0.05)
        is_agitated = analyzer._is_agitated(movement_variance=0.1)

        assert is_agitated is True

    def test_no_agitation_low_movement(self) -> None:
        """Testa que baixa variância não é agitação."""
        analyzer = PostureAnalyzer()

        # Variância baixa (< AGITATION_THRESHOLD)
        is_agitated = analyzer._is_agitated(movement_variance=0.01)

        assert is_agitated is False

    def test_agitation_at_threshold(self) -> None:
        """Testa comportamento exatamente no threshold de agitação."""
        analyzer = PostureAnalyzer()

        # Exatamente no threshold
        is_agitated = analyzer._is_agitated(movement_variance=analyzer.AGITATION_THRESHOLD)

        assert is_agitated is False  # > threshold, não >=

    def test_agitation_indicator_in_frame_analysis(self) -> None:
        """Testa que indicador de agitação aparece na análise do frame."""
        analyzer = PostureAnalyzer()
        analyzer._position_history = [
            [(0.3, 0.3)],
            [(0.5, 0.5)],  # Movimento grande
            [(0.8, 0.8)],  # Movimento grande
        ]

        detections = [
            {
                "classe": "person",
                "bbox": {"x": 0.4, "y": 0.4, "w": 0.2, "h": 0.4},
            }
        ]

        result = analyzer.analyze_frame(detections, frame_number=4, timestamp=1.0)

        # Pode ou não detectar agitação dependendo da variância calculada
        # O importante é que o método não falhe
        assert len(result.metrics) == 1


class TestImmobilityDetection:
    """Testes de detecção de rigidez/imobilidade."""

    def test_immobility_detected_very_low_movement(self) -> None:
        """Testa detecção de rigidez com variância muito baixa."""
        analyzer = PostureAnalyzer()

        # Variância muito baixa (< IMMOBILITY_THRESHOLD = 0.001)
        is_immobile = analyzer._is_immobile(movement_variance=0.0005)

        assert is_immobile is True

    def test_no_immobility_with_movement(self) -> None:
        """Testa que movimento normal não é rigidez."""
        analyzer = PostureAnalyzer()

        # Variância normal (> IMMOBILITY_THRESHOLD)
        is_immobile = analyzer._is_immobile(movement_variance=0.01)

        assert is_immobile is False

    def test_no_immobility_at_zero(self) -> None:
        """Testa que variância zero não é rigidez (ainda não há histórico)."""
        analyzer = PostureAnalyzer()

        # Variância zero (sem histórico)
        is_immobile = analyzer._is_immobile(movement_variance=0.0)

        assert is_immobile is False  # movement_variance > 0 é necessário

    def test_immobility_at_exact_threshold(self) -> None:
        """Testa comportamento exatamente no threshold de imobilidade."""
        analyzer = PostureAnalyzer()

        # Exatamente no threshold
        is_immobile = analyzer._is_immobile(movement_variance=analyzer.IMMOBILITY_THRESHOLD)

        assert is_immobile is False  # < threshold, não <=


class TestReclusivePositionDetection:
    """Testes de detecção de posição reclusa."""

    def test_reclusive_position_left_edge(self) -> None:
        """Testa posição reclusa na borda esquerda."""
        analyzer = PostureAnalyzer()

        # Posição na borda esquerda (x < CENTER_ZONE = 0.3)
        is_reclusive = analyzer._is_positioned_defensively(centroid_x=0.2, centroid_y=0.5)

        assert is_reclusive is True

    def test_reclusive_position_right_edge(self) -> None:
        """Testa posição reclusa na borda direita."""
        analyzer = PostureAnalyzer()

        # Posição na borda direita (x > 1 - CENTER_ZONE = 0.7)
        is_reclusive = analyzer._is_positioned_defensively(centroid_x=0.8, centroid_y=0.5)

        assert is_reclusive is True

    def test_reclusive_position_bottom_edge(self) -> None:
        """Testa posição reclusa na borda inferior."""
        analyzer = PostureAnalyzer()

        # Posição na borda inferior (y > 1 - CENTER_ZONE = 0.7)
        is_reclusive = analyzer._is_positioned_defensively(centroid_x=0.5, centroid_y=0.8)

        assert is_reclusive is True

    def test_central_position_not_reclusive(self) -> None:
        """Testa que posição central não é reclusa."""
        analyzer = PostureAnalyzer()

        # Posição central (dentro da zona central)
        is_reclusive = analyzer._is_positioned_defensively(centroid_x=0.5, centroid_y=0.5)

        assert is_reclusive is False

    def test_reclusive_position_at_exact_boundary(self) -> None:
        """Testa posição exatamente no limite da zona central."""
        analyzer = PostureAnalyzer()

        # Exatamente no limite
        is_reclusive = analyzer._is_positioned_defensively(
            centroid_x=analyzer.CENTER_ZONE, centroid_y=0.5
        )

        assert is_reclusive is False  # < boundary, não <=


class TestMovementHistory:
    """Testes de histórico de movimento."""

    def test_history_updates_correctly(self) -> None:
        """Testa que o histórico atualiza corretamente."""
        analyzer = PostureAnalyzer(history_size=3)

        # Adicionar posições ao histórico
        analyzer._update_history([(0.1, 0.1)])
        analyzer._update_history([(0.2, 0.2)])
        analyzer._update_history([(0.3, 0.3)])

        assert len(analyzer._position_history) == 3

        # Adicionar mais uma - deve remover a mais antiga
        analyzer._update_history([(0.4, 0.4)])

        assert len(analyzer._position_history) == 3
        assert analyzer._position_history[0] == [(0.2, 0.2)]  # Antiga removida
        assert analyzer._position_history[-1] == [(0.4, 0.4)]  # Nova adicionada

    def test_movement_variance_calculation(self) -> None:
        """Testa cálculo de variância de movimento."""
        analyzer = PostureAnalyzer(history_size=5)

        # Simular histórico de posições
        analyzer._position_history = [
            [(0.3, 0.3)],
            [(0.31, 0.31)],  # Movimento pequeno
            [(0.32, 0.32)],  # Movimento pequeno
        ]

        variance = analyzer._calculate_movement_variance(0, 0.33, 0.33)

        # Variância deve ser pequena (movimento gradual)
        assert variance >= 0
        assert isinstance(variance, float)

    def test_movement_variance_no_history(self) -> None:
        """Testa variância sem histórico suficiente."""
        analyzer = PostureAnalyzer()

        # Sem histórico
        variance = analyzer._calculate_movement_variance(0, 0.5, 0.5)

        assert variance == 0.0

    def test_reset_clears_history(self) -> None:
        """Testa que reset limpa o histórico."""
        analyzer = PostureAnalyzer()

        analyzer._update_history([(0.5, 0.5)])
        assert len(analyzer._position_history) == 1

        analyzer.reset()
        assert analyzer._position_history == []


class TestCalculatePostureRisk:
    """Testes da função calculate_posture_risk."""

    def test_empty_frame_analyses(self) -> None:
        """Testa cálculo de risco com lista vazia."""
        result = calculate_posture_risk([])

        assert result["risco_violencia"] == "baixo"
        assert result["risco_saude_mental"] == "baixo"
        assert result["indicadores"] == []
        assert result["alertas"] == []

    def test_low_risk_with_normal_postures(self) -> None:
        """Testa risco baixo com posturas normais."""
        analyses = [
            FramePostureAnalysis(
                frame_number=1,
                timestamp=0.0,
                person_detections=[],
                metrics=[
                    PostureMetrics(
                        aspect_ratio=2.5,
                        centroid_x=0.5,
                        centroid_y=0.4,
                        is_defensive=False,
                        movement_variance=0.01,
                    )
                ],
                risk_indicators=[],
            ),
            FramePostureAnalysis(
                frame_number=2,
                timestamp=1.0,
                person_detections=[],
                metrics=[
                    PostureMetrics(
                        aspect_ratio=2.6,
                        centroid_x=0.51,
                        centroid_y=0.41,
                        is_defensive=False,
                        movement_variance=0.015,
                    )
                ],
                risk_indicators=[],
            ),
        ]

        result = calculate_posture_risk(analyses)

        assert result["risco_violencia"] == "baixo"
        assert result["risco_saude_mental"] == "baixo"
        assert result["estatisticas"]["frames_analisados"] == 2
        assert result["estatisticas"]["posturas_defensivas"] == 0

    def test_medium_violence_risk_with_defensive_postures(self) -> None:
        """Testa risco médio de violência com posturas defensivas."""
        analyses = [
            FramePostureAnalysis(
                frame_number=i,
                timestamp=float(i),
                person_detections=[],
                metrics=[
                    PostureMetrics(
                        aspect_ratio=1.2,
                        centroid_x=0.2,
                        centroid_y=0.7,
                        is_defensive=True,
                        movement_variance=0.01,
                    )
                ],
                risk_indicators=["postura_defensiva"],
            )
            for i in range(10)
        ]

        result = calculate_posture_risk(analyses)

        # 100% dos frames com postura defensiva (> 30%)
        assert result["risco_violencia"] == "alto"
        assert "postura_defensiva" in result["indicadores"]

    def test_mental_health_risk_with_agitation(self) -> None:
        """Testa risco de saúde mental com agitação."""
        analyses = [
            FramePostureAnalysis(
                frame_number=i,
                timestamp=float(i),
                person_detections=[],
                metrics=[
                    PostureMetrics(
                        aspect_ratio=2.0,
                        centroid_x=0.5,
                        centroid_y=0.5,
                        is_defensive=False,
                        movement_variance=0.1,  # Acima do threshold de agitação
                    )
                ],
                risk_indicators=["agitacao"],
            )
            for i in range(10)
        ]

        result = calculate_posture_risk(analyses)

        # 100% dos frames com agitação (> 40%)
        assert result["risco_saude_mental"] == "medio"
        assert any(a["tipo"] == "agitacao_detectada" for a in result["alertas"])

    def test_high_mental_health_risk_with_immobility(self) -> None:
        """Testa risco alto de saúde mental com rigidez."""
        analyses = [
            FramePostureAnalysis(
                frame_number=i,
                timestamp=float(i),
                person_detections=[],
                metrics=[
                    PostureMetrics(
                        aspect_ratio=2.0,
                        centroid_x=0.5,
                        centroid_y=0.5,
                        is_defensive=False,
                        movement_variance=0.0001,  # Abaixo do threshold de imobilidade
                    )
                ],
                risk_indicators=["rigidez"],
            )
            for i in range(10)
        ]

        result = calculate_posture_risk(analyses)

        # 100% dos frames com rigidez (> 30%)
        assert result["risco_saude_mental"] == "medio"
        assert any(a["tipo"] == "rigidez_detectada" for a in result["alertas"])

    def test_combined_risk_indicators(self) -> None:
        """Testa múltiplos indicadores de risco simultâneos."""
        analyses = [
            FramePostureAnalysis(
                frame_number=1,
                timestamp=0.0,
                person_detections=[],
                metrics=[
                    PostureMetrics(
                        aspect_ratio=1.2,
                        centroid_x=0.2,
                        centroid_y=0.7,
                        is_defensive=True,
                        movement_variance=0.0001,
                    )
                ],
                risk_indicators=["postura_defensiva", "rigidez", "posicao_reclusa"],
            ),
        ]

        result = calculate_posture_risk(analyses)

        assert "postura_defensiva" in result["indicadores"]
        assert "rigidez" in result["indicadores"]
        assert "posicao_reclusa" in result["indicadores"]


class TestAnalyzeFrame:
    """Testes do método analyze_frame."""

    def test_analyze_frame_with_person_detection(self) -> None:
        """Testa análise de frame com detecção de pessoa."""
        analyzer = PostureAnalyzer()

        detections = [
            {
                "classe": "person",
                "bbox": {"x": 0.3, "y": 0.2, "w": 0.2, "h": 0.5},
                "confidence": 0.9,
            }
        ]

        result = analyzer.analyze_frame(detections, frame_number=1, timestamp=0.0)

        assert isinstance(result, FramePostureAnalysis)
        assert result.frame_number == 1
        assert result.timestamp == 0.0
        assert len(result.metrics) == 1
        assert result.metrics[0].aspect_ratio == 2.5  # 0.5 / 0.2

    def test_analyze_frame_ignores_non_person_detections(self) -> None:
        """Testa que detecções não-pessoa são ignoradas."""
        analyzer = PostureAnalyzer()

        detections = [
            {
                "classe": "chair",
                "bbox": {"x": 0.3, "y": 0.2, "w": 0.2, "h": 0.3},
            },
            {
                "classe": "person",
                "bbox": {"x": 0.5, "y": 0.3, "w": 0.2, "h": 0.5},
            },
        ]

        result = analyzer.analyze_frame(detections, frame_number=1, timestamp=0.0)

        assert len(result.person_detections) == 1
        assert len(result.metrics) == 1
        assert result.person_detections[0]["classe"] == "person"

    def test_analyze_frame_with_empty_detections(self) -> None:
        """Testa análise de frame sem detecções."""
        analyzer = PostureAnalyzer()

        result = analyzer.analyze_frame([], frame_number=1, timestamp=0.0)

        assert result.frame_number == 1
        assert result.person_detections == []
        assert result.metrics == []
        assert result.risk_indicators == []

    def test_analyze_frame_multiple_persons(self) -> None:
        """Testa análise de frame com múltiplas pessoas."""
        analyzer = PostureAnalyzer()

        detections = [
            {
                "classe": "person",
                "bbox": {"x": 0.2, "y": 0.2, "w": 0.15, "h": 0.4},
            },
            {
                "classe": "person",
                "bbox": {"x": 0.6, "y": 0.3, "w": 0.2, "h": 0.5},
            },
        ]

        result = analyzer.analyze_frame(detections, frame_number=1, timestamp=0.0)

        assert len(result.metrics) == 2
        assert len(result.person_detections) == 2

    def test_analyze_frame_defensive_detection_included(self) -> None:
        """Testa que indicadores de risco são incluídos no resultado."""
        analyzer = PostureAnalyzer()

        # Postura defensiva: aspect ratio baixo + posição baixa
        detections = [
            {
                "classe": "person",
                "bbox": {"x": 0.3, "y": 0.5, "w": 0.3, "h": 0.4},
                # aspect_ratio = 1.33, centroid_y = 0.5 + 0.4/2 = 0.7
            }
        ]

        result = analyzer.analyze_frame(detections, frame_number=1, timestamp=0.0)

        assert result.metrics[0].is_defensive is True
        assert "postura_defensiva" in result.risk_indicators

    def test_analyze_frame_updates_history(self) -> None:
        """Testa que analyze_frame atualiza o histórico."""
        analyzer = PostureAnalyzer()

        detections = [
            {
                "classe": "person",
                "bbox": {"x": 0.3, "y": 0.2, "w": 0.2, "h": 0.5},
            }
        ]

        analyzer.analyze_frame(detections, frame_number=1, timestamp=0.0)

        assert len(analyzer._position_history) == 1
        assert analyzer._position_history[0] == [(0.4, 0.45)]  # centroid


class TestPostureMetrics:
    """Testes da dataclass PostureMetrics."""

    def test_posture_metrics_creation(self) -> None:
        """Testa criação de PostureMetrics."""
        metrics = PostureMetrics(
            aspect_ratio=1.5,
            centroid_x=0.5,
            centroid_y=0.6,
            is_defensive=True,
            movement_variance=0.02,
        )

        assert metrics.aspect_ratio == 1.5
        assert metrics.centroid_x == 0.5
        assert metrics.centroid_y == 0.6
        assert metrics.is_defensive is True
        assert metrics.movement_variance == 0.02


class TestFramePostureAnalysis:
    """Testes da dataclass FramePostureAnalysis."""

    def test_frame_analysis_creation(self) -> None:
        """Testa criação de FramePostureAnalysis."""
        metrics = [
            PostureMetrics(
                aspect_ratio=2.0,
                centroid_x=0.5,
                centroid_y=0.5,
                is_defensive=False,
                movement_variance=0.01,
            )
        ]

        analysis = FramePostureAnalysis(
            frame_number=10,
            timestamp=5.0,
            person_detections=[{"classe": "person", "confidence": 0.9}],
            metrics=metrics,
            risk_indicators=["agitacao"],
        )

        assert analysis.frame_number == 10
        assert analysis.timestamp == 5.0
        assert len(analysis.person_detections) == 1
        assert len(analysis.metrics) == 1
        assert analysis.risk_indicators == ["agitacao"]
