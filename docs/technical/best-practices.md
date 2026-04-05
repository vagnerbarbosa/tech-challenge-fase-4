# Melhores Práticas de Código - FastAPI + Azure SDK

> Este documento deve ser validado com MCP Context7 para garantir as práticas mais atualizadas

## 1. FastAPI - Melhores Práticas

### 1.1 Estrutura de Dependências

```python
# ✅ Correto: Usar Depends para injeção de dependências
from fastapi import Depends, FastAPI

async def get_azure_text_client():
    return AzureTextAnalyticsClient()

@app.post("/analyze/text")
async def analyze_text(
    request: TextRequest,
    client: AzureTextAnalyticsClient = Depends(get_azure_text_client)
):
    result = await client.analyze(request.texto)
    return result

# ❌ Evitar: Criar cliente dentro da função (custo de inicialização)
@app.post("/analyze/text")
async def analyze_text(request: TextRequest):
    client = AzureTextAnalyticsClient()  # Custo a cada requisição!
    result = await client.analyze(request.texto)
    return result
```

### 1.2 Tratamento de Exceções

```python
# ✅ Correto: Exception handlers globais
from fastapi import FastAPI, HTTPException
from fastapi.responses import JSONResponse

app = FastAPI()

@app.exception_handler(AzureError)
async def azure_exception_handler(request, exc):
    logger.error(f"Azure error: {exc}")
    return JSONResponse(
        status_code=503,
        content={"error": "Serviço Azure temporariamente indisponível"}
    )

@app.exception_handler(QuotaExceededError)
async def quota_exception_handler(request, exc):
    return JSONResponse(
        status_code=429,
        content={"error": "Quota do Azure excedida", "retry_after": 3600}
    )
```

### 1.3 Upload de Arquivos

```python
# ✅ Correto: Limites de tamanho e tipos válidos
from fastapi import UploadFile, File, HTTPException
from typing import Optional

MAX_FILE_SIZE = 50 * 1024 * 1024  # 50MB
ALLOWED_AUDIO_TYPES = {"audio/wav", "audio/mp3", "audio/ogg"}
ALLOWED_IMAGE_TYPES = {"image/jpeg", "image/png"}

@app.post("/analyze/audio")
async def analyze_audio(
    audio: UploadFile = File(..., description="Arquivo de áudio (WAV, MP3, OGG)")
):
    # Validar tipo
    if audio.content_type not in ALLOWED_AUDIO_TYPES:
        raise HTTPException(400, f"Tipo não suportado: {audio.content_type}")

    # Validar tamanho
    content = await audio.read()
    if len(content) > MAX_FILE_SIZE:
        raise HTTPException(400, f"Arquivo muito grande: {len(content)} bytes")

    # Processar...

# ❌ Evitar: Aceitar qualquer arquivo sem validação
@app.post("/analyze/audio")
async def analyze_audio(audio: UploadFile = File(...)):
    content = await audio.read()  # Risco: arquivo gigante!
```

### 1.4 Async/Await Corretamente

```python
# ✅ Correto: Usar async para I/O bound
@app.post("/analyze/text")
async def analyze_text(request: TextRequest):
    # Azure SDK é async-friendly
    result = await azure_client.analyze_text(request.texto)
    return result

# ⚠️ Cuidado: CPU-bound pode bloquear event loop
@app.post("/analyze/complex")
async def analyze_complex(request: ComplexRequest):
    # Se processamento for CPU-intensivo, usar BackgroundTask ou ThreadPool
    result = await run_in_threadpool(cpu_intensive_task, request.data)
    return result
```

### 1.5 Configuração Pydantic

```python
# ✅ Correto: Settings com validação
from pydantic_settings import BaseSettings
from pydantic import validator

class Settings(BaseSettings):
    azure_text_key: str
    azure_text_endpoint: str
    azure_speech_key: str
    azure_speech_region: str = "brazilsouth"

    @validator("azure_text_key", "azure_speech_key")
    def validate_key_not_empty(cls, v):
        if not v or v == "your_key_here":
            raise ValueError("Azure key não configurada")
        return v

    class Config:
        env_file = ".env"

settings = Settings()
```

---

## 2. Azure SDK - Melhores Práticas

### 2.1 Singleton Pattern para Clientes Azure

```python
# ✅ Correto: Clientes como singletons
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
    # Startup: inicializar clientes
    app.state.azure_text_client = TextAnalyticsClient(...)
    app.state.azure_speech_config = SpeechConfig(...)
    yield
    # Shutdown: cleanup
    await app.state.azure_text_client.close()

app = FastAPI(lifespan=lifespan)
```

### 2.2 Retry Policy

```python
# ✅ Correto: Configurar retry policy
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

### 2.3 Rate Limiting e Quota Management

```python
# ✅ Correto: Implementar rate limiting por serviço
import asyncio
from datetime import datetime, timedelta

class AzureQuotaManager:
    def __init__(self):
        self.quotas = {
            "text_analytics": {"daily_limit": 160, "used": 0, "reset_time": None},
            "speech": {"daily_limit": 600, "used": 0, "reset_time": None},  # minutos
            "computer_vision": {"daily_limit": 160, "used": 0, "reset_time": None}
        }

    async def check_and_consume(self, service: str, amount: int = 1):
        quota = self.quotas[service]

        # Reset diário
        if quota["reset_time"] is None or datetime.now() > quota["reset_time"]:
            quota["used"] = 0
            quota["reset_time"] = datetime.now() + timedelta(days=1)

        # Verificar limite
        if quota["used"] + amount > quota["daily_limit"]:
            raise QuotaExceededError(f"Quota {service} excedida")

        quota["used"] += amount
        return True

quota_manager = AzureQuotaManager()

@app.post("/analyze/text")
async def analyze_text(request: TextRequest):
    await quota_manager.check_and_consume("text_analytics")
    result = await azure_client.analyze(request.texto)
    return result
```

### 2.4 Error Handling Azure

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
            logger.error(f"Azure HTTP error: {e}")
            raise AzureServiceError(f"Azure service error: {e.message}")
    except ServiceRequestError as e:
        logger.error(f"Azure connection error: {e}")
        raise AzureConnectionError("Cannot connect to Azure service")
```

### 2.5 Logging de Requisições Azure

```python
import logging

# Habilitar logging do Azure SDK
logging.getLogger("azure").setLevel(logging.WARNING)
logging.getLogger("azure.core.pipeline.policies.http_logging_policy").setLevel(logging.WARNING)

# Logging customizado
logger = logging.getLogger(__name__)

async def analyze_with_logging(client, text):
    logger.info(f"Azure API call: analyze_sentiment, text_length={len(text)}")
    start_time = time.time()

    try:
        result = await client.analyze_sentiment([text])
        duration = time.time() - start_time
        logger.info(f"Azure API success: duration={duration:.2f}s")
        return result
    except Exception as e:
        logger.error(f"Azure API error: {e}")
        raise
```

---

## 3. Multimodal Processing

### 3.0 Processamento de Vídeo (Frame Extraction)

```python
# ✅ Correto: Extrair frames e analisar com Azure Computer Vision
class VideoProcessor:
    def __init__(self, frame_extractor, image_analyzer):
        self.frame_extractor = frame_extractor
        self.image_analyzer = image_analyzer

    async def process_video(self, video_path: Path) -> VideoAnalysisResult:
        # Extrair frames
        frames = await self.frame_extractor.extract_frames(
            video_path,
            interval_seconds=5  # 1 frame a cada 5s
        )

        # Analisar cada frame
        frame_results = []
        for frame_path in frames:
            result = await self.image_analyzer.analyze(frame_path)
            frame_results.append(result)

        # Combinar resultados
        combined = self._combine_frame_results(frame_results)

        # Limpar frames temporários
        for frame_path in frames:
            frame_path.unlink()

        return combined
```

### 3.1 Processamento Paralelo

```python
# ✅ Correto: Processar modalidades em paralelo
import asyncio

@app.post("/analyze/multimodal")
async def analyze_multimodal(
    texto: str = Form(...),
    audio: UploadFile = File(None),
    imagem: UploadFile = File(None)
):
    tasks = []
    results = {"texto": None, "audio": None, "imagem": None}

    if texto:
        tasks.append(text_service.analyze(texto))
    if audio:
        tasks.append(audio_service.analyze(audio))
    if imagem:
        tasks.append(image_service.analyze(imagem))

    # Executar em paralelo
    task_results = await asyncio.gather(*tasks, return_exceptions=True)

    # Combinar resultados
    # ...

    return fusion_service.combine(results)
```

### 3.2 Tempo de Processamento

```python
from time import perf_counter
from contextlib import asynccontextmanager

@asynccontextmanager
async def timed_operation(operation_name: str):
    start = perf_counter()
    try:
        yield
    finally:
        duration = perf_counter() - start
        logger.info(f"Operation {operation_name} took {duration:.2f}s")

# Uso
@app.post("/analyze/audio")
async def analyze_audio(audio: UploadFile):
    async with timed_operation("audio_analysis"):
        result = await audio_service.process(audio)
    return result
```

---

## 4. Segurança e LGPD

### 4.1 Anonimização

```python
import hashlib
import uuid

def generate_patient_id(real_id: str) -> str:
    """Gerar ID anônimo para LGPD"""
    return hashlib.sha256(real_id.encode()).hexdigest()[:16]

def anonymize_text(text: str) -> str:
    """Remover dados identificáveis do texto"""
    # Regex para CPF, telefone, email
    import re
    text = re.sub(r'\d{3}\.\d{3}\.\d{3}-\d{2}', '[CPF]', text)
    text = re.sub(r'\(\d{2}\) \d{4,5}-\d{4}', '[TELEFONE]', text)
    text = re.sub(r'[\w\.-]+@[\w\.-]+\.\w+', '[EMAIL]', text)
    return text
```

### 4.2 Validação de Consentimento

```python
from fastapi import HTTPException, Header

@app.post("/analyze/audio")
async def analyze_audio(
    audio: UploadFile,
    x_consent_id: str = Header(..., description="ID do consentimento LGPD")
):
    if not await validate_consent(x_consent_id):
        raise HTTPException(403, "Consentimento não encontrado ou expirado")

    # Processar...
```

---

## 5. Testes

### 5.1 Mock Azure SDK

```python
import pytest
from unittest.mock import AsyncMock, MagicMock

@pytest.fixture
def mock_azure_text_client():
    client = MagicMock()
    client.analyze_sentiment = AsyncMock(return_value=[
        MagicMock(sentiment="negative", confidence_scores=MagicMock(negative=0.9))
    ])
    return client

async def test_analyze_text(mock_azure_text_client):
    service = TextAnalysisService(client=mock_azure_text_client)
    result = await service.analyze("Estou triste")
    assert result["sentimento"] == "negativo"
```

### 5.2 Testes de Upload

```python
from fastapi.testclient import TestClient
from io import BytesIO

def test_upload_audio(client: TestClient):
    audio_file = BytesIO(b"fake audio data")
    audio_file.name = "test.wav"

    response = client.post(
        "/analyze/audio",
        files={"audio": ("test.wav", audio_file, "audio/wav")}
    )
    assert response.status_code == 200
```

---

## 6. Observabilidade

### 6.1 Métricas Customizadas

```python
from prometheus_client import Counter, Histogram, Gauge

# Métricas
azure_requests_total = Counter(
    "azure_requests_total",
    "Total Azure API requests",
    ["service", "status"]
)

azure_request_duration = Histogram(
    "azure_request_duration_seconds",
    "Azure API request duration",
    ["service"]
)

azure_quota_remaining = Gauge(
    "azure_quota_remaining",
    "Remaining Azure quota",
    ["service"]
)

# Uso
async def analyze_text(text: str):
    with azure_request_duration.labels("text_analytics").time():
        try:
            result = await azure_client.analyze(text)
            azure_requests_total.labels("text_analytics", "success").inc()
            return result
        except Exception:
            azure_requests_total.labels("text_analytics", "error").inc()
            raise
```

---

## 7. Configuração para Context7

Para validar estas práticas com MCP Context7, buscar:

### FastAPI:
- "FastAPI best practices 2024"
- "FastAPI dependency injection patterns"
- "FastAPI file upload validation"
- "FastAPI exception handling"

### Azure SDK Python:
- "Azure SDK Python best practices"
- "Azure Cognitive Services Python SDK"
- "Azure Text Analytics Python examples"
- "Azure Speech Services Python async"
- "Azure Computer Vision Python SDK"

### Padrões:
- "Python async await best practices"
- "Circuit breaker pattern Python"
- "Rate limiting Python FastAPI"
- "Multimodal ML architecture"

---

## Checklist de Validação

Antes de commitar, verificar:

- [ ] Todos os endpoints usam Depends() corretamente
- [ ] Azure clients são singletons/reutilizados
- [ ] Rate limiting implementado para quotas
- [ ] Uploads têm validação de tamanho e tipo
- [ ] Exception handlers configurados
- [ ] Logging estruturado em todos os serviços
- [ ] Testes unitários com mocks para Azure
- [ ] Type hints em todas as funções públicas
- [ ] Anonimização LGPD implementada
- [ ] Retry policy configurado
