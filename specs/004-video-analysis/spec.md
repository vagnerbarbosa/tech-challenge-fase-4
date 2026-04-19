# Feature Specification: Análise de Vídeo com YOLOv8

**Feature Branch**: `feature/004-yolo-video-analysis`  
**Created**: 2026-04-12  
**Status**: 📝 Draft  
**Input**: Tech Challenge PDF exige YOLOv8 customizado para análise de vídeo em saúde da mulher

---

## User Scenarios & Testing

### User Story 1 - Detecção de Instrumentos Cirúrgicos (Priority: P1)

Como profissional de saúde, quero que o sistema identifique instrumentos cirúrgicos ginecológicos em vídeos de procedimentos para documentação e análise.

**Why this priority**: Requisito explícito do PDF ("instrumentos cirúrgicos ginecológicos").

**Independent Test**: POST `/analyze/video` retorna detecções de objetos mesmo sem análise de texto/áudio.

**Acceptance Scenarios**:

1. **Given** um vídeo de cirurgia ginecológica, **When** processado pelo YOLOv8, **Then** identifica instrumentos (bisturi, pinça, espéculo, etc.)
2. **Given** vídeo com instrumentos visíveis, **When** analisado, **Then** retorna bounding boxes com confiança > 70%
3. **Given** vídeo sem instrumentos cirúrgicos, **When** processado, **Then** retorna array vazio (sem falsos positivos)
4. **Given** formato de vídeo inválido, **When** submetido, **Then** retorna erro 400 com formatos aceitos

### User Story 2 - Detecção de Sangramento Anômalo (Priority: P1)

Como médico, quero detectar sangramento anômalo durante procedimentos para alertar sobre complicações.

**Why this priority**: Requisito crítico do PDF ("sangramento anômalo durante procedimentos").

**Independent Test**: Detecção de sangramento funciona independentemente de outras análises.

**Acceptance Scenarios**:

1. **Given** vídeo com sangramento visível, **When** analisado, **Then** detecta áreas de sangue com bounding box
2. **Given** sangramento excessivo detectado, **When** confiança > 80%, **Then** gera alerta de risco
3. **Given** sangramento normal/cirurgia, **When** analisado, **Then** não gera falso alerta
4. **Given** mudança de cor na imagem (não sangue), **When** processado, **Then** diferencia de sangramento real

### User Story 3 - Análise de Linguagem Corporal (Priority: P1)

Como profissional de saúde, quero identificar sinais não-verbais de desconforto ou medo em consultas para triagem de violência.

**Why this priority**: Requisito do PDF ("sinais não-verbais de desconforto ou medo", "triagem de violência").

**Independent Test**: Detecção de postura/linguagem corporal funciona isoladamente.

**Acceptance Scenarios**:

1. **Given** vídeo de consulta com paciente tensa, **When** analisado, **Then** detecta postura rígida/protetora
2. **Given** gestos de defesa/fechamento, **When** visíveis no vídeo, **Then** identifica como possível desconforto
3. **Given** expressões faciais de medo/ansiedade, **When** detectadas, **Then** combina com análise de texto se disponível
4. **Given** movimentos normais de consulta, **When** analisados, **Then** não gera falsos positivos

### User Story 4 - Triagem de Violência e Saúde Mental (Priority: P1)

Como profissional de saúde, quero que o sistema identifique sinais visuais de risco em consultas de telemedicina para triagem precoce de violência doméstica e problemas de saúde mental.

**Why this priority**: Requisito do projeto para identificação precoce de riscos em saúde materna e ginecológica, complementando as análises de texto e áudio.

**Independent Test**: POST `/analyze/video` retorna campos `risco_violencia` e `risco_saude_mental` mesmo quando outros riscos não são detectados.

**Acceptance Scenarios**:

1. **Given** um vídeo de consulta médica em formato MP4, **When** o profissional faz upload via API, **Then** o sistema processa o vídeo e retorna análise com objetos detectados e nível de risco avaliado
2. **Given** um vídeo contendo sinais visuais de agitação (movimentos rápidos), **When** processado pelo sistema, **Then** o sistema identifica alto nível de agitação e reporta como possível indicador de ansiedade
3. **Given** vídeo com objetos potencialmente perigosos visíveis (facas, tesouras), **When** analisado pelo YOLOv8, **Then** o sistema lista os objetos detectados com nível de confiança e alerta de risco
4. **Given** um vídeo sem conteúdo relevante, **When** processado, **Then** o sistema retorna "nenhum sinal detectado" sem erro, mantendo os campos obrigatórios de risco preenchidos

---

### User Story 5 - Integração com Azure Vision (Priority: P3 - Post-MVP)

Como sistema, quero usar Azure Vision como fallback quando YOLOv8 não tem certeza, garantindo análise robusta.

**Why this priority**: Implementação futura - YOLOv8 COCO já cobre casos principais. Fallback útil apenas se precisão insuficiente em produção.

**Status**: Não implementar no MVP. Avaliar necessidade após testes em produção com YOLOv8 local.

**Acceptance Scenarios** (para implementação futura):

1. **Given** YOLOv8 confiança < 50%, **When** processa imagem, **Then** chama Azure Vision automaticamente
2. **Given** Azure Vision indisponível, **When** YOLOv8 não detecta, **Then** retorna resultado parcial (sem erro)
3. **Given** ambos disponíveis, **When** analisam mesmo vídeo, **Then** combina resultados com ponderação por confiança

---

### Edge Cases

- **Vídeo corrompido ou formato inválido**: Sistema deve retornar erro 400 com mensagem clara sobre formatos aceitos (MP4, AVI, MOV)
- **Vídeo muito longo (> 2 minutos)**: Sistema deve rejeitar com erro 400 (limite de duração excedido)
- **Resolução muito baixa**: Sistema deve informar que a qualidade pode afetar a precisão da detecção
- **Ausência de pessoas no vídeo**: Sistema deve retornar "nenhuma pessoa detectada" sem erro, mantendo campos obrigatórios preenchidos
- **Múltiplas pessoas no vídeo**: Sistema deve focar na pessoa principal (maior área) ou analisar todas
- **Falha no modelo YOLOv8**: Sistema deve fallback para modo de análise simplificada ou retornar erro apropriado
- **Vídeo excede limite de tamanho (50MB)**: Sistema deve retornar erro 413 (Payload Too Large) antes de iniciar processamento
- **Timeout no processamento**: Sistema deve cancelar processamento após limite configurável e retornar erro 504
- **Falha na extração de frames**: Sistema deve tentar formatos alternativos ou retornar erro específico sobre codificação de vídeo não suportada

---

## Requirements

### Functional Requirements

- **FR-001**: Endpoint POST `/analyze/video` disponível (multipart/form-data)
- **FR-002**: Suporta vídeos MP4, AVI, MOV (máx 2 minutos, max 50MB) - amostragem adaptativa: 1 FPS até 30s, 0.2 FPS (1 frame/5s) para vídeos mais longos
- **FR-003**: Extrai frames com amostragem adaptativa por padrão (1 FPS ≤30s, 0.2 FPS >30s), permitindo override via parâmetro `extract_fps` (0.2-5.0)
- **FR-004**: YOLOv8 roda localmente em container (custo zero)
- **FR-005**: Detecta classes configuráveis: instrumentos_cirurgicos, sangramento, desconforto_postura
- **FR-006**: Retorna bounding boxes com coordenadas (x, y, width, height) e confiança
- **FR-007**: [POST-MVP] Integração opcional com Azure Vision como fallback (consome quota)
- **FR-008**: Gera alerta quando risco detectado (violência, sangramento excessivo)
- **FR-009**: Campos obrigatórios risco_violencia e risco_saude_mental em todas respostas
- **FR-010**: Cache de resultados de análise (não frames) para evitar reprocessamento do mesmo vídeo

### Key Entities

- **VideoAnalysisRequest**: { video: UploadFile, tipo: str, patient_id: str, extract_fps: int }
- **VideoAnalysisResponse**: { 
    detecoes: list[Detection],
    risco_violencia: str,
    risco_saude_mental: str,
    alertas: list[Alert],
    metadata: VideoMetadata
  }
- **Detection**: { classe: str, confianca: float, bbox: {x, y, w, h}, frame: int, timestamp: float }
- **Alert**: { tipo: str, severidade: str, descricao: str, frame_referencia: int }
- **YOLOv8Service**: Lógica de inferência local YOLOv8
- **VideoProcessor**: Extração de frames e pré-processamento

---

## Success Criteria

- **SC-001**: YOLOv8 modelo carrega em < 5 segundos no container
- **SC-002**: Processamento de vídeo 30s em < 10 segundos (local)
- **SC-003**: Precisão detecção instrumentos > 75% (threshold aceitável)
- **SC-004**: Falsos positivos sangramento < 15%
- **SC-005**: Campos obrigatórios sempre presentes
- **SC-006**: Zero custo Azure para análise de vídeo (sem fallback no MVP)

---

## Assumptions

- YOLOv8n (nano) é suficiente para MVP (rápido, leve, menos preciso que medium/large)
- Modelo pré-treinado COCO pode ser fine-tuned para instrumentos médicos específicos (post-MVP)
- CPU do container suporta inference YOLOv8n (sem GPU necessária para MVP)
- Azure Vision é fallback **post-MVP** (não implementado no MVP - 100% YOLOv8 local)
- Vídeos são processados com amostragem adaptativa: até 2 minutos, com 1 FPS para ≤30s e 0.2 FPS para vídeos mais longos
- Limite de arquivo: 50MB (igual ao áudio) para consistência entre modalidades

---

## Technical Notes

### YOLOv8 Setup (Local, Custo Zero)

```dockerfile
# Dockerfile (adição ao runtime)
RUN pip install ultralytics opencv-python-headless

# Download modelo YOLOv8n (nano) - ~6MB, rápido em CPU
RUN mkdir -p /app/models && \
    wget https://github.com/ultralytics/assets/releases/download/v8.3.0/yolov8n.pt \
    -O /app/models/yolov8n.pt

# OU usar modelo customizado se fine-tuned:
# COPY models/yolov8-custom-ginecologia.pt /app/models/
```

```python
# src/services/yolo_service.py
from ultralytics import YOLO
import cv2
import numpy as np
from pathlib import Path

class YOLOv8Service:
    """Serviço de detecção de objetos com YOLOv8 local"""
    
    def __init__(self, model_path: str = "/app/models/yolov8n.pt"):
        self.model = YOLO(model_path)
        self.model.to('cpu')  # Força CPU (Azure Free Tier = sem GPU)
        
        # Classes relevantes para saúde da mulher
        self.relevant_classes = {
            0: "person",           # Para detecção de postura/paciente
            77: "scissors",        # Tesoura cirúrgica (aprox COCO)
            # Mapear mais classes ou usar modelo customizado
        }
    
    def detect(self, image: np.ndarray, conf_threshold: float = 0.5) -> list[dict]:
        """
        Executa detecção em imagem/frame
        Retorna lista de detecções com classe, confiança e bbox
        """
        results = self.model(image, verbose=False)
        detections = []
        
        for result in results:
            boxes = result.boxes
            for box in boxes:
                conf = float(box.conf[0])
                if conf >= conf_threshold:
                    cls_id = int(box.cls[0])
                    x1, y1, x2, y2 = box.xyxy[0].tolist()
                    
                    detections.append({
                        "classe": self.model.names[cls_id],
                        "confianca": round(conf, 3),
                        "bbox": {
                            "x": round(x1, 2),
                            "y": round(y1, 2),
                            "w": round(x2 - x1, 2),
                            "h": round(y2 - y1, 2)
                        }
                    })
        
        return detections
```

### Extração de Frames

```python
# src/services/video_processor.py
import cv2
from pathlib import Path
import tempfile
import shutil

class VideoProcessor:
    """Processa vídeos extraindo frames para análise"""
    
    def __init__(self, extract_fps: int = 1):
        self.extract_fps = extract_fps  # Frames por segundo analisados
    
    def extract_frames(self, video_path: Path, output_dir: Path) -> list[dict]:
        """
        Extrai frames do vídeo para processamento
        Retorna lista de metadados dos frames
        """
        cap = cv2.VideoCapture(str(video_path))
        fps = cap.get(cv2.CAP_PROP_FPS)
        frame_interval = int(fps / self.extract_fps)
        
        frames = []
        frame_count = 0
        saved_count = 0
        
        while True:
            ret, frame = cap.read()
            if not ret:
                break
            
            # Salva frame apenas no intervalo configurado
            if frame_count % frame_interval == 0:
                timestamp = frame_count / fps
                frame_path = output_dir / f"frame_{saved_count:04d}.jpg"
                cv2.imwrite(str(frame_path), frame)
                
                frames.append({
                    "frame_number": saved_count,
                    "timestamp": round(timestamp, 2),
                    "path": frame_path
                })
                saved_count += 1
            
            frame_count += 1
        
        cap.release()
        return frames
```

### Detecção de Sangramento (Custom)

```python
# src/services/bleeding_detector.py
import cv2
import numpy as np

class BleedingDetector:
    """Detector especializado para sangramento anômalo"""
    
    def detect(self, image: np.ndarray) -> dict:
        """
        Detecta áreas de sangramento baseado em cor vermelha intensa
        Não usa ML - detecção por threshold de cor (CV clássico)
        """
        # Converte para HSV (melhor para detectar cor)
        hsv = cv2.cvtColor(image, cv2.COLOR_BGR2HSV)
        
        # Define range de vermelho em HSV
        lower_red1 = np.array([0, 100, 100])
        upper_red1 = np.array([10, 255, 255])
        lower_red2 = np.array([160, 100, 100])
        upper_red2 = np.array([180, 255, 255])
        
        # Cria máscara para vermelho
        mask1 = cv2.inRange(hsv, lower_red1, upper_red1)
        mask2 = cv2.inRange(hsv, lower_red2, upper_red2)
        red_mask = cv2.bitwise_or(mask1, mask2)
        
        # Calcula percentual de pixels vermelhos
        red_pixels = cv2.countNonZero(red_mask)
        total_pixels = image.shape[0] * image.shape[1]
        red_percentage = (red_pixels / total_pixels) * 100
        
        # Threshold para considerar sangramento
        is_bleeding = red_percentage > 2.0  # > 2% da imagem
        
        return {
            "detectado": is_bleeding,
            "confianca": min(red_percentage / 5.0, 1.0),  # Normaliza para 0-1
            "percentual_vermelho": round(red_percentage, 2),
            "bbox": self._find_bounding_box(red_mask) if is_bleeding else None
        }
    
    def _find_bounding_box(self, mask: np.ndarray) -> dict:
        """Encontra bounding box da área vermelha"""
        contours, _ = cv2.findContours(mask, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
        if contours:
            largest = max(contours, key=cv2.contourArea)
            x, y, w, h = cv2.boundingRect(largest)
            return {"x": x, "y": y, "w": w, "h": h}
        return None
```

### Cálculo de Risco a partir de Detecções

```python
# src/services/risk_calculator_video.py
def calculate_video_risk(detections: list[dict]) -> dict:
    """
    Calcula risco baseado nas detecções do vídeo
    Retorna risco_violencia e risco_saude_mental
    """
    risco_violencia = "baixo"
    risco_saude_mental = "baixo"
    alertas = []
    
    # Análise de detecções
    sangramento_detectado = False
    desconforto_detectado = False
    
    for det in detections:
        classe = det["classe"].lower()
        confianca = det["confianca"]
        
        # Sangramento excessivo = risco saúde alto
        if "sangue" in classe or "bleeding" in classe:
            if confianca > 0.8:
                risco_saude_mental = "alto"
                alertas.append({
                    "tipo": "sangramento_excessivo",
                    "severidade": "alta",
                    "descricao": "Sangramento anômalo detectado",
                    "frame_referencia": det.get("frame", 0)
                })
            elif confianca > 0.5:
                risco_saude_mental = "medio"
        
        # Postura defensiva/desconforto = possível violência
        if any(term in classe for term in ["postura_defensiva", "fechada", "tensa"]):
            if confianca > 0.7:
                risco_violencia = "alto"
                desconforto_detectado = True
                alertas.append({
                    "tipo": "comportamento_anomalo",
                    "severidade": "media",
                    "descricao": "Sinais de desconforto ou medo detectados",
                    "frame_referencia": det.get("frame", 0)
                })
    
    return {
        "risco_violencia": risco_violencia,
        "risco_saude_mental": risco_saude_mental,
        "alertas": alertas
    }
```

### Endpoint FastAPI

```python
# src/api/routes/video.py
from fastapi import APIRouter, UploadFile, File, HTTPException
from fastapi.responses import JSONResponse
import tempfile
from pathlib import Path
import shutil

router = APIRouter(prefix="/analyze", tags=["Video Analysis"])

@router.post("/video")
async def analyze_video(
    video: UploadFile = File(...),
    tipo: str = "consulta",
    patient_id: str = None,
    extract_fps: int = 1  # Frames por segundo analisados
):
    """
    Analisa vídeo usando YOLOv8 local (custo zero)
    Fallback opcional para Azure Vision
    """
    # Validações
    if not video.content_type.startswith("video/"):
        raise HTTPException(400, "Arquivo deve ser um vídeo (MP4, AVI, MOV)")
    
    # Salva vídeo temporariamente
    temp_dir = Path(tempfile.mkdtemp())
    video_path = temp_dir / "input.mp4"
    
    try:
        # Salva arquivo
        with open(video_path, "wb") as f:
            shutil.copyfileobj(video.file, f)
        
        # Extrai frames
        processor = VideoProcessor(extract_fps=extract_fps)
        frames = processor.extract_frames(video_path, temp_dir / "frames")
        
        # Processa com YOLOv8
        yolo_service = YOLOv8Service()
        all_detections = []
        
        for frame_info in frames:
            frame = cv2.imread(str(frame_info["path"]))
            
            # YOLOv8 detecção
            detections = yolo_service.detect(frame, conf_threshold=0.5)
            
            # Adiciona metadados do frame
            for det in detections:
                det["frame"] = frame_info["frame_number"]
                det["timestamp"] = frame_info["timestamp"]
            
            all_detections.extend(detections)
        
        # Detecta sangramento (CV clássico)
        bleeding_detector = BleedingDetector()
        for frame_info in frames[:5]:  # Analisa primeiros 5 frames para sangramento
            frame = cv2.imread(str(frame_info["path"]))
            bleeding = bleeding_detector.detect(frame)
            if bleeding["detectado"]:
                all_detections.append({
                    "classe": "sangramento",
                    "confianca": bleeding["confianca"],
                    "bbox": bleeding["bbox"],
                    "frame": frame_info["frame_number"],
                    "timestamp": frame_info["timestamp"]
                })
        
        # Calcula risco
        risk = calculate_video_risk(all_detections)
        
        return {
            "detecoes": all_detections,
            "risco_violencia": risk["risco_violencia"],
            "risco_saude_mental": risk["risco_saude_mental"],
            "alertas": risk["alertas"],
            "metadata": {
                "frames_analisados": len(frames),
                "duracao_video": frames[-1]["timestamp"] if frames else 0,
                "modelo": "yolov8n",
                "local_processing": True  # Indica que foi processado local (custo zero)
            }
        }
        
    finally:
        # Limpa arquivos temporários (LGPD)
        shutil.rmtree(temp_dir, ignore_errors=True)
```

### Azure Vision Fallback (Opcional)

```python
# src/services/azure_vision_fallback.py
from azure.ai.vision.imageanalysis import ImageAnalysisClient
from azure.core.credentials import AzureKeyCredential

class AzureVisionFallback:
    """Fallback para Azure Vision quando YOLOv8 não confia"""
    
    def __init__(self):
        self.client = ImageAnalysisClient(
            endpoint=settings.azure_vision_endpoint,
            credential=AzureKeyCredential(settings.azure_vision_key)
        )
    
    async def analyze_if_needed(self, frame: np.ndarray, yolo_detections: list) -> list:
        """
        Chama Azure Vision apenas se YOLOv8 confiança < threshold
        """
        low_confidence = all(d["confianca"] < 0.5 for d in yolo_detections)
        
        if not low_confidence:
            return yolo_detections  # YOLOv8 bom o suficiente
        
        # Fallback para Azure (consome quota!)
        try:
            result = self.client.analyze(
                image_data=frame,
                visual_features=["objects"]
            )
            
            # Converte resultado Azure para formato YOLO
            azure_detections = []
            for obj in result.objects:
                azure_detections.append({
                    "classe": obj.name,
                    "confianca": obj.confidence,
                    "bbox": {
                        "x": obj.bounding_box.x,
                        "y": obj.bounding_box.y,
                        "w": obj.bounding_box.w,
                        "h": obj.bounding_box.h
                    },
                    "fonte": "azure_vision"  # Indica que veio do Azure
                })
            
            return azure_detections
            
        except Exception as e:
            # Se Azure falhar, retorna o que YOLOv8 achou mesmo com baixa confiança
            return yolo_detections
```

---

## Melhores Práticas

### Performance em CPU

```python
# Otimizações para rodar em CPU (Azure Free Tier = sem GPU)

# 1. Use modelo nano (menor, mais rápido)
model = YOLO("yolov8n.pt")  # ~6MB vs 22MB (s) vs 46MB (m) vs 83MB (l)

# 2. Reduz resolução de entrada
model.predict(frame, imgsz=320)  # Menor que padrão 640 = mais rápido

# 3. Limita FPS de análise
extract_fps = 1  # 1 frame por segundo é suficiente para MVP

# 4. Batch processing se múltiplos frames
results = model([frame1, frame2, frame3], verbose=False)  # Batch
```

### Containerização

```dockerfile
# Dockerfile otimizado para YOLOv8
FROM python:3.11-slim as yolo-runtime

# Instala dependências de sistema
RUN apt-get update && apt-get install -y \
    libgl1 \
    libglib2.0-0 \
    libsm6 \
    libxext6 \
    && rm -rf /var/lib/apt/lists/*

# Instala Python deps
RUN pip install ultralytics opencv-python-headless

# Download modelo (cache eficiente)
RUN mkdir -p /app/models && \
    python -c "from ultralytics import YOLO; YOLO('yolov8n.pt')" && \
    mv /root/.cache/ultralytics/* /app/models/ || true

# Volume para modelos customizados
VOLUME ["/app/models"]

# Usuário não-root
RUN useradd -m -u 1000 appuser && chown -R appuser:appuser /app
USER appuser
```

### Cache de Frames

```python
from functools import lru_cache
import hashlib

class FrameCache:
    """Cache de frames já processados (evita reprocessar mesmo vídeo)"""
    
    def __init__(self, ttl_minutes: int = 60):
        self.cache = {}
        self.ttl = timedelta(minutes=ttl_minutes)
    
    def _get_key(self, video_path: Path) -> str:
        """Gera key baseada no hash do arquivo"""
        stats = video_path.stat()
        content = f"{video_path.name}:{stats.st_size}:{stats.st_mtime}"
        return hashlib.sha256(content.encode()).hexdigest()[:16]
    
    def get(self, video_path: Path) -> list | None:
        key = self._get_key(video_path)
        if key in self.cache:
            entry = self.cache[key]
            if datetime.now() - entry["timestamp"] < self.ttl:
                return entry["result"]
        return None
    
    def set(self, video_path: Path, result: list):
        key = self._get_key(video_path)
        self.cache[key] = {
            "result": result,
            "timestamp": datetime.now()
        }
```

---

## Clarifications

### Session 2026-04-19

- **Q**: Qual deve ser o limite oficial de tamanho de arquivo para vídeos? → **A**: 50MB (igual ao áudio) - mantém consistência entre modalidades
- **Q**: Implementar Azure Vision fallback no MVP? → **A**: Não - foco no YOLOv8 local (custo zero), fallback avaliado post-MVP se necessário
- **Q**: Como tratar vídeos que excedem o limite de processamento? → **A**: Aceitar até 2 minutos com amostragem adaptativa (1 FPS até 30s, 0.2 FPS depois)
- **Q**: FPS é adaptativo ou configurável? → **A**: Adaptativo por padrão, mas usuário pode sobrescrever via `extract_fps`
- **Q**: Cache de frames ou resultados? → **A**: Cache de resultados (VideoAnalysisResponse), não frames (LGPD)
- **Q**: Processamento async no MVP? → **A**: Não - todos os vídeos são síncronos, async é post-MVP
- **Q**: Dependência ultralytics adicionada? → **A**: Sim, ultralytics>=8.0.0 adicionado ao pyproject.toml

### Session 2026-04-12

- **Q1**: YOLOv8 precisa ser treinado do zero ou pode usar modelo pré-treinado?  
  - **A**: Usar YOLOv8n pré-treinado do COCO como baseline. Fine-tuning opcional se tivermos dataset de instrumentos médicos.

- **Q2**: Como detectar "sangramento anômalo" se COCO não tem essa classe?  
  - **A**: Implementar detector baseado em cor (CV clássico) como primeira versão. Não depende de ML treinado.

- **Q3**: Qual a estratégia para não exceder Free Tier com Azure fallback?  
  - **A**: YOLOv8 processa 100% local (custo zero). Azure Vision só é chamado se confiança YOLO < 50% e quota disponível.

- **Q4**: Como integrar com fusão multimodal depois?  
  - **A**: Endpoint `/analyze/video` retorna estrutura compatível. Fusão multimodal (spec 005) combina resultados texto + áudio + vídeo.

- **Q5**: Como funciona YOLOv8 no deploy Azure?
  - **A**: YOLOv8 roda dentro do container Docker na Azure (Container Instances ou App Service). Usa CPU do container (não consome quota Azure AI). Modelo yolov8n.pt (~6MB) é incluído no build.

---

## Deploy Azure

### Arquitetura na Azure

```
┌─────────────────────────────────────────────┐
│     Azure Container Instances /             │
│     Azure App Service (Free Tier F1)        │
│                                             │
│  ┌─────────────────────────────────────┐   │
│  │         Container Docker           │   │
│  │                                     │   │
│  │  ┌─────────────────────────────┐  │   │
│  │  │      FastAPI App             │  │   │
│  │  │                             │  │   │
│  │  │  ┌─────────────────────┐   │  │   │
│  │  │  │   YOLOv8 Local      │   │  │   │  ← CPU do container
│  │  │  │   (Custo Zero)      │   │  │   │
│  │  │  └─────────────────────┘   │  │   │
│  │  │                             │  │   │
│  │  │  ┌─────────────────────┐   │  │   │
│  │  │  │  Azure Vision       │   │  │   │  ← Fallback (quota)
│  │  │  │  (Opcional)         │   │  │   │
│  │  │  └─────────────────────┘   │  │   │
│  │  └─────────────────────────────┘  │   │
│  └─────────────────────────────────────┘   │
└─────────────────────────────────────────────┘
```

### Custos na Azure Free Tier

| Recurso | Azure Free Tier | YOLOv8 Custo |
|---------|-----------------|--------------|
| **Container Instances** | 10 instâncias/mês gratuito | Incluído |
| **YOLOv8 inference** | - | **R$ 0,00** (CPU local) |
| **Azure AI Vision** | 5,000 transactions/mês | Só fallback |

### Configuração Dockerfile para Azure

```dockerfile
# Dockerfile otimizado para Azure
FROM python:3.11-slim as runtime

# Dependências de sistema
RUN apt-get update && apt-get install -y --no-install-recommends \
    libgl1 \
    libglib2.0-0 \
    && rm -rf /var/lib/apt/lists/*

# Instala Python packages
RUN pip install --no-cache-dir \
    fastapi \
    uvicorn \
    ultralytics \
    opencv-python-headless \
    azure-ai-vision-imageanalysis

# Download YOLOv8n modelo (incluído no container)
RUN python -c "from ultralytics import YOLO; YOLO('yolov8n.pt')"

# Copia aplicação
COPY src/ ./src/

EXPOSE 8000

# Health check para Azure
HEALTHCHECK --interval=30s --timeout=10s \
    CMD python -c "import urllib.request; urllib.request.urlopen('http://localhost:8000/health')" || exit 1

CMD ["uvicorn", "src.api.main:app", "--host", "0.0.0.0", "--port", "8000"]
```

### Performance no Azure Free Tier

**Azure Container Instances (Free):**
- 1 vCPU / 2 GB RAM
- YOLOv8n inference: ~50-100ms por frame
- Vídeo 30s (30 frames): ~3-5 segundos

**Azure App Service F1 (Free):**
- 1 GB RAM
- 60 minutos CPU/dia
- Suficiente para YOLOv8n (leve)

> **Nota**: Se o container ficar lento, aumentar para S1 (Shared) ou usar Azure Container Instances com mais CPU.

### Vantagens na Azure

1. **Custo previsível** - Paga só infraestrutura, não varia com uso de vídeo
2. **Rápido** - Sem latência de rede para AI Services
3. **Escalável** - Mais containers = mais capacidade
4. **Resiliente** - Funciona mesmo se Azure Vision estiver indisponível

---

## Referências

- [YOLOv8 Documentation](https://docs.ultralytics.com/)
- [YOLOv8 Python Quickstart](https://docs.ultralytics.com/usage/python/)
- [OpenCV HSV Color Space](https://docs.opencv.org/4.x/df/d9d/tutorial_py_colorspaces.html)
- [Azure AI Vision SDK](https://learn.microsoft.com/azure/ai-services/computer-vision/sdk/overview-sdk)
- COCO Dataset Classes: https://github.com/ultralytics/ultralytics/blob/main/ultralytics/cfg/datasets/coco.yaml

---

## Checklist de Implementação

- [x] Especificação consolidada (2026-04-19) - incorporou requisitos de análise comportamental
- [ ] Instalar YOLOv8 no Dockerfile
- [ ] Baixar modelo yolov8n.pt (6MB)
- [ ] Implementar VideoProcessor (extração frames)
- [ ] Implementar YOLOv8Service (inference)
- [ ] Implementar BleedingDetector (CV clássico)
- [ ] Implementar endpoint POST `/analyze/video`
- [ ] Adicionar risco_violencia/risco_saude_mental nas respostas
- [ ] [POST-MVP] Avaliar processamento assíncrono para vídeos longos (>1 min) se necessário
- [ ] Adicionar validação de tamanho de arquivo (50MB, igual ao áudio)
- [ ] Testar com vídeos de exemplo
- [ ] Documentar limitações (COCO genérico vs instrumentos médicos)
- [ ] Criar plano de fine-tuning se necessário (pós-MVP)
