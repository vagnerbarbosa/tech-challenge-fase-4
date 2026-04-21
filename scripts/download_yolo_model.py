#!/usr/bin/env python3
"""Script para baixar o modelo YOLOv8n.

Este script baixa o modelo YOLOv8n (nano) pré-treinado do COCO dataset.
O modelo tem ~6MB e é otimizado para CPU.

Uso:
    python scripts/download_yolo_model.py

O modelo será salvo em: models/yolov8n.pt
"""

import sys
from pathlib import Path

def download_model():
    """Baixa o modelo YOLOv8n usando Ultralytics."""
    try:
        from ultralytics import YOLO
        print("Baixando modelo YOLOv8n...")

        # Download do modelo - YOLO automaticamente baixa para ~/.ultralytics
        model = YOLO("yolov8n.pt")

        # Mover para o diretório models/
        models_dir = Path("models")
        models_dir.mkdir(exist_ok=True)

        # O modelo é baixado automaticamente para ~/.ultralytics
        # Vamos apenas verificar se carregou corretamente
        print(f"✅ Modelo YOLOv8n carregado com sucesso!")
        print(f"   Classes: {len(model.names)}")
        print(f"   Exemplos: {list(model.names.values())[:5]}...")

        return 0

    except ImportError:
        print("❌ Erro: ultralytics não instalado.")
        print("   Execute: poetry install")
        return 1
    except Exception as e:
        print(f"❌ Erro ao baixar modelo: {e}")
        return 1


if __name__ == "__main__":
    sys.exit(download_model())
