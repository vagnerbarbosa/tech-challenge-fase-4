# Feature Specification: Análise de Texto

**Feature Branch**: `feature/002-text-analysis`
**Created**: 2026-04-11
**Status**: ✅ Concluído
**Input**: User description: "Implementar endpoint de análise de texto usando Azure Text Analytics"

---

## User Scenarios & Testing

### User Story 1 - Análise de Sentimento (Priority: P1)

Como profissional de saúde, quero submeter textos de prontuários ou diários para identificar sentimentos e riscos.

**Why this priority**: Análise de texto é uma das 3 modalidades obrigatórias do projeto e base para fusão multimodal.

**Independent Test**: POST `/analyze/text` retorna análise completa mesmo sem as outras modalidades implementadas.

**Acceptance Scenarios**:

1. **Given** um texto válido, **When** submeto ao endpoint, **Then** recebo sentimento (positivo/negativo/neutro) com score
2. **Given** texto com sinais de violência, **When** processado, **Then** identifica risco_violencia como alto
3. **Given** texto com sinais de ansiedade, **When** processado, **Then** identifica risco_saude_mental como alto
4. **Given** texto menor que 10 caracteres, **When** submetido, **Then** retorna erro 400 com mensagem clara

### User Story 2 - Integração Azure Text Analytics (Priority: P1)

Como sistema, quero integrar com Azure Text Analytics para análise de sentimento confiável.

**Why this priority**: Azure Text Analytics é requisito obrigatório (Azure AI Services).

**Independent Test**: Verificar se chamadas Azure estão sendo feitas corretamente.

**Acceptance Scenarios**:

1. **Given** credenciais Azure configuradas, **When** analiso texto, **Then** chama API Azure Text Analytics
2. **Given** Azure indisponível, **When** tento analisar, **Then** retorna erro 502 com mensagem amigável
3. **Given** quota Azure excedida, **When** tento analisar, **Then** retorna erro 429 com informações de retry

### User Story 3 - Extração de Palavras-Chave (Priority: P2)

Como profissional de saúde, quero ver palavras-chave extraídas do texto para entender indicadores.

**Why this priority**: Ajuda na interpretação dos resultados, embora não seja crítico para MVP.

**Independent Test**: Response inclui array de palavras_chave.

**Acceptance Scenarios**:

1. **Given** texto com conteúdo emocional, **When** analisado, **Then** extrai palavras indicativas (ansiedade, medo, etc.)

---

## Requirements

### Functional Requirements

- **FR-001**: Endpoint POST `/analyze/text` disponível
- **FR-002**: Aceita texto em português (min: 10, max: 5000 caracteres)
- **FR-003**: Integra com Azure Text Analytics para sentimento
- **FR-004**: Retorna obrigatoriamente: risco_violencia, risco_saude_mental
- **FR-005**: Retorna: sentimento, score (-1 a 1), palavras_chave
- **FR-006**: Validação de entrada com erro 400 para dados inválidos
- **FR-007**: Campos obrigatórios risco_violencia e risco_saude_mental em todas respostas
- **FR-008**: Implementar cache em memória com TTL 1h para evitar reprocessamento
- **FR-009**: Usar lista pré-definida de palavras-chave de risco para detecção local

### Key Entities

- **TextAnalysisRequest**: { texto: str, tipo: str, patient_id: str }
- **TextAnalysisResponse**: { sentimento: str, score: float, risco_violencia: str, risco_saude_mental: str, palavras_chave: list, metadata: object }
- **TextAnalysisService**: Lógica de negócio e integração Azure

---

## Success Criteria

- **SC-001**: Latência média < 2 segundos
- **SC-002**: Precisão de detecção > 80% (conforme critérios do projeto)
- **SC-003**: Campos risco_violencia e risco_saude_mental sempre presentes
- **SC-004**: Integração Azure testada e funcional

---

## Assumptions

- Azure Text Analytics credenciais disponíveis (.env)
- Free Tier: 5.000 requests/mês (suficiente para desenvolvimento)
- Texto em português do Brasil (pt-BR)
- Não armazenamos o texto original (LGPD)

---

## Technical Notes

### Azure Text Analytics SDK
- Pacote: `azure-ai-textanalytics>=5.4.0`
- Endpoint: Configurado via env var
- Região: Brazil South (recomendado para latência)

### Rate Limiting Considerations
- Daily limit: ~160 requests (5000/30)
- Implementar cache para evitar reprocessamento
- Logar uso para monitoramento

### Detecção de Risco
```python
# Configuração de palavras-chave de risco
RISK_KEYWORDS = {
    "violencia": ["violência", "agressão", "ameaça", "bater", "machucar"],
    "saude_mental": ["ansiedade", "depressão", "suicídio", "medo", "pânico", "tristeza"]
}

def calculate_risk(text: str, sentiment: dict) -> dict:
    """
    Calcula risco combinando sentimento Azure + palavras-chave locais
    """
    text_lower = text.lower()
    risco_violencia = "baixo"
    risco_saude_mental = "baixo"

    # Conta ocorrências de palavras de risco
    violencia_count = sum(1 for word in RISK_KEYWORDS["violencia"] if word in text_lower)
    saude_count = sum(1 for word in RISK_KEYWORDS["saude_mental"] if word in text_lower)

    # Combina com sentimento
    if sentiment["sentiment"] == "negative":
        if violencia_count >= 2:
            risco_violencia = "alto"
        elif violencia_count == 1:
            risco_violencia = "medio"

        if saude_count >= 2:
            risco_saude_mental = "alto"
        elif saude_count == 1:
            risco_saude_mental = "medio"

    return {
        "risco_violencia": risco_violencia,
        "risco_saude_mental": risco_saude_mental,
        "violencia_keywords_found": violencia_count,
        "saude_keywords_found": saude_count
    }
```

### Cache em Memória
```python
from datetime import datetime, timedelta
from typing import Optional, Dict

class AnalysisCache:
    """Cache em memória para resultados de análise"""

    def __init__(self, ttl_minutes: int = 60):
        self._cache: Dict[str, dict] = {}
        self._timestamps: Dict[str, datetime] = {}
        self._ttl = timedelta(minutes=ttl_minutes)

    def get(self, key: str) -> Optional[dict]:
        """Retorna resultado do cache se válido"""
        if key in self._cache:
            if datetime.now() - self._timestamps[key] < self._ttl:
                return self._cache[key]
            else:
                # Expirado, remove
                del self._cache[key]
                del self._timestamps[key]
        return None

    def set(self, key: str, value: dict):
        """Armazena resultado no cache"""
        self._cache[key] = value
        self._timestamps[key] = datetime.now()

    def clear_expired(self):
        """Limpa entradas expiradas"""
        now = datetime.now()
        expired = [
            k for k, ts in self._timestamps.items()
            if now - ts >= self._ttl
        ]
        for k in expired:
            del self._cache[k]
            del self._timestamps[k]
```

---

## Melhores Práticas de Implementação

### Padrão Singleton para Cliente Azure

```python
from azure.ai.textanalytics import TextAnalyticsClient
from azure.core.credentials import AzureKeyCredential
from functools import lru_cache

@lru_cache()
def get_text_analytics_client():
    """Cliente singleton para Azure Text Analytics"""
    return TextAnalyticsClient(
        endpoint=settings.azure_text_endpoint,
        credential=AzureKeyCredential(settings.azure_text_key)
    )

# Ou usando lifespan (FastAPI moderno)
from contextlib import asynccontextmanager

@asynccontextmanager
async def lifespan(app: FastAPI):
    app.state.azure_text_client = TextAnalyticsClient(...)
    yield
    await app.state.azure_text_client.close()

app = FastAPI(lifespan=lifespan)
```

### Retry Policy

```python
from azure.core.pipeline.policies import RetryPolicy

retry_policy = RetryPolicy(
    retry_total=3,
    retry_connect=3,
    retry_read=3,
    retry_status=3,
    backoff_factor=0.3,
    status_forcelist=[500, 502, 503, 504]
)

client = TextAnalyticsClient(
    endpoint=settings.azure_text_endpoint,
    credential=AzureKeyCredential(settings.azure_text_key),
    retry_policy=retry_policy
)
```

### Tratamento de Erros Azure

```python
from azure.core.exceptions import HttpResponseError, ServiceRequestError

async def safe_azure_call(func, *args, **kwargs):
    """Wrapper seguro para chamadas Azure"""
    try:
        return await func(*args, **kwargs)
    except HttpResponseError as e:
        if e.status_code == 429:
            raise QuotaExceededError("Azure quota exceeded")
        elif e.status_code == 401:
            raise AuthenticationError("Invalid Azure credentials")
        else:
            raise AzureServiceError(f"Azure service error: {e.message}")
    except ServiceRequestError as e:
        raise AzureConnectionError("Cannot connect to Azure service")
```

### Sanitização de Input

```python
import unicodedata
import re

def sanitize_text_input(text: str) -> str:
    """Sanitiza texto antes de enviar ao Azure"""
    # 1. Normalizar Unicode
    text = unicodedata.normalize('NFKC', text)

    # 2. Remover zero-width characters (steganography)
    zero_width = '\u200B\u200C\u200D\u2060\uFEFF'
    for char in zero_width:
        text = text.replace(char, '')

    # 3. Remover control characters
    text = re.sub(r'[\x00-\x08\x0B\x0C\x0E-\x1F\x7F-\x9F]', '', text)

    # 4. Limitar sequências repetidas (prevenir DoS)
    text = re.sub(r'(.)\1{10,}', r'\1', text)  # Max 10 repetições

    return text.strip()
```

### Injeção de Dependências FastAPI

```python
from fastapi import Depends

async def get_azure_text_client():
    return TextAnalyticsClient()

@app.post("/analyze/text")
async def analyze_text(
    request: TextRequest,
    client: TextAnalyticsClient = Depends(get_azure_text_client)
):
    result = await client.analyze(request.texto)
    return result
```

---

## Clarifications

### Session 2026-04-11

- **Q1**: Como determinar risco_violencia/risco_saude_mental apenas com sentimento do Azure?
  - **A**: Combinar sentimento do Azure + detecção local de palavras-chave indicativas de risco
- **Q2**: Qual estratégia de cache usar?
  - **A**: Cache em memória (dict) com TTL 1h, cachear resultado completo
- **Q3**: De onde vem as palavras-chave para detecção de risco?
  - **A**: Palavras pré-definidas em arquivo de configuração (violência, agressão, medo, ansiedade, depressão, suicídio)

---

## Referências

- Documentação completa: `docs/technical/context7-best-practices.md`
- [Azure AI Language](https://learn.microsoft.com/azure/ai-services/language-service/)
- [Azure Text Analytics SDK Python](https://learn.microsoft.com/python/api/azure-ai-textanalytics/)
