"""Serviços de análise e processamento de dados."""

from src.services.risk_detector import calculate_risk
from src.services.text_analysis import (
    TextAnalysisError,
    TextAnalysisService,
    get_text_analysis_service,
)

__all__ = [
    "calculate_risk",
    "TextAnalysisService",
    "TextAnalysisError",
    "get_text_analysis_service",
]
