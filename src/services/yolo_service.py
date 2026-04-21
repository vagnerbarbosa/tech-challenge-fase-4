"""Serviço de detecção de objetos usando YOLOv8 para análise de vídeo."""

from typing import Any

import numpy as np
from ultralytics import YOLO  # type: ignore[attr-defined]


class YOLOv8Service:
    """Serviço para detecção de objetos em vídeo usando YOLOv8.

    Este serviço utiliza o modelo YOLOv8n (nano) otimizado para CPU,
    detectando objetos relevantes para contexto médico e segurança:
    - Pessoas (rastreamento de movimento)
    - Tesouras e facas (instrumentos/detecção de risco)

    Attributes:
        model: Instância do modelo YOLO carregado
        model_path: Caminho para o arquivo do modelo
        relevant_classes: IDs das classes COCO de interesse
    """

    # Mapeamento de classes COCO relevantes
    COCO_CLASSES = {
        "person": 0,
        "knife": 43,
        "scissors": 77,
    }

    def __init__(self, model_name: str = "yolov8n.pt") -> None:
        """Inicializa o serviço YOLOv8 carregando o modelo.

        O modelo YOLOv8n (nano) tem aproximadamente 6MB e é
        otimizado para execução em CPU, ideal para containers.

        Args:
            model_name: Nome do modelo YOLO a ser carregado.
                       Padrão: "yolov8n.pt" (modelo nano mais leve)

        Raises:
            RuntimeError: Se houver erro ao carregar o modelo
        """
        self.model_name = model_name
        self.model: YOLO | None = None
        self.relevant_class_ids = set(self.COCO_CLASSES.values())

        try:
            self.model = YOLO(model_name)
        except Exception as e:
            raise RuntimeError(f"Erro ao carregar modelo YOLO {model_name}: {e}") from e

    def detect(
        self, image: np.ndarray, conf_threshold: float = 0.5
    ) -> list[dict[str, Any]]:
        """Executa detecção de objetos em uma imagem.

        Args:
            image: Array numpy da imagem (formato BGR - padrão OpenCV)
            conf_threshold: Limiar mínimo de confiança (0.0 a 1.0)
                           Padrão: 0.5 (50% de confiança)

        Returns:
            Lista de detecções, cada uma contendo:
                - classe: Nome da classe detectada (ex: "person")
                - confianca: Score de confiança (0.0 a 1.0)
                - bbox: Dicionário com x, y, w, h (coordenadas normalizadas 0-1)

        Raises:
            ValueError: Se a imagem for inválida
            RuntimeError: Se o modelo não estiver carregado
        """
        if self.model is None:
            raise RuntimeError("Modelo YOLO não foi carregado")

        if not isinstance(image, np.ndarray) or image.size == 0:
            raise ValueError("Imagem inválida: deve ser um array numpy não vazio")

        # Executa inferência com tamanho otimizado para CPU (320x320)
        results = self.model(image, verbose=False, imgsz=320)

        detections: list[dict[str, Any]] = []

        if not results or len(results) == 0:
            return detections

        result = results[0]

        if result.boxes is None or len(result.boxes) == 0:
            return detections

        # Obtém dimensões da imagem para normalização
        img_height, img_width = image.shape[:2]

        # Processa cada detecção
        for box in result.boxes:
            confidence = float(box.conf.item())

            # Filtra por limiar de confiança
            if confidence < conf_threshold:
                continue

            class_id = int(box.cls.item())

            # Filtra apenas classes relevantes
            if class_id not in self.relevant_class_ids:
                continue

            # Obtém nome da classe
            class_name = self._get_class_name(class_id)

            # Extrai bounding box (xyxy format -> x, y, w, h normalizado)
            x1, y1, x2, y2 = box.xyxy[0].cpu().numpy()

            # Converte para formato x, y, w, h normalizado (0-1)
            x = float(x1) / img_width
            y = float(y1) / img_height
            w = (float(x2) - float(x1)) / img_width
            h = (float(y2) - float(y1)) / img_height

            detection = {
                "classe": class_name,
                "confianca": round(confidence, 4),
                "bbox": {
                    "x": round(x, 4),
                    "y": round(y, 4),
                    "w": round(w, 4),
                    "h": round(h, 4),
                },
            }
            detections.append(detection)

        return detections

    def _get_class_name(self, class_id: int) -> str:
        """Obtém o nome da classe a partir do ID.

        Args:
            class_id: ID da classe COCO

        Returns:
            Nome da classe (ex: "person", "knife", "scissors")
        """
        for name, cid in self.COCO_CLASSES.items():
            if cid == class_id:
                return name
        return "unknown"

    def get_supported_classes(self) -> dict[str, int]:
        """Retorna as classes suportadas pelo serviço.

        Returns:
            Dicionário mapeando nome da classe para ID COCO
        """
        return self.COCO_CLASSES.copy()
