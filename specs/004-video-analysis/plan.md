# Implementation Plan: Análise de Vídeo com YOLOv8

**Branch**: `011-video-analysis-yolov8` | **Date**: 2026-04-19 | **Spec**: [spec.md](spec.md)
**Input**: Feature specification from `/specs/004-video-analysis/spec.md`

**Note**: This template is filled in by the `/speckit.plan` command. See `.specify/templates/plan-template.md` for the execution workflow.

## Summary

Implementar endpoint `/analyze/video` para processamento de vídeos usando YOLOv8 local (custo zero) para detecção de:
1. **Objetos relevantes**: Pessoas, objetos potencialmente perigosos (COCO classes)
2. **Sangramento**: Detector CV clássico baseado em cor HSV
3. **Riscos**: Cálculo de `risco_violencia` e `risco_saude_mental` a partir de detecções

**Abordagem técnica**: 
- YOLOv8n pré-treinado rodando localmente no container (sem custo Azure)
- Extração de frames com OpenCV + amostragem adaptativa (1 FPS ≤30s, 0.2 FPS >30s)
- Integração com infraestrutura existente (cache, rate limiting, LGPD cleanup)

## Technical Context

**Language/Version**: Python 3.11+  
**Primary Dependencies**: 
- FastAPI (framework web)
- Ultralytics YOLOv8 (detecção de objetos)
- OpenCV (extração de frames)
- NumPy (processamento de arrays)
- Azure AI Vision SDK (fallback post-MVP)

**Storage**: Arquivos temporários em `/tmp` (LGPD-compliant com auto-cleanup)  
**Testing**: pytest + pytest-asyncio + httpx  
**Target Platform**: Linux container (Docker) / Azure Container Instances  
**Project Type**: Web service (FastAPI REST API)  
**Performance Goals**: 
- Vídeo 30s processado em < 10 segundos
- YOLOv8n carrega em < 5 segundos
- Suporta 5 análises simultâneas sem degradação

**Constraints**: 
- Azure Free Tier (sem GPU, CPU limitado)
- Limite 50MB por vídeo
- Máximo 2 minutos de duração
- ~24 frames máximo por vídeo (amostragem adaptativa)

**Scale/Scope**: MVP - análise síncrona para todos os vídeos (até 2 min), com amostragem adaptativa para garantir performance

## Constitution Check

*GATE: Must pass before Phase 0 research. Re-check after Phase 1 design.*

| Princípio | Status | Observações |
|-----------|--------|-------------|
| **I. LGPD Compliance** | ✅ PASS | TempFileManager já implementado, cleanup automático |
| **II. Azure Free Tier Protection** | ✅ PASS | YOLOv8 100% local, sem chamadas Azure no MVP |
| **III. Test Coverage >70%** | ⚠️ CHECK | Requer testes para VideoProcessor, YOLOv8Service |
| **IV. Container-First** | ✅ PASS | Dockerfile existente, dependências OpenCV já configuradas |
| **V. Documentação em Português** | ✅ PASS | Spec em português, código segue padrão Python (inglês) |
| **VI. Security-First** | ✅ PASS | Validação de arquivos já implementada (magic numbers) |
| **VII. Multimodal Architecture** | ✅ PASS | Endpoint independente, compatível com fusão futura |

**Gates para prosseguir:**
- ✅ Não adiciona novos serviços externos obrigatórios
- ✅ Não quebra compatibilidade com endpoints existentes
- ✅ Respeita LGPD (arquivos temporários, sem logging de conteúdo)
- ✅ Escopo definido e mensurável

## Project Structure

### Documentation (this feature)

```text
specs/[###-feature]/
├── plan.md              # This file (/speckit.plan command output)
├── research.md          # Phase 0 output (/speckit.plan command)
├── data-model.md        # Phase 1 output (/speckit.plan command)
├── quickstart.md        # Phase 1 output (/speckit.plan command)
├── contracts/           # Phase 1 output (/speckit.plan command)
└── tasks.md             # Phase 2 output (/speckit.tasks command - NOT created by /speckit.plan)
```

### Source Code (repository root)

```text
src/
├── api/
│   └── routes/
│       ├── video.py              # NOVO: Endpoint POST /analyze/video
│       └── ... (routes existentes)
├── models/
│   └── schemas.py                # ADICIONAR: VideoAnalysisRequest, VideoAnalysisResponse
├── services/
│   ├── video_analysis.py         # NOVO: VideoAnalysisService
│   ├── yolo_service.py           # NOVO: YOLOv8Service
│   ├── video_processor.py        # NOVO: VideoProcessor
│   └── bleeding_detector.py      # NOVO: BleedingDetector
├── core/
│   └── ... (existente)
└── utils/
    └── ... (existente)

tests/
├── unit/
│   ├── services/
│   │   ├── test_video_analysis.py      # NOVO
│   │   ├── test_yolo_service.py        # NOVO
│   │   ├── test_video_processor.py     # NOVO
│   │   └── test_bleeding_detector.py   # NOVO
│   └── ... (existentes)
├── integration/
│   └── test_video_endpoint.py    # NOVO
└── ... (existentes)

# Modelo YOLOv8 (baixado no build)
models/
└── yolov8n.pt                    # NOVO: ~6MB, incluído no Dockerfile
```

**Structure Decision**: Single project FastAPI, seguindo padrão estabelecido pelas modalidades de texto e áudio. Cada componente tem seu próprio arquivo e testes correspondentes.

## Complexity Tracking

> **Fill ONLY if Constitution Check has violations that must be justified**

| Violation | Why Needed | Simpler Alternative Rejected Because |
|-----------|------------|-------------------------------------|
| Nenhuma | - | - |

---

## Phase Completion Status

### Phase 0: Research ✅ COMPLETED
**Output**: [research.md](research.md)
- Decisões técnicas consolidadas
- YOLOv8n selecionado como modelo base
- OpenCV definido para extração de frames
- Azure Vision fallback adiado para post-MVP

### Phase 1: Design ✅ COMPLETED
**Outputs**:
- [data-model.md](data-model.md) - Schemas Pydantic definidos
- [contracts/video-endpoint.md](contracts/video-endpoint.md) - Contrato da API
- [quickstart.md](quickstart.md) - Guia de uso rápido

### Phase 2: Tasks (Next)
**Command**: `/speckit.tasks` (gerar tasks.md)
