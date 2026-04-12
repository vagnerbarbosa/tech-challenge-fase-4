"""Utilitários do projeto.

Este módulo contém funções auxiliares e utilitárias usadas em todo o projeto.
"""

from src.utils.text_utils import (
    extract_words,
    normalize_unicode,
    remove_html_tags,
    sanitize_text_input,
    truncate_text,
)

__all__ = [
    "sanitize_text_input",
    "normalize_unicode",
    "extract_words",
    "remove_html_tags",
    "truncate_text",
]
