"""
Mock Server para Azure AI Services
Simula endpoints de Text Analytics, Speech e Vision
Roda servidores nas portas 3001, 3002 e 3003
"""

import multiprocessing
import sys
from typing import Any

from fastapi import FastAPI, File, UploadFile
from fastapi.responses import JSONResponse
from pydantic import BaseModel

# ==========================================
# MODELOS
# ==========================================


class TextAnalysisRequest(BaseModel):
    documents: list[dict[str, Any]]


class SentimentResponse(BaseModel):
    documents: list[dict[str, Any]]


class SpeechToTextResponse(BaseModel):
    DisplayText: str
    Duration: int
    Offset: int


class VisionAnalysisResponse(BaseModel):
    description: dict[str, Any]
    tags: list[dict[str, Any]]
    objects: list[dict[str, Any]]


# ==========================================
# TEXT ANALYTICS (porta 3001)
# ==========================================


def create_text_app():
    """Cria aplicação Text Analytics."""
    app = FastAPI(title="Azure AI Language Mock", port=3001)

    @app.post("/text/analytics/v3.1/sentiment")
    async def analyze_sentiment(request: TextAnalysisRequest):
        """Mock do Azure Text Analytics - Análise de Sentimento."""
        results = []
        for doc in request.documents:
            text = doc.get("text", "").lower()

            # Lógica simples para determinar sentimento
            positive_words = [
                "feliz",
                "ótimo",
                "bem",
                "saudável",
                "tranquila",
                "calma",
                "alegre",
                "contente",
            ]
            negative_words = [
                "ansiosa",
                "triste",
                "mal",
                "medo",
                "deprimida",
                "estresse",
                "ansiedade",
                "violência",
            ]

            pos_count = sum(1 for word in positive_words if word in text)
            neg_count = sum(1 for word in negative_words if word in text)

            if neg_count > pos_count:
                sentiment = "negative"
                confidence = {"negative": 0.85, "neutral": 0.10, "positive": 0.05}
            elif pos_count > neg_count:
                sentiment = "positive"
                confidence = {"positive": 0.85, "neutral": 0.10, "negative": 0.05}
            else:
                sentiment = "neutral"
                confidence = {"neutral": 0.80, "positive": 0.10, "negative": 0.10}

            results.append(
                {
                    "id": doc.get("id", "1"),
                    "sentiment": sentiment,
                    "confidenceScores": confidence,
                    "sentences": [
                        {
                            "sentiment": sentiment,
                            "confidenceScores": confidence,
                            "text": doc.get("text", ""),
                        }
                    ],
                }
            )

        return {"documents": results}

    @app.post("/text/analytics/v3.1/keyPhrases")
    async def extract_key_phrases(request: TextAnalysisRequest):
        """Mock do Azure Text Analytics - Extração de Frases-chave."""
        results = []
        for doc in request.documents:
            text = doc.get("text", "")
            words = text.split()[:5]

            results.append({"id": doc.get("id", "1"), "keyPhrases": words})

        return {"documents": results}

    @app.get("/health")
    async def health_check():
        return {"status": "healthy", "service": "text-analytics-mock", "port": 3001}

    return app


# ==========================================
# SPEECH SERVICES (porta 3002)
# ==========================================


def create_speech_app():
    """Cria aplicação Speech Services."""
    app = FastAPI(title="Azure AI Speech Mock", port=3002)

    @app.post("/speech/v2.0/recognition")
    async def speech_to_text(file: UploadFile = File(...)):
        """Mock do Azure Speech Services - Speech to Text."""
        return JSONResponse(
            content={
                "RecognitionStatus": "Success",
                "DisplayText": "Estou me sentindo um pouco ansiosa ultimamente.",
                "Duration": 3500000,
                "Offset": 100000,
            }
        )

    @app.post("/speech/v2.0/synthesis")
    async def text_to_speech(request: dict[str, Any]):
        """Mock do Azure Speech Services - Text to Speech."""
        return JSONResponse(
            content={
                "status": "synthesis",
                "audioUrl": "http://mock-azure:3002/audio/sample.wav",
            }
        )

    @app.get("/health")
    async def health_check():
        return {"status": "healthy", "service": "speech-services-mock", "port": 3002}

    return app


# ==========================================
# COMPUTER VISION (porta 3003)
# ==========================================


def create_vision_app():
    """Cria aplicação Computer Vision."""
    app = FastAPI(title="Azure AI Vision Mock", port=3003)

    @app.post("/vision/v3.1/analyze")
    async def analyze_image(
        visualFeatures: str = "description,tags,objects", file: UploadFile = File(...)
    ):
        """Mock do Azure Computer Vision - Análise de Imagem."""
        is_sad = file.size % 2 == 0

        if is_sad:
            description = "Pessoa com expressão facial triste"
            tags = [
                {"name": "person", "confidence": 0.95},
                {"name": "sad", "confidence": 0.80},
                {"name": "indoor", "confidence": 0.70},
            ]
        else:
            description = "Pessoa sorrindo"
            tags = [
                {"name": "person", "confidence": 0.95},
                {"name": "smile", "confidence": 0.85},
                {"name": "happy", "confidence": 0.75},
            ]

        return {
            "description": {
                "tags": ["person", "face", "indoor"],
                "captions": [{"text": description, "confidence": 0.85}],
            },
            "tags": tags,
            "objects": [
                {"object": "person", "confidence": 0.92, "parent": {"object": "human"}}
            ],
            "metadata": {"width": 800, "height": 600, "format": "Jpeg"},
        }

    @app.post("/vision/v3.1/describe")
    async def describe_image(file: UploadFile = File(...)):
        """Mock do Azure Computer Vision - Descrição de Imagem."""
        return {
            "description": {
                "captions": [
                    {"text": "Uma pessoa em um ambiente interno", "confidence": 0.82}
                ],
                "tags": ["person", "indoor", "face"],
            },
            "requestId": "mock-request-123",
            "metadata": {"width": 800, "height": 600, "format": "Jpeg"},
        }

    @app.get("/health")
    async def health_check():
        return {"status": "healthy", "service": "vision-mock", "port": 3003}

    return app


# ==========================================
# SERVIDORES
# ==========================================


def run_text_server():
    """Inicia servidor Text Analytics na porta 3001."""
    import uvicorn

    app = create_text_app()
    uvicorn.run(app, host="0.0.0.0", port=3001, log_level="info")


def run_speech_server():
    """Inicia servidor Speech Services na porta 3002."""
    import uvicorn

    app = create_speech_app()
    uvicorn.run(app, host="0.0.0.0", port=3002, log_level="info")


def run_vision_server():
    """Inicia servidor Vision na porta 3003."""
    import uvicorn

    app = create_vision_app()
    uvicorn.run(app, host="0.0.0.0", port=3003, log_level="info")


# ==========================================
# MAIN
# ==========================================

if __name__ == "__main__":
    multiprocessing.set_start_method("spawn")

    # Inicia 3 processos separados para cada serviço
    text_process = multiprocessing.Process(target=run_text_server)
    speech_process = multiprocessing.Process(target=run_speech_server)
    vision_process = multiprocessing.Process(target=run_vision_server)

    text_process.start()
    speech_process.start()
    vision_process.start()

    print("🚀 Mock Azure AI Services iniciado:")
    print("   - Text Analytics: http://localhost:3001")
    print("   - Speech Services: http://localhost:3002")
    print("   - Computer Vision: http://localhost:3003")

    try:
        text_process.join()
        speech_process.join()
        vision_process.join()
    except KeyboardInterrupt:
        print("\n🛑 Encerrando serviços...")
        text_process.terminate()
        speech_process.terminate()
        vision_process.terminate()
        sys.exit(0)
