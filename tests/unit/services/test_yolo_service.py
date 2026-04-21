"""Testes unitários para YOLOv8Service.

Estes testes validam a detecção de objetos usando YOLOv8,
com foco em classes relevantes para análise de vídeo médico.
"""

import sys
from pathlib import Path

import numpy as np
import pytest

# Adicionar src ao path
sys.path.insert(0, str(Path(__file__).parent.parent.parent.parent / "src"))

from src.services.yolo_service import YOLOv8Service


class TestYOLOv8Service:
    """Testes para o serviço YOLOv8."""

    def test_service_initialization(self):
        """Testa se o serviço inicializa corretamente."""
        # Nota: Este teste pode falhar se o modelo não estiver baixado
        # Em CI, usar mock ou garantir que o modelo está disponível
        try:
            service = YOLOv8Service()
            assert service.model is not None
            assert service.model_name == "yolov8n.pt"
        except RuntimeError as e:
            pytest.skip(f"Modelo YOLO não disponível: {e}")

    def test_get_supported_classes(self):
        """Testa se as classes suportadas estão corretas."""
        try:
            service = YOLOv8Service()
            classes = service.get_supported_classes()

            assert "person" in classes
            assert "knife" in classes
            assert "scissors" in classes
            assert classes["person"] == 0
            assert classes["knife"] == 43
            assert classes["scissors"] == 77
        except RuntimeError:
            pytest.skip("Modelo YOLO não disponível")

    def test_detect_with_empty_image(self):
        """Testa detecção com imagem vazia."""
        try:
            service = YOLOv8Service()

            with pytest.raises(ValueError, match="Imagem inválida"):
                service.detect(np.array([]))
        except RuntimeError:
            pytest.skip("Modelo YOLO não disponível")

    def test_detect_with_valid_image(self):
        """Testa detecção com imagem válida (mock)."""
        # Criar uma imagem de teste simples (preto)
        test_image = np.zeros((640, 480, 3), dtype=np.uint8)

        try:
            service = YOLOv8Service()
            detections = service.detect(test_image, conf_threshold=0.5)

            # Deve retornar uma lista (pode estar vazia se não detectar nada)
            assert isinstance(detections, list)

        except RuntimeError:
            pytest.skip("Modelo YOLO não disponível")

    def test_class_name_mapping(self):
        """Testa o mapeamento de nomes de classes."""
        try:
            service = YOLOv8Service()

            assert service._get_class_name(0) == "person"
            assert service._get_class_name(43) == "knife"
            assert service._get_class_name(77) == "scissors"
            assert service._get_class_name(999) == "unknown"
        except RuntimeError:
            pytest.skip("Modelo YOLO não disponível")

    def test_confidence_filtering(self):
        """Testa se a filtragem por confiança funciona."""
        # Este é um teste de integração que requer uma imagem real
        # com objetos detectáveis
        pytest.skip("Teste de integração - requer imagem com objetos")


class TestYOLOv8ServiceMock:
    """Testes usando mocks para o YOLOv8Service."""

    @pytest.fixture
    def mock_service(self, monkeypatch):
        """Cria um serviço mockado."""
        # Mock da classe YOLO
        class MockYOLO:
            def __init__(self, model_name):
                self.model_name = model_name

            def __call__(self, image, verbose=False, imgsz=320):
                # Retorna resultados mock
                class MockTensor:
                    """Mock de tensor PyTorch."""
                    def __init__(self, data):
                        self._data = np.array(data)

                    def cpu(self):
                        return self

                    def numpy(self):
                        return self._data

                class MockBox:
                    def __init__(self, conf, cls, xyxy):
                        self.conf = np.array([conf])
                        self.cls = np.array([cls])
                        self.xyxy = [MockTensor(xyxy)]

                class MockResult:
                    def __init__(self):
                        self.boxes = [
                            MockBox(0.85, 0, [100, 100, 200, 300]),  # person
                            MockBox(0.75, 77, [300, 200, 350, 250]),  # scissors
                        ]

                return [MockResult()]

        # Aplicar mock
        monkeypatch.setattr("src.services.yolo_service.YOLO", MockYOLO)

        return YOLOv8Service()

    def test_mock_detection(self, mock_service):
        """Testa detecção com mock."""
        test_image = np.zeros((480, 640, 3), dtype=np.uint8)
        detections = mock_service.detect(test_image, conf_threshold=0.5)

        assert len(detections) == 2
        assert detections[0]["classe"] == "person"
        assert detections[0]["confianca"] == 0.85
        assert detections[1]["classe"] == "scissors"

    def test_mock_bbox_format(self, mock_service):
        """Testa formato do bounding box retornado."""
        test_image = np.zeros((480, 640, 3), dtype=np.uint8)
        detections = mock_service.detect(test_image, conf_threshold=0.5)

        for det in detections:
            bbox = det["bbox"]
            assert "x" in bbox
            assert "y" in bbox
            assert "w" in bbox
            assert "h" in bbox
            # Coordenadas devem estar normalizadas (0-1)
            assert 0 <= bbox["x"] <= 1
            assert 0 <= bbox["y"] <= 1
            assert 0 <= bbox["w"] <= 1
            assert 0 <= bbox["h"] <= 1
