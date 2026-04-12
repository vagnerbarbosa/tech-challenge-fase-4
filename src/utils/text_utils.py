"""Utilitários para processamento de texto.

Este módulo contém funções genéricas para manipulação e sanitização de texto.
"""

import re
import unicodedata


def sanitize_text_input(text: str) -> str:
    """Sanitiza entrada de texto removendo caracteres problemáticos.

    Remove:
    - Caracteres de largura zero (zero-width)
    - Caracteres de controle
    - Espaços excessivos
    - Normaliza quebras de linha

    Args:
        text: Texto de entrada

    Returns:
        Texto sanitizado
    """
    # Remove caracteres de largura zero
    zero_width_chars = [
        "\u200b",  # Zero width space
        "\u200c",  # Zero width non-joiner
        "\u200d",  # Zero width joiner
        "\ufeff",  # Zero width no-break space (BOM)
        "\u2060",  # Word joiner
        "\u200e",  # Left-to-right mark
        "\u200f",  # Right-to-left mark
    ]

    sanitized = text
    for char in zero_width_chars:
        sanitized = sanitized.replace(char, "")

    # Remove caracteres de controle (exceto quebras de linha normais)
    sanitized = "".join(
        char for char in sanitized
        if char == "\n" or char == "\r" or (ord(char) >= 32 and ord(char) != 127)
    )

    # Normaliza quebras de linha
    sanitized = sanitized.replace("\r\n", "\n").replace("\r", "\n")

    # Remove espaços excessivos
    sanitized = " ".join(sanitized.split())

    return sanitized.strip()


def normalize_unicode(text: str) -> str:
    """Normaliza texto para forma NFKC.

    Converte caracteres Unicode para forma canônica compatível.
    Útil para padronizar texto antes de comparações.

    Args:
        text: Texto de entrada

    Returns:
        Texto normalizado
    """
    return unicodedata.normalize("NFKC", text)


def extract_words(text: str, min_length: int = 3) -> list[str]:
    """Extrai palavras de um texto.

    Args:
        text: Texto de entrada
        min_length: Tamanho mínimo das palavras (padrão: 3)

    Returns:
        Lista de palavras extraídas
    """
    words = re.findall(r'\b[a-zA-ZÀ-ÿ]+\b', text.lower())
    return [w for w in words if len(w) >= min_length]


def remove_html_tags(text: str) -> str:
    """Remove tags HTML do texto.

    Args:
        text: Texto que pode conter tags HTML

    Returns:
        Texto sem tags HTML
    """
    clean = re.compile('<.*?>')
    return re.sub(clean, '', text)


def truncate_text(text: str, max_length: int, suffix: str = "...") -> str:
    """Trunca texto para um tamanho máximo.

    Args:
        text: Texto de entrada
        max_length: Tamanho máximo desejado
        suffix: Sufixo a adicionar se truncado (padrão: "...")

    Returns:
        Texto truncado se necessário
    """
    if len(text) <= max_length:
        return text
    return text[:max_length - len(suffix)] + suffix
