"""Analisador de postura e linguagem corporal.

Este módulo analisa a postura e movimento de pessoas detectadas
em vídeos para identificar sinais de desconforto ou medo.
"""

from dataclasses import dataclass
from typing import Any

import numpy as np


@dataclass
class PostureMetrics:
    """Métricas de postura para uma detecção de pessoa."""

    aspect_ratio: float  # Razão altura/largura
    centroid_x: float  # Posição X normalizada (0-1)
    centroid_y: float  # Posição Y normalizada (0-1)
    is_defensive: bool  # Postura defensiva detectada
    movement_variance: float  # Variância de movimento


@dataclass
class FramePostureAnalysis:
    """Análise de postura para um frame específico."""

    frame_number: int
    timestamp: float
    person_detections: list[dict[str, Any]]
    metrics: list[PostureMetrics]
    risk_indicators: list[str]


class PostureAnalyzer:
    """Analisador de postura e linguagem corporal.

    Detecta sinais de desconforto ou medo através de:
    1. Análise de proporção do bounding box (postura fechada vs aberta)
    2. Análise de movimento (agitação vs imobilidade)
    3. Posição no frame (encolhida, recuada)

    Attributes:
        history: Histórico de posições para cálculo de variância
        defensive_threshold: Threshold para considerar postura defensiva
        movement_threshold: Threshold para detecção de agitação
    """

    # Thresholds para análise
    DEFENSIVE_ASPECT_RATIO_MAX = 1.8  # Postura fechada: razão baixa
    DEFENSIVE_ASPECT_RATIO_MIN = 0.8  # Postura muito fechada
    AGITATION_THRESHOLD = 0.05  # Variância alta = agitação
    IMMOBILITY_THRESHOLD = 0.001  # Variância muito baixa = rigidez
    CENTER_ZONE = 0.3  # Zona central do frame (0.3-0.7)

    def __init__(self, history_size: int = 5) -> None:
        """Inicializa o analisador de postura.

        Args:
            history_size: Número de frames para manter no histórico
        """
        self.history_size = history_size
        self._position_history: list[list[tuple[float, float]]] = []

    def analyze_frame(
        self,
        detections: list[dict[str, Any]],
        frame_number: int,
        timestamp: float,
    ) -> FramePostureAnalysis:
        """Analisa postura em um frame específico.

        Args:
            detections: Lista de detecções YOLO (apenas classe 'person')
            frame_number: Número do frame
            timestamp: Timestamp do frame em segundos

        Returns:
            FramePostureAnalysis com métricas e indicadores de risco
        """
        metrics: list[PostureMetrics] = []
        risk_indicators: list[str] = []
        person_detections: list[dict[str, Any]] = []
        current_positions: list[tuple[float, float]] = []

        for det in detections:
            if det.get("classe") != "person":
                continue

            person_detections.append(det)
            bbox = det.get("bbox", {})

            if not bbox:
                continue

            # Calcular métricas do bounding box
            x, y, w, h = bbox.get("x", 0), bbox.get("y", 0), bbox.get("w", 0), bbox.get("h", 0)

            # Razão altura/largura (aspect ratio)
            aspect_ratio = h / w if w > 0 else 0

            # Centroid normalizado
            centroid_x = x + w / 2
            centroid_y = y + h / 2
            current_positions.append((centroid_x, centroid_y))

            # Detectar postura defensiva
            is_defensive = self._is_defensive_posture(aspect_ratio, centroid_y)

            # Calcular variância de movimento
            movement_variance = self._calculate_movement_variance(
                len(metrics), centroid_x, centroid_y
            )

            metric = PostureMetrics(
                aspect_ratio=aspect_ratio,
                centroid_x=centroid_x,
                centroid_y=centroid_y,
                is_defensive=is_defensive,
                movement_variance=movement_variance,
            )
            metrics.append(metric)

            # Identificar indicadores de risco
            if is_defensive:
                risk_indicators.append("postura_defensiva")

            if self._is_agitated(movement_variance):
                risk_indicators.append("agitacao")

            if self._is_immobile(movement_variance):
                risk_indicators.append("rigidez")

            if self._is_positioned_defensively(centroid_x, centroid_y):
                risk_indicators.append("posicao_reclusa")

        # Atualizar histórico
        self._update_history(current_positions)

        return FramePostureAnalysis(
            frame_number=frame_number,
            timestamp=timestamp,
            person_detections=person_detections,
            metrics=metrics,
            risk_indicators=list(set(risk_indicators)),  # Remover duplicatas
        )

    def _is_defensive_posture(self, aspect_ratio: float, centroid_y: float) -> bool:
        """Detecta se a postura é defensiva.

        Postura defensiva:
        - Razão altura/largura baixa (pessoa "encolhida")
        - Posição baixa no frame (agachada ou sentada)

        Args:
            aspect_ratio: Razão altura/largura do bounding box
            centroid_y: Posição Y do centroid (0-1)

        Returns:
            True se postura defensiva detectada
        """
        # Postura fechada: razão entre 0.8 e 1.8
        is_closed = (
            self.DEFENSIVE_ASPECT_RATIO_MIN <= aspect_ratio <= self.DEFENSIVE_ASPECT_RATIO_MAX
        )

        # Posição baixa: centroid Y > 0.6 (parte inferior do frame)
        is_low = centroid_y > 0.6

        return is_closed and is_low

    def _calculate_movement_variance(
        self, person_index: int, current_x: float, current_y: float
    ) -> float:
        """Calcula variância de movimento para uma pessoa.

        Args:
            person_index: Índice da pessoa no histórico
            current_x: Posição X atual
            current_y: Posição Y atual

        Returns:
            Variância do movimento (quanto maior, mais agitada)
        """
        if len(self._position_history) < 2:
            return 0.0

        # Pegar histórico desta pessoa
        person_history = []
        for frame_positions in self._position_history:
            if person_index < len(frame_positions):
                person_history.append(frame_positions[person_index])

        if len(person_history) < 2:
            return 0.0

        # Calcular variância das posições
        positions = np.array(person_history)
        variance = np.var(positions, axis=0)

        # Variância total (magnitude)
        return float(np.sqrt(variance[0] ** 2 + variance[1] ** 2))

    def _is_agitated(self, movement_variance: float) -> bool:
        """Detecta se há agitação excessiva."""
        return movement_variance > self.AGITATION_THRESHOLD

    def _is_immobile(self, movement_variance: float) -> bool:
        """Detecta rigidez (imobilidade)."""
        return movement_variance < self.IMMOBILITY_THRESHOLD and movement_variance > 0

    def _is_positioned_defensively(self, centroid_x: float, centroid_y: float) -> bool:
        """Detecta posição defensiva no frame.

        Posição defensiva: afastada das áreas centrais,
        geralmente em cantos ou bordas.
        """
        # Longe do centro (posição reclusa)
        is_off_center = (
            centroid_x < self.CENTER_ZONE
            or centroid_x > (1 - self.CENTER_ZONE)
            or centroid_y > (1 - self.CENTER_ZONE)
        )

        return is_off_center

    def _update_history(self, positions: list[tuple[float, float]]) -> None:
        """Atualiza o histórico de posições."""
        self._position_history.append(positions)

        # Manter apenas os últimos N frames
        if len(self._position_history) > self.history_size:
            self._position_history.pop(0)

    def reset(self) -> None:
        """Reseta o histórico de análise."""
        self._position_history.clear()


def calculate_posture_risk(
    frame_analyses: list[FramePostureAnalysis],
) -> dict[str, Any]:
    """Calcula risco baseado nas análises de postura.

    Args:
        frame_analyses: Lista de análises de frames

    Returns:
        Dicionário com risco de violência e saúde mental
    """
    if not frame_analyses:
        return {
            "risco_violencia": "baixo",
            "risco_saude_mental": "baixo",
            "indicadores": [],
            "alertas": [],
        }

    # Contar indicadores ao longo do tempo
    all_indicators: list[str] = []
    defensive_count = 0
    agitation_count = 0
    immobility_count = 0

    for analysis in frame_analyses:
        all_indicators.extend(analysis.risk_indicators)

        for metric in analysis.metrics:
            if metric.is_defensive:
                defensive_count += 1
            if metric.movement_variance > PostureAnalyzer.AGITATION_THRESHOLD:
                agitation_count += 1
            elif metric.movement_variance < PostureAnalyzer.IMMOBILITY_THRESHOLD:
                immobility_count += 1

    # Determinar risco
    total_frames = len(frame_analyses)
    unique_indicators = set(all_indicators)

    risco_violencia = "baixo"
    risco_saude_mental = "baixo"
    alertas: list[dict[str, Any]] = []

    # Risco alto se múltiplos indicadores em muitos frames
    if defensive_count >= total_frames * 0.3 or "postura_defensiva" in unique_indicators:
        risco_violencia = "medio"

    if agitation_count >= total_frames * 0.4:
        risco_saude_mental = "medio"
        alertas.append({
            "tipo": "agitacao_detectada",
            "severidade": "media",
            "descricao": "Movimentação excessiva detectada",
        })

    if immobility_count >= total_frames * 0.3:
        risco_saude_mental = "alto" if risco_saude_mental == "medio" else "medio"
        alertas.append({
            "tipo": "rigidez_detectada",
            "severidade": "alta",
            "descricao": "Postura rígida ou imobilidade detectada",
        })

    # Postura defensiva persistente = risco alto de violência
    if defensive_count >= total_frames * 0.5:
        risco_violencia = "alto"
        alertas.append({
            "tipo": "postura_defensiva_persistente",
            "severidade": "alta",
            "descricao": "Postura defensiva persistente detectada",
        })

    return {
        "risco_violencia": risco_violencia,
        "risco_saude_mental": risco_saude_mental,
        "indicadores": list(unique_indicators),
        "alertas": alertas,
        "estatisticas": {
            "frames_analisados": total_frames,
            "posturas_defensivas": defensive_count,
            "agitacao_detectada": agitation_count,
            "rigidez_detectada": immobility_count,
        },
    }
