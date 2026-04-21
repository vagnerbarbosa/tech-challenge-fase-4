"""Testes unitários para VideoAnalysisService.

Estes testes validam a orquestração do processamento de vídeo,
coordenando VideoProcessor, YOLOv8Service e BleedingDetector.
"""

import sys
from pathlib import Path
from unittest.mock import MagicMock, patch

import numpy as np
import pytest

# Adicionar src ao path
sys.path.insert(0, str(Path(__file__).parent.parent.parent.parent / "src"))

from src.services.video_analysis import VideoAnalysisService


class TestVideoAnalysisService:
    """Testes para o serviço de análise de vídeo."""

    @pytest.fixture
    def service(self):
        """Cria uma instância do VideoAnalysisService."""
        return VideoAnalysisService()

    @pytest.fixture
    def mock_frame_info(self, tmp_path):
        """Cria frames mock para testes."""
        frames_dir = tmp_path / "frames"
        frames_dir.mkdir()

        from src.services.video_processor import FrameInfo

        frames = []
        for i in range(5):
            frame_path = frames_dir / f"frame_{i:06d}_{i:.3f}s.jpg"
            # Criar arquivo vazio para simular frame
            frame_path.write_text("")
            frames.append(
                FrameInfo(
                    frame_number=i,
                    timestamp=float(i),
                    path=frame_path,
                )
            )
        return frames

    def test_service_initialization(self, service):
        """Testa se o serviço inicializa corretamente com lazy loading."""
        assert service._yolo_service is None
        assert service._bleeding_detector is None
        assert service._video_processor is None
        assert service._logger is None

    def test_get_logger_lazy_initialization(self, service):
        """Testa lazy initialization do logger."""
        logger = service._get_logger()
        assert logger is not None
        assert service._logger is not None

        # Segunda chamada deve retornar o mesmo logger
        logger2 = service._get_logger()
        assert logger2 is logger

    def test_get_yolo_service_lazy_initialization(self, service):
        """Testa lazy initialization do YOLOv8Service."""
        with patch("src.services.yolo_service.YOLO") as mock_yolo_class:
            mock_yolo_instance = MagicMock()
            mock_yolo_class.return_value = mock_yolo_instance

            yolo_service = service._get_yolo_service()
            assert yolo_service is not None
            assert service._yolo_service is not None
            mock_yolo_class.assert_called_once()

            # Segunda chamada deve retornar a mesma instância
            yolo_service2 = service._get_yolo_service()
            assert yolo_service2 is yolo_service
            mock_yolo_class.assert_called_once()  # Não deve chamar novamente

    def test_get_bleeding_detector_lazy_initialization(self, service):
        """Testa lazy initialization do BleedingDetector."""
        with patch(
            "src.services.bleeding_detector.BleedingDetector"
        ) as mock_bleeding_class:
            mock_bleeding_instance = MagicMock()
            mock_bleeding_class.return_value = mock_bleeding_instance

            bleeding_detector = service._get_bleeding_detector()
            assert bleeding_detector is not None
            assert service._bleeding_detector is not None
            mock_bleeding_class.assert_called_once()

            # Segunda chamada deve retornar a mesma instância
            bleeding_detector2 = service._get_bleeding_detector()
            assert bleeding_detector2 is bleeding_detector
            mock_bleeding_class.assert_called_once()  # Não deve chamar novamente

    def test_get_video_processor_lazy_initialization(self, service):
        """Testa lazy initialization do VideoProcessor."""
        with patch(
            "src.services.video_processor.VideoProcessor"
        ) as mock_processor_class:
            mock_processor_instance = MagicMock()
            mock_processor_class.return_value = mock_processor_instance

            video_processor = service._get_video_processor()
            assert video_processor is not None
            assert service._video_processor is not None
            mock_processor_class.assert_called_once()

            # Segunda chamada deve retornar a mesma instância
            video_processor2 = service._get_video_processor()
            assert video_processor2 is video_processor
            mock_processor_class.assert_called_once()  # Não deve chamar novamente

    @patch("cv2.imread")
    @patch("src.services.video_analysis.calculate_video_risk")
    def test_analyze_successful_flow(
        self, mock_calculate_risk, mock_imread, service, tmp_path, mock_frame_info
    ):
        """Testa fluxo completo de análise de vídeo."""
        # Configurar mocks
        video_path = tmp_path / "test_video.mp4"
        video_path.write_text("fake video")
        temp_dir = tmp_path / "temp"
        temp_dir.mkdir()

        # Mock do VideoProcessor
        mock_video_processor = MagicMock()
        mock_video_processor.extract_frames.return_value = mock_frame_info
        service._video_processor = mock_video_processor

        # Mock do YOLOv8Service
        mock_yolo_service = MagicMock()
        mock_yolo_service.detect.return_value = [
            {
                "classe": "knife",
                "confianca": 0.85,
                "bbox": {"x": 0.1, "y": 0.2, "w": 0.3, "h": 0.4},
            }
        ]
        service._yolo_service = mock_yolo_service

        # Mock do BleedingDetector
        mock_bleeding_detector = MagicMock()
        mock_bleeding_detector.detect.return_value = {
            "detectado": False,
            "confianca": 0.0,
            "percentual_vermelho": 0.5,
            "bbox": None,
        }
        service._bleeding_detector = mock_bleeding_detector

        # Mock do cv2.imread - simula leitura bem-sucedida
        mock_frame = np.zeros((480, 640, 3), dtype=np.uint8)
        mock_imread.return_value = mock_frame

        # Mock do calculate_video_risk
        mock_calculate_risk.return_value = {
            "risco_violencia": "medio",
            "risco_saude_mental": "baixo",
            "alertas": [
                {
                    "tipo": "objeto_perigoso",
                    "severidade": "media",
                    "descricao": "Objeto potencialmente perigoso detectado: knife",
                }
            ],
        }

        # Executar análise
        result = service.analyze(video_path, duration_seconds=10.0, temp_dir=temp_dir)

        # Verificar resultado
        assert "detecoes" in result
        assert "risco_violencia" in result
        assert "risco_saude_mental" in result
        assert "alertas" in result
        assert "frames_processados" in result
        assert "tempo_processamento_ms" in result

        # Verificar valores
        assert result["risco_violencia"] == "medio"
        assert result["risco_saude_mental"] == "baixo"
        assert result["frames_processados"] == 5
        assert len(result["alertas"]) == 1

        # Verificar que os serviços foram chamados corretamente
        mock_video_processor.extract_frames.assert_called_once_with(
            video_path, temp_dir / "frames", 10.0
        )
        assert mock_yolo_service.detect.call_count == 5  # Um para cada frame
        assert mock_bleeding_detector.detect.call_count == 5  # Apenas primeiros 5 frames
        mock_calculate_risk.assert_called_once()

    @patch("cv2.imread")
    def test_analyze_with_frame_read_failure(
        self, mock_imread, service, tmp_path, mock_frame_info
    ):
        """Testa análise quando alguns frames falham na leitura."""
        video_path = tmp_path / "test_video.mp4"
        video_path.write_text("fake video")
        temp_dir = tmp_path / "temp"
        temp_dir.mkdir()

        # Mock do VideoProcessor
        mock_video_processor = MagicMock()
        mock_video_processor.extract_frames.return_value = mock_frame_info
        service._video_processor = mock_video_processor

        # Mock do YOLOv8Service
        mock_yolo_service = MagicMock()
        mock_yolo_service.detect.return_value = []
        service._yolo_service = mock_yolo_service

        # Mock do BleedingDetector
        mock_bleeding_detector = MagicMock()
        mock_bleeding_detector.detect.return_value = {
            "detectado": False,
            "confianca": 0.0,
            "bbox": None,
        }
        service._bleeding_detector = mock_bleeding_detector

        # Mock do cv2.imread - alterna entre sucesso e falha
        # Precisa de 10 valores: 5 para YOLO + 5 para bleeding
        mock_imread.side_effect = [
            np.zeros((480, 640, 3), dtype=np.uint8),  # Sucesso (YOLO)
            None,  # Falha (YOLO)
            np.zeros((480, 640, 3), dtype=np.uint8),  # Sucesso (YOLO)
            None,  # Falha (YOLO)
            np.zeros((480, 640, 3), dtype=np.uint8),  # Sucesso (YOLO)
            np.zeros((480, 640, 3), dtype=np.uint8),  # Sucesso (bleeding)
            None,  # Falha (bleeding)
            np.zeros((480, 640, 3), dtype=np.uint8),  # Sucesso (bleeding)
            None,  # Falha (bleeding)
            np.zeros((480, 640, 3), dtype=np.uint8),  # Sucesso (bleeding)
        ]

        with patch("src.services.video_analysis.calculate_video_risk") as mock_calc:
            mock_calc.return_value = {
                "risco_violencia": "baixo",
                "risco_saude_mental": "baixo",
                "alertas": [],
            }

            _result = service.analyze(video_path, duration_seconds=10.0, temp_dir=temp_dir)

            # Verificar que apenas os frames lidos com sucesso foram processados
            assert mock_yolo_service.detect.call_count == 3  # Apenas frames que foram lidos
            assert _result is not None  # Usar resultado para evitar F841

    @patch("cv2.imread")
    def test_analyze_with_bleeding_detection(
        self, mock_imread, service, tmp_path, mock_frame_info
    ):
        """Testa análise com detecção de sangramento."""
        video_path = tmp_path / "test_video.mp4"
        video_path.write_text("fake video")
        temp_dir = tmp_path / "temp"
        temp_dir.mkdir()

        # Mock do VideoProcessor
        mock_video_processor = MagicMock()
        mock_video_processor.extract_frames.return_value = mock_frame_info
        service._video_processor = mock_video_processor

        # Mock do YOLOv8Service - sem detecções
        mock_yolo_service = MagicMock()
        mock_yolo_service.detect.return_value = []
        service._yolo_service = mock_yolo_service

        # Mock do BleedingDetector - detecta sangramento
        mock_bleeding_detector = MagicMock()
        mock_bleeding_detector.detect.return_value = {
            "detectado": True,
            "confianca": 0.9,
            "percentual_vermelho": 4.5,
            "bbox": {"x": 0.2, "y": 0.3, "w": 0.1, "h": 0.15},
        }
        service._bleeding_detector = mock_bleeding_detector

        # Mock do cv2.imread
        mock_imread.return_value = np.zeros((480, 640, 3), dtype=np.uint8)

        with patch("src.services.video_analysis.calculate_video_risk") as mock_calc:
            mock_calc.return_value = {
                "risco_violencia": "baixo",
                "risco_saude_mental": "alto",
                "alertas": [
                    {
                        "tipo": "sangramento_detectado",
                        "severidade": "alta",
                        "descricao": "Possível sangramento excessivo detectado",
                    }
                ],
            }

            result = service.analyze(video_path, duration_seconds=10.0, temp_dir=temp_dir)

            # Verificar que sangramento foi adicionado às detecções
            detecoes = result["detecoes"]
            bleeding_detections = [d for d in detecoes if d.get("classe") == "sangramento"]
            assert len(bleeding_detections) == 5  # Um para cada frame

            # Verificar estrutura da detecção de sangramento
            bleeding_det = bleeding_detections[0]
            assert bleeding_det["classe"] == "sangramento"
            assert bleeding_det["confianca"] == 0.9
            assert "bbox" in bleeding_det
            assert "frame" in bleeding_det
            assert "timestamp" in bleeding_det

    @patch("cv2.imread")
    def test_analyze_frame_metadata_in_detections(
        self, mock_imread, service, tmp_path, mock_frame_info
    ):
        """Testa que metadados do frame são adicionados às detecções."""
        video_path = tmp_path / "test_video.mp4"
        video_path.write_text("fake video")
        temp_dir = tmp_path / "temp"
        temp_dir.mkdir()

        # Mock do VideoProcessor
        mock_video_processor = MagicMock()
        mock_video_processor.extract_frames.return_value = mock_frame_info
        service._video_processor = mock_video_processor

        # Mock do YOLOv8Service
        mock_yolo_service = MagicMock()
        mock_yolo_service.detect.return_value = [
            {"classe": "person", "confianca": 0.95, "bbox": {"x": 0.0, "y": 0.0, "w": 1.0, "h": 1.0}}
        ]
        service._yolo_service = mock_yolo_service

        # Mock do BleedingDetector
        mock_bleeding_detector = MagicMock()
        mock_bleeding_detector.detect.return_value = {
            "detectado": False,
            "confianca": 0.0,
            "bbox": None,
        }
        service._bleeding_detector = mock_bleeding_detector

        # Mock do cv2.imread
        mock_imread.return_value = np.zeros((480, 640, 3), dtype=np.uint8)

        with patch("src.services.video_analysis.calculate_video_risk") as mock_calc:
            mock_calc.return_value = {
                "risco_violencia": "baixo",
                "risco_saude_mental": "baixo",
                "alertas": [],
            }

            service.analyze(video_path, duration_seconds=10.0, temp_dir=temp_dir)

            # Verificar que cada detecção tem frame e timestamp
            # Pegar as chamadas feitas ao YOLO
            calls = mock_yolo_service.detect.call_args_list
            assert len(calls) == 5  # 5 frames

            # Verificar no resultado final
            calc_call_args = mock_calc.call_args[0][0]
            for det in calc_call_args:
                assert "frame" in det
                assert "timestamp" in det

    @patch("cv2.imread")
    def test_analyze_multiple_yolo_detections(
        self, mock_imread, service, tmp_path
    ):
        """Testa análise com múltiplas detecções por frame."""
        video_path = tmp_path / "test_video.mp4"
        video_path.write_text("fake video")
        temp_dir = tmp_path / "temp"
        temp_dir.mkdir()

        # Criar frames mock
        from src.services.video_processor import FrameInfo

        frames_dir = temp_dir / "frames"
        frames_dir.mkdir()
        frames = [
            FrameInfo(frame_number=0, timestamp=0.0, path=frames_dir / "frame_000000_0.000s.jpg"),
            FrameInfo(frame_number=1, timestamp=1.0, path=frames_dir / "frame_000001_1.000s.jpg"),
        ]
        for f in frames:
            f.path.write_text("")

        # Mock do VideoProcessor
        mock_video_processor = MagicMock()
        mock_video_processor.extract_frames.return_value = frames
        service._video_processor = mock_video_processor

        # Mock do YOLOv8Service - múltiplas detecções por frame
        mock_yolo_service = MagicMock()
        mock_yolo_service.detect.return_value = [
            {"classe": "person", "confianca": 0.9, "bbox": {"x": 0.1, "y": 0.1, "w": 0.3, "h": 0.4}},
            {"classe": "knife", "confianca": 0.8, "bbox": {"x": 0.5, "y": 0.5, "w": 0.1, "h": 0.2}},
        ]
        service._yolo_service = mock_yolo_service

        # Mock do BleedingDetector
        mock_bleeding_detector = MagicMock()
        mock_bleeding_detector.detect.return_value = {"detectado": False, "confianca": 0.0, "bbox": None}
        service._bleeding_detector = mock_bleeding_detector

        # Mock do cv2.imread
        mock_imread.return_value = np.zeros((480, 640, 3), dtype=np.uint8)

        with patch("src.services.video_analysis.calculate_video_risk") as mock_calc:
            mock_calc.return_value = {
                "risco_violencia": "alto",
                "risco_saude_mental": "baixo",
                "alertas": [],
            }

            _result = service.analyze(video_path, duration_seconds=5.0, temp_dir=temp_dir)

            # 2 frames * 2 detecções = 4 detecções totais
            assert _result is not None  # Usar resultado para evitar F841
            detecoes_enviadas = mock_calc.call_args[0][0]
            assert len(detecoes_enviadas) == 4

            # Verificar que cada detecção tem metadados diferentes
            person_dets = [d for d in detecoes_enviadas if d["classe"] == "person"]
            knife_dets = [d for d in detecoes_enviadas if d["classe"] == "knife"]
            assert len(person_dets) == 2
            assert len(knife_dets) == 2

    def test_analyze_creates_frames_directory(self, service, tmp_path):
        """Testa que o diretório de frames é passado corretamente."""
        video_path = tmp_path / "test_video.mp4"
        video_path.write_text("fake video")
        temp_dir = tmp_path / "temp"
        temp_dir.mkdir()

        # Mock do VideoProcessor
        mock_video_processor = MagicMock()
        mock_video_processor.extract_frames.return_value = []
        service._video_processor = mock_video_processor

        with patch("src.services.video_analysis.calculate_video_risk") as mock_calc:
            mock_calc.return_value = {
                "risco_violencia": "baixo",
                "risco_saude_mental": "baixo",
                "alertas": [],
            }

            service.analyze(video_path, duration_seconds=5.0, temp_dir=temp_dir)

            # Verificar que extract_frames foi chamado com o diretório correto
            call_args = mock_video_processor.extract_frames.call_args
            assert call_args[0][1] == temp_dir / "frames"

    def test_analyze_processing_time(self, service, tmp_path):
        """Testa que o tempo de processamento é calculado e retornado."""

        video_path = tmp_path / "test_video.mp4"
        video_path.write_text("fake video")
        temp_dir = tmp_path / "temp"
        temp_dir.mkdir()

        # Mock do VideoProcessor
        mock_video_processor = MagicMock()
        mock_video_processor.extract_frames.return_value = []
        service._video_processor = mock_video_processor

        with (
            patch("src.services.video_analysis.calculate_video_risk") as mock_calc,
            patch("src.services.video_analysis.time.time") as mock_time,
        ):
                # Mock time.time() - retorna valores fixos para teste
                mock_time.return_value = 0.5
                mock_calc.return_value = {
                    "risco_violencia": "baixo",
                    "risco_saude_mental": "baixo",
                    "alertas": [],
                }

                result = service.analyze(video_path, duration_seconds=5.0, temp_dir=temp_dir)

                # Tempo deve estar em ms e ser >= 0 (tempo foi calculado)
                assert result["tempo_processamento_ms"] >= 0


class TestVideoAnalysisServiceIntegration:
    """Testes de integração leve para VideoAnalysisService."""

    def test_analyze_with_real_dependencies_mocked_cv2(self, tmp_path):
        """Testa análise com dependências reais mas OpenCV mockado."""
        service = VideoAnalysisService()

        video_path = tmp_path / "test_video.mp4"
        video_path.write_text("fake video")
        temp_dir = tmp_path / "temp"
        temp_dir.mkdir()

        # Criar frames mock
        from src.services.video_processor import FrameInfo

        frames_dir = temp_dir / "frames"
        frames_dir.mkdir()
        frames = [
            FrameInfo(
                frame_number=0,
                timestamp=0.0,
                path=frames_dir / "frame_000000_0.000s.jpg",
            )
        ]
        frames[0].path.write_text("")

        # Mock do VideoProcessor
        mock_video_processor = MagicMock()
        mock_video_processor.extract_frames.return_value = frames
        service._video_processor = mock_video_processor

        # Usar YOLO service real (pode skipar se modelo não disponível)
        try:
            from src.services.yolo_service import YOLOv8Service

            yolo_service = YOLOv8Service()
            service._yolo_service = yolo_service
        except RuntimeError:
            pytest.skip("YOLOv8 não disponível")

        # Mock do BleedingDetector real
        from src.services.bleeding_detector import BleedingDetector

        service._bleeding_detector = BleedingDetector()

        # Mock do cv2.imread
        with patch("cv2.imread") as mock_imread:
            # Criar imagem de teste
            test_image = np.zeros((480, 640, 3), dtype=np.uint8)
            mock_imread.return_value = test_image

            with patch("src.services.video_analysis.calculate_video_risk") as mock_calc:
                mock_calc.return_value = {
                    "risco_violencia": "baixo",
                    "risco_saude_mental": "baixo",
                    "alertas": [],
                }

                result = service.analyze(
                    video_path, duration_seconds=5.0, temp_dir=temp_dir
                )

                assert result["frames_processados"] == 1
                assert "detecoes" in result
                assert "tempo_processamento_ms" in result
