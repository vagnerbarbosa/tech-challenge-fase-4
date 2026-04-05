"""
Mock Server para Azure AI Services
Simula endpoints de Text Analytics, Speech e Vision
"""

import random
from datetime import datetime
from typing import Any

from fastapi import FastAPI, HTTPException, UploadFile, File
from fastapi.responses import JSONResponse, FileResponse
from pydantic import BaseModel

app = FastAPI(title="Azure AI Services Mock")


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

@app.post("/text/analytics/v3.1/sentiment")
async def analyze_sentiment(request: TextAnalysisRequest):
    """Mock do Azure Text Analytics - Análise de Sentimento."""

    results = []
    for doc in request.documents:
        text = doc.get("text", "").lower()

        # Lógica simples para determinar sentimento
        positive_words = ["feliz", "ótimo", "bem", "saudável", "tranquila", "calma"]
        negative_words = ["ansiosa", "triste", "mal", "medo", "deprimida", "estresse"]

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

        results.append({
            "id": doc.get("id", "1"),
            "sentiment": sentiment,
            "confidenceScores": confidence,
            "sentences": [{
                "sentiment": sentiment,
                "confidenceScores": confidence,
                "text": doc.get("text", "")
            }]
        })

    return {"documents": results}


@app.post("/text/analytics/v3.1/keyPhrases")
async def extract_key_phrases(request: TextAnalysisRequest):
    """Mock do Azure Text Analytics - Extração de Frases-chave."""

    results = []
    for doc in request.documents:
        text = doc.get("text", "")
        # Extrai palavras simples como keyphrases
        words = text.split()[:5]  # Primeiras 5 palavras

        results.append({
            "id": doc.get("id", "1"),
            "keyPhrases": words
        })

    return {"documents": results}


# ==========================================
# SPEECH SERVICES (porta 3002)
# ==========================================

@app.post("/speech/v2.0/recognition")
async def speech_to_text(file: UploadFile = File(...)):
    """Mock do Azure Speech Services - Speech to Text."""

    # Simula processamento de áudio
    return JSONResponse(content={
        "RecognitionStatus": "Success",
        "DisplayText": "Estou me sentindo um pouco ansiosa ultimamente.",
        "Duration": 3500000,
        "Offset": 100000
    })


@app.post("/speech/v2.0/synthesis")
async def text_to_speech(request: dict[str, Any]):
    """Mock do Azure Speech Services - Text to Speech."""

    # Retorna um arquivo de áudio fake
    return JSONResponse(content={
        "status": "synthesis",
        "audioUrl": "http://mock-azure:3002/audio/sample.wav"
    })


# ==========================================
# COMPUTER VISION (porta 3003)
# ==========================================

@app.post("/vision/v3.1/analyze")
async def analyze_image(
    visualFeatures: str = "description,tags,objects",
    file: UploadFile = File(...)
):
    """Mock do Azure Computer Vision - Análise de Imagem."""

    # Determina se é uma imagem triste ou feliz baseado no tamanho (mock)
    is_sad = file.size % 2 == 0  # Aleatório baseado em paridade

    if is_sad:
        description = "Pessoa com expressão facial triste"
        tags = [
            {"name": "person", "confidence": 0.95},
            {"name": "sad", "confidence": 0.80},
            {"name": "indoor", "confidence": 0.70}
        ]
    else:
        description = "Pessoa sorrindo"
        tags = [
            {"name": "person", "confidence": 0.95},
            {"name": "smile", "confidence": 0.85},
            {"name": "happy", "confidence": 0.75}
        ]

    return {
        "description": {
            "tags": ["person", "face", "indoor"],
            "captions": [
                {
                    "text": description,
                    "confidence": 0.85
                }
            ]
        },
        "tags": tags,
        "objects": [
            {
                "object": "person",
                "confidence": 0.92,
                "parent": {"object": "human"}
            }
        ],
        "metadata": {
            "width": 800,
            "height": 600,
            "format": "Jpeg"
        }
    }


@app.post("/vision/v3.1/describe")
async def describe_image(file: UploadFile = File(...)):
    """Mock do Azure Computer Vision - Descrição de Imagem."""

    return {
        "description": {
            "captions": [
                {
                    "text": "Uma pessoa em um ambiente interno",
                    "confidence": 0.82
                }
            ],
            "tags": ["person", "indoor", "face"]
        },
        "requestId": "mock-request-123",
        "metadata": {
            "width": 800,
            "height": 600,
            "format": "Jpeg"
        }
    }


# ==========================================
# HEALTH CHECK
# ==========================================

@app.get("/health")
async def health_check():
    """Health check do mock server."""
    return {
        "status": "healthy",
        "service": "azure-mock",
        "timestamp": datetime.utcnow().isoformat()
    }


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=3001)
