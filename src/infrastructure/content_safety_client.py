"""Cliente Azure AI Content Safety para detecção multilíngue de risco.

Este módulo fornece acesso ao Azure AI Content Safety API, que detecta
conteúdo prejudicial (autoagressão, violência, discurso de ódio) de forma
agnóstica a idioma, suportando 100+ línguas automaticamente.
"""

import os
from dataclasses import dataclass
from functools import lru_cache
from typing import Any

import requests  # type: ignore[import-untyped]
from azure.core.credentials import AzureKeyCredential

from src.infrastructure.azure_clients import (
    AuthenticationError,
    AzureClientError,
    AzureConfigurationError,
    AzureConnectionError,
    QuotaExceededError,
)


@dataclass
class ContentSafetyResult:
    """Resultado da análise de Content Safety.

    Attributes:
        self_harm_severity: Severidade de autoagressão (0-6)
        violence_severity: Severidade de violência (0-6)
        hate_severity: Severidade de discurso de ódio (0-6)
        sexual_severity: Severidade de conteúdo sexual (0-6)
        is_harmful: True se alguma categoria tem severidade > 2
        highest_category: Categoria com maior severidade
        highest_severity: Valor da maior severidade
    """

    self_harm_severity: int
    violence_severity: int
    hate_severity: int
    sexual_severity: int

    @property
    def is_harmful(self) -> bool:
        """Retorna True se conteúdo é potencialmente prejudicial."""
        return max(
            self.self_harm_severity,
            self.violence_severity,
            self.hate_severity,
            self.sexual_severity,
        ) > 2

    @property
    def highest_category(self) -> str:
        """Retorna categoria com maior severidade."""
        severities: dict[str, int] = {
            "SelfHarm": self.self_harm_severity,
            "Violence": self.violence_severity,
            "Hate": self.hate_severity,
            "Sexual": self.sexual_severity,
        }
        return max(severities.items(), key=lambda x: x[1])[0]

    @property
    def highest_severity(self) -> int:
        """Retorna valor da maior severidade."""
        return max(
            self.self_harm_severity,
            self.violence_severity,
            self.hate_severity,
            self.sexual_severity,
        )

    def to_dict(self) -> dict[str, Any]:
        """Converte resultado para dicionário."""
        return {
            "self_harm_severity": self.self_harm_severity,
            "violence_severity": self.violence_severity,
            "hate_severity": self.hate_severity,
            "sexual_severity": self.sexual_severity,
            "is_harmful": self.is_harmful,
            "highest_category": self.highest_category,
            "highest_severity": self.highest_severity,
        }


class ContentSafetyClient:
    """Cliente para Azure AI Content Safety API.

    Detecta conteúdo prejudicial em múltiplos idiomas sem necessidade
    de configuração específica por língua.

    Attributes:
        endpoint: Endpoint do Azure Content Safety
        credential: Credencial Azure
        api_version: Versão da API
    """

    def __init__(
        self,
        endpoint: str | None = None,
        key: str | None = None,
        api_version: str = "2024-09-01",
    ):
        """Inicializa cliente Content Safety.

        Args:
            endpoint: Endpoint do Content Safety (ou None para usar env var)
            key: Chave de API (ou None para usar env var)
            api_version: Versão da API

        Raises:
            AzureConfigurationError: Se credenciais não forem fornecidas
        """
        self.endpoint = endpoint or os.getenv("AZURE_CONTENT_SAFETY_ENDPOINT")
        key = key or os.getenv("AZURE_CONTENT_SAFETY_KEY")

        if not self.endpoint or not key:
            raise AzureConfigurationError(
                "Credenciais do Azure Content Safety não configuradas. "
                "Configure AZURE_CONTENT_SAFETY_ENDPOINT e AZURE_CONTENT_SAFETY_KEY."
            )

        # Remove trailing slash do endpoint
        self.endpoint = self.endpoint.rstrip("/")
        self.credential = AzureKeyCredential(key)
        self.api_version = api_version

    def analyze_text(
        self,
        text: str,
        categories: list[str] | None = None,
        output_type: str = "FourSeverityLevels",
    ) -> ContentSafetyResult:
        """Analisa texto para conteúdo prejudicial.

        Args:
            text: Texto para analisar
            categories: Lista de categorias (SelfHarm, Violence, Hate, Sexual)
            output_type: Tipo de output (FourSeverityLevels, EightSeverityLevels)

        Returns:
            ContentSafetyResult com severidades por categoria

        Raises:
            QuotaExceededError: Quando quota é excedida
            AuthenticationError: Quando autenticação falha
            AzureConnectionError: Quando conexão falha
        """
        if not categories:
            categories = ["SelfHarm", "Violence", "Hate", "Sexual"]

        url = f"{self.endpoint}/contentsafety/text:analyze"
        params = {"api-version": self.api_version}

        headers = {
            "Content-Type": "application/json",
            "Ocp-Apim-Subscription-Key": self.credential.key,
        }

        body = {
            "text": text,
            "categories": categories,
            "outputType": output_type,
        }

        try:
            response = requests.post(
                url,
                params=params,
                headers=headers,
                json=body,
                timeout=30,
            )
            response.raise_for_status()
            data = response.json()

            return self._parse_response(data)

        except requests.exceptions.HTTPError as e:
            if response.status_code == 429:
                raise QuotaExceededError(
                    "Quota do Azure Content Safety excedida."
                ) from e
            elif response.status_code in (401, 403):
                raise AuthenticationError(
                    "Autenticação Azure Content Safety falhou."
                ) from e
            else:
                raise AzureClientError(
                    f"Erro na API Content Safety: {e}"
                ) from e

        except requests.exceptions.RequestException as e:
            raise AzureConnectionError(
                f"Falha ao conectar ao Content Safety: {e}"
            ) from e

    def _parse_response(self, data: dict[str, Any]) -> ContentSafetyResult:
        """Parse da resposta da API Content Safety.

        Args:
            data: JSON da resposta da API

        Returns:
            ContentSafetyResult com severidades extraídas
        """
        categories_analysis = data.get("categoriesAnalysis", [])

        severities = {
            "SelfHarm": 0,
            "Violence": 0,
            "Hate": 0,
            "Sexual": 0,
        }

        for category in categories_analysis:
            cat_name = category.get("category", "")
            severity = category.get("severity", 0)
            if cat_name in severities:
                severities[cat_name] = severity

        return ContentSafetyResult(
            self_harm_severity=severities["SelfHarm"],
            violence_severity=severities["Violence"],
            hate_severity=severities["Hate"],
            sexual_severity=severities["Sexual"],
        )

    def analyze_batch(
        self,
        texts: list[str],
        categories: list[str] | None = None,
    ) -> list[ContentSafetyResult]:
        """Analisa múltiplos textos em batch.

        Args:
            texts: Lista de textos para analisar
            categories: Lista de categorias

        Returns:
            Lista de ContentSafetyResult
        """
        return [
            self.analyze_text(text, categories)
            for text in texts
            if text.strip()
        ]


@lru_cache
def get_content_safety_client() -> ContentSafetyClient:
    """Obtém cliente Content Safety singleton.

    Returns:
        Instância cached de ContentSafetyClient
    """
    return ContentSafetyClient()
