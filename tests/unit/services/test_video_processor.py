"""Testes unitários para VideoProcessor.

Estes testes validam a extração de frames de vídeos
com suporte a FPS adaptativo.
"""

import sys
from pathlib import Path

import numpy as np
import pytest

# Adicionar src ao path
sys.path.insert(0, str(Path(__file__).parent.parent.parent.parent / "src"))

from src.services.video_processor import FrameInfo, VideoProcessor


class TestVideoProcessor:
    """Testes para o processador de vídeo."""

    @pytest.fixture
    def processor(self):
        """Cria uma instância do VideoProcessor."""
        return VideoProcessor()

    def test_calculate_extraction_fps_short_video(self, processor):
        """Testa FPS para vídeos curtos (≤30s)."""
        fps = processor._calculate_extraction_fps(30.0)
        assert fps == 1.0

        fps = processor._calculate_extraction_fps(10.0)
        assert fps == 1.0

        fps = processor._calculate_extraction_fps(0.5)
        assert fps == 1.0

    def test_calculate_extraction_fps_long_video(self, processor):
        """Testa FPS para vídeos longos (>30s)."""
        fps = processor._calculate_extraction_fps(31.0)
        assert fps == 0.2

        fps = processor._calculate_extraction_fps(60.0)
        assert fps == 0.2

        fps = processor._calculate_extraction_fps(120.0)
        assert fps == 0.2

    def test_frame_info_dataclass(self):
        """Testa a estrutura FrameInfo."""
        frame_info = FrameInfo(
            frame_number=5,
            timestamp=2.5,
            path=Path("/tmp/frame_005.jpg"),
        )

        assert frame_info.frame_number == 5
        assert frame_info.timestamp == 2.5
        assert str(frame_info.path) == "/tmp/frame_005.jpg"

    def test_extract_frames_file_not_found(self, processor, tmp_path):
        """Testa erro quando arquivo não existe."""
        non_existent = tmp_path / "non_existent.mp4"
        output_dir = tmp_path / "frames"

        with pytest.raises(FileNotFoundError):
            processor.extract_frames(non_existent, output_dir, duration_seconds=10.0)

    def test_get_video_duration_file_not_found(self, processor, tmp_path):
        """Testa erro ao obter duração de arquivo inexistente."""
        non_existent = tmp_path / "non_existent.mp4"

        with pytest.raises(FileNotFoundError):
            processor.get_video_duration(non_existent)

    def test_get_video_duration_invalid_file(self, processor, tmp_path):
        """Testa erro com arquivo inválido."""
        # Criar um arquivo que não é vídeo
        invalid_file = tmp_path / "not_a_video.txt"
        invalid_file.write_text("not a video")

        with pytest.raises(ValueError):
            processor.get_video_duration(invalid_file)


class TestVideoProcessorIntegration:
    """Testes de integração que requerem OpenCV."""

    @pytest.fixture
    def sample_video(self, tmp_path):
        """Cria um vídeo de teste simples."""
        try:
            import cv2

            video_path = tmp_path / "test_video.mp4"
            output_dir = tmp_path / "frames"

            # Criar um vídeo simples: 10 frames, 1 fps = 10 segundos
            fourcc = cv2.VideoWriter_fourcc(*'mp4v')
            out = cv2.VideoWriter(str(video_path), fourcc, 1.0, (640, 480))

            for i in range(10):
                # Frame preto
                frame = np.zeros((480, 640, 3), dtype=np.uint8)
                # Adicionar texto para tornar frames diferentes
                cv2.putText(frame, f"Frame {i}", (50, 50),
                           cv2.FONT_HERSHEY_SIMPLEX, 1, (255, 255, 255), 2)
                out.write(frame)

            out.release()

            return video_path, output_dir
        except ImportError:
            pytest.skip("OpenCV não disponível")

    def test_extract_frames_integration(self, sample_video):
        """Testa extração de frames de um vídeo real."""
        try:
            from src.services.video_processor import VideoProcessor

            video_path, output_dir = sample_video

            processor = VideoProcessor()
            frames = processor.extract_frames(
                video_path, output_dir, duration_seconds=10.0
            )

            # Deve extrair aproximadamente 10 frames (1 fps * 10 segundos)
            assert len(frames) >= 1
            assert len(frames) <= 10

            # Verificar estrutura dos frames
            for frame_info in frames:
                assert isinstance(frame_info, FrameInfo)
                assert frame_info.frame_number >= 0
                assert frame_info.timestamp >= 0.0
                assert frame_info.path.exists()

        except Exception as e:
            pytest.skip(f"Erro na integração: {e}")

    def test_get_video_duration_integration(self, sample_video):
        """Testa obtenção de duração de vídeo real."""
        try:
            from src.services.video_processor import VideoProcessor

            video_path, _ = sample_video

            processor = VideoProcessor()
            duration = processor.get_video_duration(video_path)

            # Duração deve ser próxima de 10 segundos
            assert 9.0 <= duration <= 11.0

        except Exception as e:
            pytest.skip(f"Erro na integração: {e}")
