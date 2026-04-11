"""Serviços de análise e processamento de dados."""

from src.services.risk_detector import calculate_risk, sanitize_text_input
from src.services.text_analysis import (
    TextAnalysisError,
    TextAnalysisService,
    get_text_analysis_service,
)

__all__ = [
    "calculate_risk",
    "sanitize_text_input",
    "TextAnalysisService",
    "TextAnalysisError",
    "get_text_analysis_service",
]
