"""Rotas para análise de texto."""

from typing import Annotated, Any

from fastapi import APIRouter, Depends, HTTPException, Request, status

from src.models.schemas import TextAnalysisRequest, TextAnalysisResponse
from src.services.text_analysis import (
    TextAnalysisError,
    TextAnalysisService,
    get_text_analysis_service,
)

# Dependency type reutilizável com Annotated (Python 3.9+)
TextAnalysisServiceDep = Annotated[TextAnalysisService, Depends(get_text_analysis_service)]

router = APIRouter(prefix="/analyze", tags=["Text Analysis"])


@router.post(
    "/text",
    response_model=TextAnalysisResponse,
    status_code=status.HTTP_200_OK,
    summary="Analisa texto para sentimento e riscos",
    description="Recebe um texto em português e retorna análise de sentimento, níveis de risco e palavras-chave.",
    responses={
        200: {
            "description": "Análise realizada com sucesso",
            "model": TextAnalysisResponse,
        },
        400: {
            "description": "Dados de entrada inválidos",
            "content": {
                "application/json": {
                    "example": {
                        "error": "VALIDATION_ERROR",
                        "message": "Dados de entrada inválidos",
                        "details": [{
                            "field": "texto",
                            "message": "Texto deve ter entre 10 e 5000 caracteres",
                        }],
                    }
                }
            },
        },
        429: {
            "description": "Limite de requisições excedido",
            "content": {
                "application/json": {
                    "example": {
                        "error": "QUOTA_EXCEEDED",
                        "message": "Limite de requisições ao Azure excedido",
                        "retry_after": 3600,
                    }
                }
            },
        },
        502: {
            "description": "Erro no serviço Azure",
            "content": {
                "application/json": {
                    "example": {
                        "error": "AZURE_SERVICE_ERROR",
                        "message": "Erro ao comunicar com serviço Azure",
                    }
                }
            },
        },
        503: {
            "description": "Serviço indisponível",
            "content": {
                "application/json": {
                    "example": {
                        "error": "SERVICE_UNAVAILABLE",
                        "message": "Configuração Azure não encontrada",
                    }
                }
            },
        },
    },
)
async def analyze_text(
    request: Request,
    analysis_request: TextAnalysisRequest,
    service: TextAnalysisServiceDep,
) -> Any:
    """Endpoint para análise de texto.

    Recebe um texto em português e retorna:
    - Sentimento (positivo, negativo, neutro, misto)
    - Score de sentimento (-1.0 a 1.0)
    - Risco de violência (baixo, medio, alto)
    - Risco de saúde mental (baixo, medio, alto)
    - Palavras-chave extraídas
    - Indicadores de risco encontrados
    - Metadados do processamento

    Args:
        request: Objeto Request do FastAPI
        analysis_request: Dados da requisição de análise
        service: Serviço de análise de texto (injeção de dependência)

    Returns:
        TextAnalysisResponse com resultados da análise

    Raises:
        HTTPException: Em caso de erro na análise
    """
    try:
        result = await service.analyze(
            text=analysis_request.texto,
            tipo=analysis_request.tipo or "geral",
            patient_id=analysis_request.patient_id,
        )
        return result

    except TextAnalysisError as e:
        raise HTTPException(
            status_code=e.status_code,
            detail={
                "error": "ANALYSIS_ERROR",
                "message": e.message,
            },
        ) from e
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail={
                "error": "INTERNAL_ERROR",
                "message": "Erro interno ao processar análise",
            },
        ) from e


@router.get(
    "/text/cache/stats",
    summary="Retorna estatísticas do cache",
    description="Retorna informações sobre o cache de análises em memória.",
    responses={
        200: {
            "description": "Estatísticas do cache",
            "content": {
                "application/json": {
                    "example": {
                        "entries": 150,
                        "ttl_minutes": 60.0,
                    }
                }
            },
        },
    },
)
async def get_cache_stats(
    service: TextAnalysisServiceDep,
) -> dict[str, Any]:
    """Retorna estatísticas do cache de análises.

    Args:
        service: Serviço de análise de texto

    Returns:
        Dicionário com estatísticas do cache
    """
    # Acesso ao cache através do serviço
    from src.core.cache import get_cache

    cache = get_cache()
    return cache.get_stats()


@router.post(
    "/text/cache/clear",
    summary="Limpa o cache",
    description="Remove todas as entradas do cache de análises.",
    responses={
        200: {
            "description": "Cache limpo com sucesso",
            "content": {
                "application/json": {
                    "example": {
                        "message": "Cache limpo com sucesso",
                    }
                }
            },
        },
    },
)
async def clear_cache(
    service: TextAnalysisServiceDep,
) -> dict[str, str]:
    """Limpa todas as entradas do cache.

    Args:
        service: Serviço de análise de texto

    Returns:
        Confirmação de limpeza do cache
    """
    from src.core.cache import get_cache

    cache = get_cache()
    cache.clear_all()
    return {"message": "Cache limpo com sucesso"}
