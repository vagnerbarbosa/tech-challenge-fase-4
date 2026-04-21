# Research: Análise de Vídeo com YOLOv8

**Date**: 2026-04-19  
**Feature**: Análise de Vídeo para Detecção de Riscos Visuais

---

## Decisões Técnicas Consolidadas

### 1. Modelo YOLOv8

**Decision**: Usar YOLOv8n (nano) pré-treinado do COCO dataset

**Rationale**:
- ~6MB de tamanho (vs 22MB small, 46MB medium)
- Inferência rápida em CPU (50-100ms por frame)
- Classes COCO cobrem objetos relevantes: `person` (0), `knife` (43), `scissors` (77), etc.
- Sem necessidade de treinamento customizado para MVP

**Alternatives considered**:
- YOLOv8s/m/l: Rejeitados - muito pesados para Azure Free Tier (sem GPU)
- Treinamento customizado: Rejeitado - fora de escopo do MVP, requer dataset médico

---

### 2. Extração de Frames

**Decision**: OpenCV (cv2.VideoCapture) com amostragem adaptativa

**Rationale**:
- Biblioteca já instalada (dependência do projeto)
- Amostragem adaptativa: 1 FPS até 30s, 0.2 FPS (1 frame/5s) para vídeos >30s
- Máximo ~24 frames por vídeo (performance previsível)

**Alternatives considered**:
- FFmpeg direto: Rejeitado - mais complexo, OpenCV já encapsula
- Frame a frame completo: Rejeitado - muito lento para vídeos longos

---

### 3. Detecção de Sangramento

**Decision**: Computer Vision clássico (HSV color thresholding)

**Rationale**:
- COCO não tem classe "blood" ou "bleeding"
- HSV permite detectar vermelho intenso característico
- Simples, rápido, não requer treinamento
- Threshold: >2% pixels vermelhos = sangramento detectado

**Alternatives considered**:
- Modelo customizado: Rejeitado - requer dataset médico anotado
- Azure Vision: Rejeitado - custo, latência adicional

---

### 4. Rate Limiting

**Decision**: Não aplicável (YOLOv8 100% local)

**Rationale**:
- YOLOv8 roda no container, não consome quota Azure
- Única limitação é recursos do container (CPU/memória)
- Azure Vision fallback é post-MVP

---

### 5. Processamento Síncrono vs Assíncrono

**Decision**: Síncrono para MVP (vídeos até 2 minutos)

**Rationale**:
- Amostragem adaptativa limita número de frames
- Vídeo 2min = ~24 frames = processamento rápido (< 10s)
- Async adiciona complexidade (jobs, workers, estado)
- Pode ser adicionado futuramente se necessário

**Alternatives considered**:
- Celery + Redis: Rejeitado - complexidade excessiva para MVP
- AsyncIO puro: Considerado - pode ser usado internamente para processar frames em paralelo

---

### 6. Cache de Resultados

**Decision**: Reutilizar AnalysisCache existente (src/core/cache.py)

**Rationale**:
- Cache já implementado para texto
- Funciona com hash do arquivo (tamanho + mtime + nome)
- TTL configurável (padrão: 60 minutos)
- Evita reprocessar mesmo vídeo

---

### 7. Storage de Arquivos

**Decision**: Local filesystem (/tmp) com cleanup automático

**Rationale**:
- Segue padrão estabelecido pelo áudio
- TempFileManager já implementado (LGPD-compliant)
- Azure Blob é post-MVP/se necessário

---

## Referências Técnicas

### YOLOv8 COCO Classes Relevantes
```python
RELEVANT_CLASSES = {
    0: "person",          # Para detecção de pessoa/postura
    43: "knife",          # Objeto perigoso
    77: "scissors",       # Objeto médico/perigoso
    # Outros objetos podem ser mapeados conforme necessidade
}
```

### OpenCV + YOLOv8 Exemplo
```python
from ultralytics import YOLO
import cv2

model = YOLO("yolov8n.pt")
model.to('cpu')  # Força CPU

# Inference
results = model(frame, verbose=False)
```

### HSV Range para Vermelho (Sangramento)
```python
lower_red1 = np.array([0, 100, 100])
upper_red1 = np.array([10, 255, 255])
lower_red2 = np.array([160, 100, 100])
upper_red2 = np.array([180, 255, 255])
```

---

## Conclusão

Todas as decisões técnicas estão alinhadas com:
1. **Constitution**: LGPD, Container-First, Test Coverage
2. **Azure Free Tier**: 100% processamento local (custo zero)
3. **MVP Scope**: Funcionalidade core sem complexidade desnecessária
4. **Extensibilidade**: Estrutura preparada para fallback Azure Vision post-MVP
