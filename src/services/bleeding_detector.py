"""Detector de sangramento baseado em análise de cor vermelha em imagens.

Este módulo utiliza OpenCV para detectar regiões de sangramento em imagens
médicas através da identificação de pixels vermelhos intensos no espaço de cor HSV.
"""

from typing import Any

import cv2
import numpy as np


class BleedingDetector:
    """Detector de sangramento usando análise de cor em espaço HSV.

    Este detector identifica sangramento em imagens médicas através da
    detecção de pixels vermelhos intensos, utilizando o espaço de cor HSV
    para maior robustez contra variações de iluminação.

    Attributes:
        threshold_percentual: Percentual mínimo de pixels vermelhos para
            considerar sangramento detectado (padrão: 2%).
        max_confidence_percentual: Percentual máximo para normalização
            da confiança (padrão: 5%).
    """

    # Ranges de vermelho em HSV (dois ranges devido à natureza circular do H)
    LOWER_RED1 = np.array([0, 100, 100])
    UPPER_RED1 = np.array([10, 255, 255])
    LOWER_RED2 = np.array([160, 100, 100])
    UPPER_RED2 = np.array([180, 255, 255])

    def __init__(
        self,
        threshold_percentual: float = 2.0,
        max_confidence_percentual: float = 5.0,
    ) -> None:
        """Inicializa o detector de sangramento.

        Args:
            threshold_percentual: Percentual mínimo de pixels vermelhos
                para considerar sangramento detectado. Padrão: 2.0.
            max_confidence_percentual: Percentual máximo usado como base
                para normalização da confiança (confiança = percentual / max).
                Padrão: 5.0.
        """
        self.threshold_percentual = threshold_percentual
        self.max_confidence_percentual = max_confidence_percentual

    def detect(self, image: np.ndarray) -> dict[str, Any]:
        """Detecta sangramento na imagem fornecida.

        Processo:
        1. Converte a imagem para espaço de cor HSV
        2. Aplica máscaras para identificar pixels vermelhos
        3. Calcula o percentual de pixels vermelhos
        4. Encontra a maior área contígua de sangramento
        5. Retorna resultados com bounding box e confiança

        Args:
            image: Imagem no formato numpy array (BGR ou RGB).
                   Suporta imagens em escala de cinza ou coloridas.

        Returns:
            Dicionário contendo:
                - detectado: bool - True se sangramento detectado (> threshold)
                - confianca: float - Confiança normalizada (0-1)
                - percentual_vermelho: float - Percentual de pixels vermelhos
                - bbox: dict com x, y, w, h da maior área, ou None se não detectado

        Raises:
            ValueError: Se a imagem for inválida ou vazia.
        """
        if image is None or image.size == 0:
            raise ValueError("Imagem inválida ou vazia")

        # Converte para HSV se necessário
        if len(image.shape) == 2:
            # Imagem em escala de cinza - converte para BGR primeiro
            hsv_image = cv2.cvtColor(cv2.cvtColor(image, cv2.COLOR_GRAY2BGR), cv2.COLOR_BGR2HSV)
        elif len(image.shape) == 3 and image.shape[2] == 3:
            # Imagem colorida (BGR ou RGB)
            # OpenCV usa BGR por padrão, assume BGR
            hsv_image = cv2.cvtColor(image, cv2.COLOR_BGR2HSV)
        else:
            raise ValueError(f"Formato de imagem não suportado: shape={image.shape}")

        # Cria máscaras para os dois ranges de vermelho
        mask1 = cv2.inRange(hsv_image, self.LOWER_RED1, self.UPPER_RED1)
        mask2 = cv2.inRange(hsv_image, self.LOWER_RED2, self.UPPER_RED2)

        # Combina as máscaras (vermelho pode estar em ambos os ranges)
        red_mask = cv2.bitwise_or(mask1, mask2)

        # Calcula percentual de pixels vermelhos
        total_pixels = image.shape[0] * image.shape[1]
        red_pixels = cv2.countNonZero(red_mask)
        percentual_vermelho = (red_pixels / total_pixels) * 100.0

        # Determina se houve detecção
        detectado = percentual_vermelho > self.threshold_percentual

        # Calcula confiança normalizada (limitada a 1.0)
        confianca = min(percentual_vermelho / self.max_confidence_percentual, 1.0)

        # Encontra bounding box da maior área vermelha
        bbox = None
        if detectado and red_pixels > 0:
            bbox = self._find_largest_contour_bbox(red_mask)

        return {
            "detectado": detectado,
            "confianca": round(confianca, 4),
            "percentual_vermelho": round(percentual_vermelho, 4),
            "bbox": bbox,
        }

    def _find_largest_contour_bbox(self, mask: np.ndarray) -> dict[str, float] | None:
        """Encontra o bounding box do maior contorno na máscara.

        Args:
            mask: Máscara binária (pixels vermelhos = 255).

        Returns:
            Dicionário com x, y, w, h normalizados (0-1) do maior contorno,
            ou None se não houver contornos.
        """
        # Encontra contornos
        contours, _ = cv2.findContours(
            mask, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE
        )

        if not contours:
            return None

        # Encontra o maior contorno por área
        largest_contour = max(contours, key=cv2.contourArea)

        # Calcula bounding box
        x, y, w, h = cv2.boundingRect(largest_contour)

        # Obtém dimensões da máscara para normalização
        mask_height, mask_width = mask.shape[:2]

        # Normaliza coordenadas para 0-1
        return {
            "x": round(float(x) / mask_width, 4),
            "y": round(float(y) / mask_height, 4),
            "w": round(float(w) / mask_width, 4),
            "h": round(float(h) / mask_height, 4),
        }


def get_bleeding_detector() -> BleedingDetector:
    """Obtém instância padrão do detector de sangramento.

    Returns:
        Instância de BleedingDetector com configurações padrão.
    """
    return BleedingDetector()
