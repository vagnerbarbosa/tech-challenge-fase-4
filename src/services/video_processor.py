"""Serviço de processamento de vídeo para extração de frames.

Este módulo fornece funcionalidades para extrair frames de vídeos
usando OpenCV, com suporte a FPS adaptativo baseado na duração do vídeo.
"""

from dataclasses import dataclass
from pathlib import Path

import cv2


@dataclass
class FrameInfo:
    """Informações de um frame extraído do vídeo.

    Attributes:
        frame_number: Número sequencial do frame extraído.
        timestamp: Tempo em segundos no vídeo original onde o frame foi capturado.
        path: Caminho do arquivo temporário onde o frame foi salvo.
    """

    frame_number: int
    timestamp: float
    path: Path


class VideoProcessor:
    """Processador de vídeo para extração de frames.

    Responsável por extrair frames de vídeos usando OpenCV,
    com suporte a FPS adaptativo baseado na duração do vídeo.

    FPS Adaptativo:
        - Vídeos ≤ 30 segundos: 1 FPS (1 frame por segundo)
        - Vídeos > 30 segundos: 0.2 FPS (1 frame a cada 5 segundos)
    """

    def __init__(self) -> None:
        """Inicializa o processador de vídeo."""
        pass

    def _calculate_extraction_fps(self, duration_seconds: float) -> float:
        """Calcula o FPS de extração baseado na duração do vídeo.

        Args:
            duration_seconds: Duração do vídeo em segundos.

        Returns:
            FPS de extração a ser utilizado.
        """
        if duration_seconds <= 30:
            return 1.0  # 1 frame por segundo
        return 0.2  # 1 frame a cada 5 segundos

    def extract_frames(
        self,
        video_path: Path,
        output_dir: Path,
        duration_seconds: float,
    ) -> list[FrameInfo]:
        """Extrai frames de um vídeo usando FPS adaptativo.

        Args:
            video_path: Caminho para o arquivo de vídeo.
            output_dir: Diretório onde os frames extraídos serão salvos.
            duration_seconds: Duração do vídeo em segundos.

        Returns:
            Lista de FrameInfo contendo metadados de cada frame extraído.

        Raises:
            FileNotFoundError: Se o arquivo de vídeo não existir.
            ValueError: Se o vídeo não puder ser aberto ou processado.
            RuntimeError: Se ocorrer erro durante a extração dos frames.
        """
        if not video_path.exists():
            raise FileNotFoundError(f"Arquivo de vídeo não encontrado: {video_path}")

        # Criar diretório de saída se não existir
        output_dir.mkdir(parents=True, exist_ok=True)

        # Abrir o vídeo
        cap = cv2.VideoCapture(str(video_path))
        if not cap.isOpened():
            raise ValueError(f"Não foi possível abrir o vídeo: {video_path}")

        try:
            # Obter propriedades do vídeo
            video_fps = cap.get(cv2.CAP_PROP_FPS)

            if video_fps <= 0:
                raise ValueError(f"FPS inválido do vídeo: {video_fps}")

            # Calcular FPS de extração adaptativo
            extract_fps = self._calculate_extraction_fps(duration_seconds)

            # Calcular intervalo em frames (a cada quantos frames capturar)
            frame_interval = int(video_fps / extract_fps)

            frames_info: list[FrameInfo] = []
            frame_count = 0
            extracted_count = 0

            while True:
                ret, frame = cap.read()
                if not ret:
                    break

                # Extrair frame no intervalo calculado
                if frame_count % frame_interval == 0:
                    # Calcular timestamp em segundos
                    timestamp = frame_count / video_fps

                    # Criar nome do arquivo
                    frame_filename = f"frame_{extracted_count:06d}_{timestamp:.3f}s.jpg"
                    frame_path = output_dir / frame_filename

                    # Salvar frame
                    success = cv2.imwrite(str(frame_path), frame)
                    if not success:
                        raise RuntimeError(f"Falha ao salvar frame: {frame_path}")

                    # Adicionar metadados
                    frames_info.append(
                        FrameInfo(
                            frame_number=extracted_count,
                            timestamp=timestamp,
                            path=frame_path,
                        )
                    )
                    extracted_count += 1

                frame_count += 1

        finally:
            cap.release()

        return frames_info

    def get_video_duration(self, video_path: Path) -> float:
        """Obtém a duração de um vídeo em segundos.

        Args:
            video_path: Caminho para o arquivo de vídeo.

        Returns:
            Duração do vídeo em segundos.

        Raises:
            FileNotFoundError: Se o arquivo de vídeo não existir.
            ValueError: Se o vídeo não puder ser aberto.
        """
        if not video_path.exists():
            raise FileNotFoundError(f"Arquivo de vídeo não encontrado: {video_path}")

        cap = cv2.VideoCapture(str(video_path))
        if not cap.isOpened():
            raise ValueError(f"Não foi possível abrir o vídeo: {video_path}")

        try:
            fps = cap.get(cv2.CAP_PROP_FPS)
            frame_count = cap.get(cv2.CAP_PROP_FRAME_COUNT)

            if fps <= 0:
                raise ValueError(f"FPS inválido do vídeo: {fps}")

            duration = frame_count / fps
            return duration
        finally:
            cap.release()
