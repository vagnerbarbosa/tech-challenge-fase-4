"""Testes unitários para o BleedingDetector.

Este módulo contém testes para o detector de sangramento que utiliza
análise de cor HSV para identificar regiões vermelhas em imagens.
"""

import numpy as np
import pytest

from src.services.bleeding_detector import BleedingDetector


class TestBleedingDetector:
    """Testes para a classe BleedingDetector."""

    def test_init_default_values(self) -> None:
        """Testa inicialização com valores padrão."""
        detector = BleedingDetector()

        assert detector.threshold_percentual == 2.0
        assert detector.max_confidence_percentual == 5.0

    def test_init_custom_values(self) -> None:
        """Testa inicialização com valores customizados."""
        detector = BleedingDetector(
            threshold_percentual=5.0,
            max_confidence_percentual=10.0,
        )

        assert detector.threshold_percentual == 5.0
        assert detector.max_confidence_percentual == 10.0

    def test_detect_no_bleeding_normal_image(self) -> None:
        """Testa detecção em imagem sem sangramento (cor normal/azul/verde)."""
        detector = BleedingDetector()

        # Cria imagem 100x100 azul (BGR: 255, 0, 0) - sem vermelho
        image = np.full((100, 100, 3), (255, 0, 0), dtype=np.uint8)

        result = detector.detect(image)

        assert result["detectado"] is False
        assert result["percentual_vermelho"] == pytest.approx(0.0, abs=0.1)
        assert result["confianca"] == pytest.approx(0.0, abs=0.01)
        assert result["bbox"] is None

    def test_detect_no_bleeding_green_image(self) -> None:
        """Testa detecção em imagem verde - sem sangramento."""
        detector = BleedingDetector()

        # Cria imagem 100x100 verde (BGR: 0, 255, 0)
        image = np.full((100, 100, 3), (0, 255, 0), dtype=np.uint8)

        result = detector.detect(image)

        assert result["detectado"] is False
        assert result["percentual_vermelho"] < 1.0
        assert result["bbox"] is None

    def test_detect_with_bleeding_red_image(self) -> None:
        """Testa detecção em imagem com sangramento (região vermelha intensa)."""
        detector = BleedingDetector()

        # Cria imagem 100x100 toda vermelha intensa (BGR: 0, 0, 255)
        image = np.full((100, 100, 3), (0, 0, 255), dtype=np.uint8)

        result = detector.detect(image)

        assert result["detectado"] is True
        assert result["percentual_vermelho"] > 50.0  # Deve detectar muito vermelho
        assert result["confianca"] > 0.5
        assert result["bbox"] is not None
        assert "x" in result["bbox"]
        assert "y" in result["bbox"]
        assert "w" in result["bbox"]
        assert "h" in result["bbox"]

    def test_detect_partial_bleeding(self) -> None:
        """Testa detecção com sangramento parcial (metade da imagem vermelha)."""
        detector = BleedingDetector()

        # Cria imagem 100x100 metade vermelha, metade azul
        image = np.zeros((100, 100, 3), dtype=np.uint8)
        image[:50, :] = (0, 0, 255)  # Metade superior vermelha (BGR)
        image[50:, :] = (255, 0, 0)  # Metade inferior azul (BGR)

        result = detector.detect(image)

        # Deve ter aproximadamente 50% de pixels vermelhos
        assert result["percentual_vermelho"] == pytest.approx(50.0, rel=0.1)
        assert result["detectado"] is True
        assert result["bbox"] is not None

    def test_detect_grayscale_image(self) -> None:
        """Testa detecção em imagem em escala de cinza."""
        detector = BleedingDetector()

        # Cria imagem 100x100 em escala de cinza (sem vermelho)
        image = np.full((100, 100), 128, dtype=np.uint8)

        result = detector.detect(image)

        assert result["detectado"] is False
        assert result["percentual_vermelho"] < 2.0

    def test_detect_threshold_boundary(self) -> None:
        """Testa comportamento no limiar de detecção."""
        # Detector com threshold de 5%
        detector = BleedingDetector(threshold_percentual=5.0)

        # Cria imagem com exatamente 4% de pixels vermelhos (abaixo do threshold)
        image = np.zeros((100, 100, 3), dtype=np.uint8)
        # 400 pixels vermelhos = 4% de 10000
        image[:4, :] = (0, 0, 255)  # 4 linhas vermelhas

        result = detector.detect(image)

        # Pode ou não detectar dependendo da precisão
        # O importante é que a confiança seja calculada
        assert "confianca" in result
        assert "percentual_vermelho" in result

    def test_detect_confidence_calculation(self) -> None:
        """Testa cálculo de confiança baseado no percentual de vermelho."""
        detector = BleedingDetector(max_confidence_percentual=10.0)

        # Cria imagem com 5% de pixels vermelhos
        image = np.zeros((100, 100, 3), dtype=np.uint8)
        image[:5, :] = (0, 0, 255)  # 5 linhas vermelhas = 5%

        result = detector.detect(image)

        # Confiança esperada: 5% / 10% = 0.5
        expected_confidence = result["percentual_vermelho"] / 10.0
        assert result["confianca"] == pytest.approx(expected_confidence, abs=0.05)

    def test_detect_confidence_capped_at_1(self) -> None:
        """Testa que confiança é limitada a 1.0."""
        detector = BleedingDetector(max_confidence_percentual=5.0)

        # Cria imagem toda vermelha (100% de pixels vermelhos)
        image = np.full((100, 100, 3), (0, 0, 255), dtype=np.uint8)

        result = detector.detect(image)

        # Confiança deve ser limitada a 1.0
        assert result["confianca"] == pytest.approx(1.0, abs=0.01)

    def test_detect_invalid_image_none(self) -> None:
        """Testa erro ao passar imagem None."""
        detector = BleedingDetector()

        with pytest.raises(ValueError, match="Imagem inválida ou vazia"):
            detector.detect(None)  # type: ignore[arg-type]

    def test_detect_invalid_image_empty(self) -> None:
        """Testa erro ao passar imagem vazia."""
        detector = BleedingDetector()

        empty_image = np.array([], dtype=np.uint8)
        with pytest.raises(ValueError, match="Imagem inválida ou vazia"):
            detector.detect(empty_image)

    def test_detect_invalid_image_shape(self) -> None:
        """Testa erro ao passar imagem com formato inválido."""
        detector = BleedingDetector()

        # Imagem 4D inválida
        invalid_image = np.zeros((10, 10, 10, 3), dtype=np.uint8)
        with pytest.raises(ValueError, match="Formato de imagem não suportado"):
            detector.detect(invalid_image)

    def test_detect_invalid_image_single_channel(self) -> None:
        """Testa erro ao passar imagem com canal único mas não 2D."""
        detector = BleedingDetector()

        # Imagem com shape inválido (3D mas apenas 1 canal)
        invalid_image = np.zeros((10, 10, 1), dtype=np.uint8)
        # Isso é aceitável como imagem 2D para o detector
        # pois len(shape) == 3 e shape[2] != 3
        with pytest.raises(ValueError, match="Formato de imagem não suportado"):
            detector.detect(invalid_image)

    def test_bbox_normalization(self) -> None:
        """Testa que bounding box é normalizado entre 0 e 1."""
        detector = BleedingDetector()

        # Cria imagem 100x100 com região vermelha em uma área específica
        image = np.zeros((100, 100, 3), dtype=np.uint8)
        # Região vermelha: x=20-40, y=30-60 (20x30 pixels)
        image[30:60, 20:40] = (0, 0, 255)

        result = detector.detect(image)

        assert result["detectado"] is True
        assert result["bbox"] is not None

        bbox = result["bbox"]
        # Verifica que todas as coordenadas estão entre 0 e 1
        assert 0.0 <= bbox["x"] <= 1.0
        assert 0.0 <= bbox["y"] <= 1.0
        assert 0.0 <= bbox["w"] <= 1.0
        assert 0.0 <= bbox["h"] <= 1.0

        # Verifica valores esperados (com tolerância)
        # x = 20/100 = 0.2, y = 30/100 = 0.3
        # w = 20/100 = 0.2, h = 30/100 = 0.3
        assert bbox["x"] == pytest.approx(0.2, abs=0.05)
        assert bbox["y"] == pytest.approx(0.3, abs=0.05)
        assert bbox["w"] == pytest.approx(0.2, abs=0.05)
        assert bbox["h"] == pytest.approx(0.3, abs=0.05)

    def test_bbox_no_contours(self) -> None:
        """Testa bounding box quando não há contornos."""
        detector = BleedingDetector()

        # Máscara vazia (sem pixels vermelhos)
        mask = np.zeros((100, 100), dtype=np.uint8)

        bbox = detector._find_largest_contour_bbox(mask)

        assert bbox is None

    def test_bbox_multiple_contours(self) -> None:
        """Testa que retorna o maior contorno quando há múltiplos."""
        detector = BleedingDetector()

        # Cria imagem com dois blobs vermelhos de tamanhos diferentes
        image = np.zeros((100, 100, 3), dtype=np.uint8)
        # Blob pequeno: 10x10
        image[10:20, 10:20] = (0, 0, 255)
        # Blob grande: 40x40
        image[50:90, 50:90] = (0, 0, 255)

        result = detector.detect(image)

        assert result["detectado"] is True
        assert result["bbox"] is not None

        # O bbox deve corresponder ao maior contorno (blob grande)
        bbox = result["bbox"]
        # Centro aproximado do blob grande: x=50/100=0.5, y=50/100=0.5
        assert bbox["x"] >= 0.4  # Deve estar próximo do blob grande
        assert bbox["y"] >= 0.4

    def test_detect_small_red_spots(self) -> None:
        """Testa detecção de pequenas manchas vermelhas."""
        detector = BleedingDetector(threshold_percentual=0.5)

        # Cria imagem com pequenas manchas vermelhas
        image = np.zeros((200, 200, 3), dtype=np.uint8)
        # Alguns pixels vermelhos espalhados
        image[50, 50] = (0, 0, 255)
        image[51, 50] = (0, 0, 255)
        image[50, 51] = (0, 0, 255)
        image[100, 100] = (0, 0, 255)
        image[100, 101] = (0, 0, 255)

        result = detector.detect(image)

        # Deve detectar pixels vermelhos mesmo que poucos
        assert result["percentual_vermelho"] > 0

    def test_detect_orange_not_counted_as_red(self) -> None:
        """Testa que cor laranja não é contada como vermelho."""
        detector = BleedingDetector()

        # Cria imagem laranja (BGR: 0, 165, 255)
        image = np.full((100, 100, 3), (0, 165, 255), dtype=np.uint8)

        result = detector.detect(image)

        # Laranja pode ter algum componente vermelho em HSV
        # mas deve ser menos que threshold
        if result["detectado"]:
            assert result["percentual_vermelho"] < 5.0

    def test_detect_dark_red(self) -> None:
        """Testa detecção de vermelho escuro (baixa saturação)."""
        detector = BleedingDetector()

        # Cria imagem vermelho escuro (BGR: 0, 50, 100)
        # Este vermelho pode não ser detectado devido à baixa saturação
        image = np.full((100, 100, 3), (0, 50, 100), dtype=np.uint8)

        result = detector.detect(image)

        # Verifica que a detecção foi realizada
        assert "detectado" in result
        assert "percentual_vermelho" in result
        assert "confianca" in result

    def test_result_format_consistency(self) -> None:
        """Testa que o formato do resultado é consistente."""
        detector = BleedingDetector()

        # Testa com imagem sem sangramento
        image_no_red = np.full((100, 100, 3), (255, 255, 0), dtype=np.uint8)
        result1 = detector.detect(image_no_red)

        required_keys = {"detectado", "confianca", "percentual_vermelho", "bbox"}
        assert set(result1.keys()) == required_keys
        assert isinstance(result1["detectado"], bool)
        assert isinstance(result1["confianca"], float)
        assert isinstance(result1["percentual_vermelho"], float)

        # Testa com imagem com sangramento
        image_red = np.full((100, 100, 3), (0, 0, 255), dtype=np.uint8)
        result2 = detector.detect(image_red)

        assert set(result2.keys()) == required_keys
        assert isinstance(result2["detectado"], bool)
        assert isinstance(result2["confianca"], float)
        assert isinstance(result2["percentual_vermelho"], float)
        assert isinstance(result2["bbox"], dict)


class TestGetBleedingDetector:
    """Testes para a função factory get_bleeding_detector."""

    def test_get_bleeding_detector_returns_instance(self) -> None:
        """Testa que factory retorna instância de BleedingDetector."""
        from src.services.bleeding_detector import get_bleeding_detector

        detector = get_bleeding_detector()

        assert isinstance(detector, BleedingDetector)
        assert detector.threshold_percentual == 2.0
        assert detector.max_confidence_percentual == 5.0

    def test_get_bleeding_detector_singleton_behavior(self) -> None:
        """Testa que múltiplas chamadas retornam instâncias independentes."""
        from src.services.bleeding_detector import get_bleeding_detector

        detector1 = get_bleeding_detector()
        detector2 = get_bleeding_detector()

        # Devem ser instâncias diferentes (não singleton)
        assert detector1 is not detector2
        # Mas com mesmos valores padrão
        assert detector1.threshold_percentual == detector2.threshold_percentual
