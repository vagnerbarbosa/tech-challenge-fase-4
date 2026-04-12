"""Detector de risco baseado em palavras-chave e análise de sentimento."""

from typing import Any

from src.core.config import RISK_KEYWORDS


def calculate_risk(text: str, sentiment: str, confidence_scores: dict[str, float]) -> dict[str, Any]:
    """Calcula níveis de risco baseado em palavras-chave e sentimento Azure.

    Esta função analisa o texto em busca de palavras-chave relacionadas a
    violência doméstica e saúde mental, combinando com o sentimento geral
    do texto para determinar níveis de risco.

    Args:
        text: Texto normalizado para análise
        sentiment: Sentimento classificado pelo Azure (positivo, negativo, neutro, misto)
        confidence_scores: Dicionário com scores de confiança do Azure por sentimento

    Returns:
        Dicionário contendo:
            - risco_violencia: str ("baixo", "medio", "alto")
            - risco_saude_mental: str ("baixo", "medio", "alto")
            - indicadores: list[str] - palavras-chave encontradas
            - score_violencia: int (0-100)
            - score_saude_mental: int (0-100)
    """
    text_lower = text.lower().strip()

    # Detecta palavras-chave
    violencia_matches = _find_keywords(text_lower, RISK_KEYWORDS["violencia"])
    saude_mental_matches = _find_keywords(text_lower, RISK_KEYWORDS["saude_mental"])

    # Calcula scores baseados em palavras-chave
    score_violencia = _calculate_keyword_score(
        violencia_matches, sentiment, confidence_scores
    )
    score_saude_mental = _calculate_keyword_score(
        saude_mental_matches, sentiment, confidence_scores
    )

    # Converte scores em níveis de risco
    risco_violencia = _score_to_risk_level(score_violencia)
    risco_saude_mental = _score_to_risk_level(score_saude_mental)

    # Combina todos os indicadores
    indicadores = list(set(violencia_matches + saude_mental_matches))

    return {
        "risco_violencia": risco_violencia,
        "risco_saude_mental": risco_saude_mental,
        "indicadores": indicadores,
        "score_violencia": score_violencia,
        "score_saude_mental": score_saude_mental,
    }


def _find_keywords(text: str, keywords: list[str]) -> list[str]:
    """Enconca palavras-chave presentes no texto.

    Args:
        text: Texto em minúsculas para busca
        keywords: Lista de palavras-chave a buscar

    Returns:
        Lista de palavras-chave encontradas no texto
    """
    matches = []
    for keyword in keywords:
        if keyword in text:
            matches.append(keyword)
    return matches


def _calculate_keyword_score(
    matches: list[str], sentiment: str, confidence_scores: dict[str, float]
) -> int:
    """Calcula score numérico baseado em palavras-chave e sentimento.

    O score varia de 0 a 100, onde:
    - 0-33: Baixo risco
    - 34-66: Médio risco
    - 67-100: Alto risco

    Args:
        matches: Lista de palavras-chave encontradas
        sentiment: Sentimento classificado pelo Azure
        confidence_scores: Dicionário com scores de confiança

    Returns:
        Score numérico de 0 a 100
    """
    score = 0

    # Pontuação baseada na quantidade de palavras-chave
    # Cada palavra adiciona entre 10-20 pontos
    for _ in matches:
        score += 15

    # Ajusta baseado no sentimento
    sentiment_score = confidence_scores.get("negative", 0.0)

    if sentiment == "negativo":
        # Sentimento negativo com alta confiança aumenta o risco
        score += int(sentiment_score * 30)
    elif sentiment == "misto":
        # Sentimento misto pode indicar conflito emocional
        score += int(sentiment_score * 15)
    elif sentiment == "positivo":
        # Sentimento positivo reduz o risco
        positive_score = confidence_scores.get("positive", 0.0)
        score -= int(positive_score * 20)

    # Garante que o score fique entre 0 e 100
    return max(0, min(100, score))


def _score_to_risk_level(score: int) -> str:
    """Converte score numérico em nível de risco.

    Args:
        score: Score de 0 a 100

    Returns:
        Nível de risco: "baixo", "medio" ou "alto"
    """
    if score >= 60:
        return "alto"
    elif score >= 30:
        return "medio"
    else:
        return "baixo"


