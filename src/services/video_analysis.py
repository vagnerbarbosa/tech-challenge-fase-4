"""Serviço de análise de vídeo.

Este módulo orquestra o processamento de vídeos,
coordenando VideoProcessor, YOLOv8Service e BleedingDetector.
"""

import time
from pathlib import Path
from typing import TYPE_CHECKING, Any

if TYPE_CHECKING:
    from structlog.stdlib import BoundLogger

from src.services.risk_calculator_video import calculate_video_risk
from src.services.posture_analyzer import PostureAnalyzer, calculate_posture_risk

# Type imports for annotations
from src.services.bleeding_detector import BleedingDetector
from src.services.video_processor import VideoProcessor
from src.services.yolo_service import YOLOv8Service


class VideoAnalysisService:
    """Serviço principal de análise de vídeo.

    Orquestra o processamento completo de vídeos:
    1. Extração de frames
    2. Detecção de objetos com YOLOv8
    3. Detecção de sangramento
    4. Cálculo de riscos
    """

    def __init__(self) -> None:
        """Inicializa o serviço de análise de vídeo."""
        self._yolo_service: YOLOv8Service | None = None
        self._bleeding_detector: BleedingDetector | None = None
        self._video_processor: VideoProcessor | None = None
        self._posture_analyzer: PostureAnalyzer | None = None
        self._logger: BoundLogger | None = None

    def _get_logger(self) -> "BoundLogger":
        """Lazy initialization do logger."""
        if self._logger is None:
            from structlog import get_logger

            self._logger = get_logger()
        return self._logger

    def _get_yolo_service(self) -> "YOLOv8Service":
        """Lazy initialization do YOLOv8Service."""
        if self._yolo_service is None:
            from src.services.yolo_service import YOLOv8Service

            self._yolo_service = YOLOv8Service()
        return self._yolo_service

    def _get_bleeding_detector(self) -> "BleedingDetector":
        """Lazy initialization do BleedingDetector."""
        if self._bleeding_detector is None:
            from src.services.bleeding_detector import BleedingDetector

            self._bleeding_detector = BleedingDetector()
        return self._bleeding_detector

    def _get_video_processor(self) -> "VideoProcessor":
        """Lazy initialization do VideoProcessor."""
        if self._video_processor is None:
            from src.services.video_processor import VideoProcessor

            self._video_processor = VideoProcessor()
        return self._video_processor

    def _get_posture_analyzer(self) -> "PostureAnalyzer":
        """Lazy initialization do PostureAnalyzer."""
        if self._posture_analyzer is None:
            from src.services.posture_analyzer import PostureAnalyzer

            self._posture_analyzer = PostureAnalyzer()
        return self._posture_analyzer

    def analyze(
        self,
        video_path: Path,
        duration_seconds: float,
        temp_dir: Path,
    ) -> dict[str, Any]:
        """Analisa um vídeo completo.

        Args:
            video_path: Caminho para o arquivo de vídeo.
            duration_seconds: Duração do vídeo em segundos.
            temp_dir: Diretório temporário para salvar frames.

        Returns:
            Dicionário com:
                - detecoes: list[dict] (todas as detecções)
                - risco_violencia: str
                - risco_saude_mental: str
                - alertas: list[dict]
                - frames_processados: int
                - tempo_processamento_ms: int
        """
        logger = self._get_logger()
        start_time = time.time()

        logger.info(
            "video_analysis_started",
            video_path=str(video_path),
            duration_seconds=duration_seconds,
        )

        # 1. Extrair frames
        video_processor = self._get_video_processor()
        frames_dir = temp_dir / "frames"
        frames = video_processor.extract_frames(video_path, frames_dir, duration_seconds)

        logger.debug(
            "frames_extracted",
            count=len(frames),
            duration_seconds=duration_seconds,
        )

        # 2. Processar frames com YOLOv8 e PostureAnalyzer
        yolo_service = self._get_yolo_service()
        posture_analyzer = self._get_posture_analyzer()
        all_detections: list[dict[str, Any]] = []
        posture_analyses: list[Any] = []

        for frame_info in frames:
            import cv2

            frame = cv2.imread(str(frame_info.path))
            if frame is None:
                logger.warning(
                    "frame_read_failed",
                    frame_path=str(frame_info.path),
                )
                continue

            # Detectar objetos
            detections = yolo_service.detect(frame, conf_threshold=0.5)

            # Adicionar metadados do frame
            for det in detections:
                det["frame"] = frame_info.frame_number
                det["timestamp"] = frame_info.timestamp
                all_detections.append(det)

            # Analisar postura para frames com pessoas
            posture_analysis = posture_analyzer.analyze_frame(
                detections, frame_info.frame_number, frame_info.timestamp
            )
            if posture_analysis.person_detections:
                posture_analyses.append(posture_analysis)
                # Adicionar indicadores de postura às detecções
                for det in detections:
                    if det.get("classe") == "person":
                        det["posture_indicators"] = posture_analysis.risk_indicators

        logger.debug(
            "yolo_detection_complete",
            detections_count=len(all_detections),
            posture_frames_analyzed=len(posture_analyses),
        )

        # 3. Detectar sangramento (apenas nos primeiros 5 frames)
        bleeding_detector = self._get_bleeding_detector()
        import cv2

        for frame_info in frames[:5]:
            frame = cv2.imread(str(frame_info.path))
            if frame is None:
                continue

            bleeding_result = bleeding_detector.detect(frame)
            if bleeding_result["detectado"]:
                all_detections.append({
                    "classe": "sangramento",
                    "confianca": bleeding_result["confianca"],
                    "bbox": bleeding_result["bbox"],
                    "frame": frame_info.frame_number,
                    "timestamp": frame_info.timestamp,
                })

        logger.debug(
            "bleeding_detection_complete",
            bleeding_detected=any(
                d.get("classe") == "sangramento" for d in all_detections
            ),
        )

        # 4. Calcular riscos (YOLO + sangramento)
        risk_result = calculate_video_risk(all_detections)

        # 5. Calcular riscos de postura
        posture_risk = calculate_posture_risk(posture_analyses)

        # 6. Combinar riscos (elevar se necessário)
        def _combine_risk(risco1: str, risco2: str) -> str:
            """Combina dois níveis de risco, elevando ao maior."""
            levels = {"baixo": 0, "medio": 1, "alto": 2}
            max_level = max(levels.get(risco1, 0), levels.get(risco2, 0))
            for level, val in levels.items():
                if val == max_level:
                    return level
            return risco1

        combined_risco_violencia = _combine_risk(
            risk_result["risco_violencia"], posture_risk["risco_violencia"]
        )
        combined_risco_saude_mental = _combine_risk(
            risk_result["risco_saude_mental"], posture_risk["risco_saude_mental"]
        )

        # Combinar alertas
        combined_alertas = risk_result["alertas"] + posture_risk.get("alertas", [])

        processing_time_ms = int((time.time() - start_time) * 1000)

        logger.info(
            "video_analysis_complete",
            frames_processed=len(frames),
            detections_count=len(all_detections),
            posture_frames_analyzed=len(posture_analyses),
            risco_violencia=combined_risco_violencia,
            risco_saude_mental=combined_risco_saude_mental,
            processing_time_ms=processing_time_ms,
        )

        return {
            "detecoes": all_detections,
            "risco_violencia": combined_risco_violencia,
            "risco_saude_mental": combined_risco_saude_mental,
            "alertas": combined_alertas,
            "frames_processados": len(frames),
            "tempo_processamento_ms": processing_time_ms,
            "postura_analise": {
                "frames_com_pessoas": len(posture_analyses),
                "indicadores_postura": posture_risk.get("indicadores", []),
                "estatisticas_postura": posture_risk.get("estatisticas", {}),
            },
        }
