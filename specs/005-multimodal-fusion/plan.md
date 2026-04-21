# Implementation Plan: Fusão Multimodal

**Branch**: `005-multimodal-fusion` | **Date**: 2026-04-21 | **Spec**: [spec.md](spec.md)
**Input**: Feature specification from `/specs/005-multimodal-fusion/spec.md`

**Note**: This template is filled in by the `/speckit.plan` command. See `.specify/templates/plan-template.md` for the execution workflow.

## Summary

Implementar endpoint `/analyze/multimodal` para processamento simultâneo de texto, áudio e vídeo, combinando resultados via late fusion ponderado por confiança.

**Abordagem técnica**:
- Reutilizar serviços existentes (TextAnalysisService, AudioAnalysisService, VideoAnalysisService)
- Processamento paralelo com `asyncio.gather()` para otimizar latência
- Late fusion com ponderação por confiança de cada modalidade
- Fallback gracioso: se uma modalidade falhar, as demais continuam
- Timeout de 30s por modalidade

## Technical Context

**Language/Version**: Python 3.11+
**Primary Dependencies**:
- FastAPI (framework web)
- Pydantic v2 (schemas)
- asyncio (processamento paralelo)
- Serviços existentes: TextAnalysisService, AudioAnalysisService, VideoAnalysisService

**Storage**: Arquivos temporários em `/tmp` (LGPD-compliant com auto-cleanup)
**Testing**: pytest + pytest-asyncio + httpx
**Target Platform**: Linux container (Docker) / Azure App Service
**Project Type**: Web service (FastAPI REST API)
**Performance Goals**:
- Latência total < 15s (com 3 modalidades)
- Processamento paralelo: tempo total ≈ max(tempo_individual) + overhead_fusão
- Timeout por modalidade: 30s

**Constraints**:
- Pelo menos uma modalidade deve ser fornecida
- Azure Free Tier para texto e áudio (video é local)
- LGPD: cleanup automático de arquivos temporários

**Scale/Scope**: MVP - endpoint síncrono que orquestra serviços existentes

## Constitution Check

*GATE: Must pass before Phase 0 research. Re-check after Phase 1 design.*

| Princípio | Status | Observações |
|-----------|--------|-------------|
| **I. LGPD Compliance** | ✅ PASS | Reutiliza TempFileManager existente, cleanup automático em `finally` blocks |
| **II. Azure Free Tier Protection** | ✅ PASS | Rate limiting já implementado nos endpoints individuais; multimodal reutiliza os mesmos checks |
| **III. Test Coverage >70%** | ✅ PASS | Serviços individuais já testados; foco em testar fusão e endpoint |
| **IV. Container-First** | ✅ PASS | Nenhuma dependência nova; reutiliza container existente |
| **V. Documentação em Português** | ✅ PASS | Spec em português, código segue padrão Python (inglês) |
| **VI. Security-First** | ✅ PASS | Validação de uploads já implementada nos endpoints existentes |
| **VII. Multimodal Architecture** | ✅ PASS | Último módulo core; implementa a composição multimodal planejada |

**Gates para prosseguir:**
- ✅ Não adiciona novos serviços externos obrigatórios (reutiliza existentes)
- ✅ Não quebra compatibilidade com endpoints existentes
- ✅ Respeita LGPD (arquivos temporários, sem logging de conteúdo)
- ✅ Escopo definido e mensurável

## Project Structure

### Documentation (this feature)

```text
specs/005-multimodal-fusion/
├── plan.md              # This file
├── tasks.md             # Phase 2 output (será criado após plan approval)
└── spec.md              # Already exists
```

### Source Code (repository root)

```text
src/
├── api/
│   └── routes/
│       ├── multimodal.py       # NOVO: Endpoint POST /analyze/multimodal
│       └── ... (routes existentes)
├── models/
│   └── schemas.py              # ADICIONAR: MultimodalRequest, MultimodalResponse, FusionResult
├── services/
│   └── multimodal_fusion.py    # NOVO: FusionService, LateFusionCalculator
└── core/
    └── ... (existente)

tests/
├── unit/
│   └── services/
│       └── test_multimodal_fusion.py  # NOVO: Testes do algoritmo de fusão
├── integration/
│   └── test_multimodal_endpoint.py    # NOVO: Testes do endpoint
└── ... (existentes)
```

**Structure Decision**: Seguir padrão estabelecido pelas outras modalidades. FusionService orquestra serviços existentes sem duplicar lógica.

## Complexity Tracking

> **Fill ONLY if Constitution Check has violations that must be justified**

| Violation | Why Needed | Simpler Alternative Rejected Because |
|-----------|------------|-------------------------------------|
| Nenhuma | - | - |

---

## Phase Completion Status

### Phase 0: Research ✅ COMPLETED
**Output**: spec.md já contém research técnico (late fusion, asyncio.gather, tratamento de falhas)
- Algoritmo de late fusion definido
- Processamento paralelo com asyncio confirmado
- Regras de alerta estabelecidas

### Phase 1: Design ✅ COMPLETED
**Outputs**:
- Schemas definidos no spec.md (MultimodalRequest, MultimodalResponse, FusionResult)
- Contrato da API documentado em api-contracts.md
- Algoritmo de fusão com código de referência no spec.md

### Phase 2: Tasks ⏳ PENDING
**Output**: tasks.md será criado após aprovação deste plan

---

## Integration Points

### Com endpoints existentes

```python
# FusionService orquestra:
from src.services.text_analysis import TextAnalysisService
from src.services.audio_analysis import AudioAnalysisService
from src.services.video_analysis import VideoAnalysisService

# Cada serviço mantém sua interface atual
# - TextAnalysisService.analyze(text, tipo, patient_id) -> TextAnalysisResponse
# - AudioAnalysisService.analyze(audio_path, patient_id) -> dict
# - VideoAnalysisService.analyze(video_path, duration, temp_dir) -> dict
```

### Com schemas existentes

```python
# MultimodalResponse compõe:
class MultimodalResponse(BaseModel):
    fusao: FusionResult
    texto: TextAnalysisResponse | None
    audio: AudioAnalysisResponse | None
    video: VideoAnalysisResponse | None
    metadata: AnalysisMetadata
```

### Rate Limiting

- Texto e áudio: rate limiting aplicado nos serviços individuais (já existente)
- Vídeo: processamento local (sem quota Azure)
- Multimodal: não adiciona quota adicional; cada modalidade consome sua própria quota

---

## Context7 Research Check

Antes de implementar, consultar Context7 MCP para verificar melhores práticas atualizadas (2026):

- [ ] FastAPI 0.135+ async patterns e lifespan management
- [ ] Pydantic v2 model composition (nested models, computed fields)
- [ ] Python 3.12 asyncio.gather best practices e exception handling
- [ ] pytest-asyncio testing patterns para processamento paralelo
- [ ] Structlog 24.x structured logging patterns

**Why**: O projeto usa stack moderna (FastAPI 0.135+, Pydantic v2, Python 3.12). Context7 garante que implementação segue padrões mais recentes e evita antipatterns de versões anteriores.

---

## Decisões de Design

### 1. Late Fusion (não Early Fusion)

**Decisão**: Combinar resultados finais de cada modalidade (late fusion)

**Rationale**:
- Simplicidade: não precisa alinhar features de modalidades diferentes
- Transparência: retorna resultados individuais + fusão
- Extensibilidade: nova modalidade não requer mudanças nas existentes
- Constitution: princípio VII (Multimodal Architecture) recomenda composição

### 2. Ponderação por Confiança

**Decisão**: Modalidades com maior confiança têm peso maior na fusão

**Rationale**:
- Áudio com baixa qualidade de gravação → confiança baixa → peso menor
- Texto claro e detalhado → confiança alta → peso maior
- Fallback: se confiança = 0, distribui pesos igualmente

### 3. Tratamento de Falhas

**Decisão**: Se uma modalidade falhar, processa as demais (graceful degradation)

**Rationale**:
- Usuário pode submeter vídeo corrompido mas áudio e texto válidos
- Alerta no response indica quais modalidades falharam
- Só retorna erro se TODAS as modalidades falharem

### 4. Timeout por Modalidade

**Decisão**: 30s timeout por modalidade via `asyncio.wait_for`

**Rationale**:
- Vídeo longo pode demorar; não deve bloquear texto/áudio
- SC-001: latência total < 15s; timeout evita exceções
- Texto geralmente < 1s; áudio < 10s; vídeo < 10s

---

## Próximos Passos

1. Criar `tasks.md` com lista detalhada de tarefas
2. Executar tarefas em ordem:
   - Fase 1: Schemas (MultimodalRequest, MultimodalResponse, FusionResult)
   - Fase 2: FusionService + LateFusionCalculator
   - Fase 3: Endpoint /analyze/multimodal
   - Fase 4: Testes unitários e integração
3. Executar `@speckit.clarify` para auditoria
4. Merge na branch main
