# Feature Specification: Análise Multimodal (Fusão)

**Feature Branch**: `[005-multimodal-fusion]`
**Created**: 2026-04-11
**Status**: Draft
**Input**: User description: "Implementar endpoint de fusão multimodal combinando texto, áudio e imagem"

---

## User Scenarios & Testing

### User Story 1 - Fusão Late de Modalidades (Priority: P1)

Como profissional de saúde, quero submeter texto + áudio + imagem simultaneamente para análise combinada mais precisa.

**Why this priority**: Fusão multimodal é o diferencial principal do projeto e requisito obrigatório.

**Independent Test**: POST `/analyze/multimodal` processa 3 modalidades e retorna resultado combinado.

**Acceptance Scenarios**:

1. **Given** texto, áudio e imagem válidos, **When** submeto ao endpoint, **Then** processa as 3 modalidades
2. **Given** resultados individuais, **When** combinados, **Then** aplica late fusion ponderado
3. **Given** risco alto em 2+ modalidades, **When** fusão calculada, **Then** alerta = true
4. **Given** apenas uma modalidade, **When** submetida, **Then** processa normalmente (fallback)

### User Story 2 - Geração de Recomendações (Priority: P1)

Como profissional de saúde, quero receber recomendações de ação baseadas na análise combinada.

**Why this priority**: Recomendações ajudam na tomada de decisão clínica.

**Independent Test**: Response inclui campo recomendação contextualizado.

**Acceptance Scenarios**:

1. **Given** risco_violencia = alto, **When** fusão completa, **Then** recomendação sugere encaminhamento
2. **Given** risco_saude_mental = alto, **When** fusão completa, **Then** recomendação sugere apoio psicológico
3. **Given** ambos riscos = baixo, **When** fusão completa, **Then** recomendação padrão de acompanhamento

### User Story 3 - Processamento Paralelo (Priority: P2)

Como sistema, quero processar modalidades em paralelo para otimizar tempo de resposta.

**Why this priority**: Latência é crítica para experiência do usuário.

**Independent Test**: Verificar que tempo de resposta é menor que soma individual.

**Acceptance Scenarios**:

1. **Given** 3 modalidades, **When** submetidas, **Then** processa texto, áudio e imagem simultaneamente
2. **Given** processamento paralelo, **When** uma modalidade falha, **Then** outras continuam e retornam resultado parcial

---

## Requirements

### Functional Requirements

- **FR-001**: Endpoint POST `/analyze/multimodal` disponível
- **FR-002**: Aceita texto (form-data) + áudio (file) + imagem (file)
- **FR-003**: Pelo menos uma modalidade deve ser fornecida
- **FR-004**: Processa modalidades em paralelo (asyncio.gather)
- **FR-005**: Implementa late fusion com ponderação por confiança
- **FR-006**: Retorna obrigatoriamente: risco_violencia, risco_saude_mental (calculados na fusão)
- **FR-007**: Retorna: score combinado, confiança, alerta (boolean), recomendação
- **FR-008**: Retorna resultados individuais de cada modalidade
- **FR-009**: Gera alerta se risco alto em 2+ modalidades
- **FR-010**: Fallback gracioso se uma modalidade falhar

### Key Entities

- **MultimodalRequest**: multipart/form-data com texto, audio, imagem, patient_id
- **FusionResult**: { risco_violencia, risco_saude_mental, confiança, alerta, recomendação }
- **MultimodalResponse**: { fusao: FusionResult, texto: Result, audio: Result, imagem: Result, metadata }
- **FusionService**: Coordena processamento e aplica algoritmo de fusão

---

## Success Criteria

- **SC-001**: Latência total < 15s (com 3 modalidades)
- **SC-002**: Fusão demonstra precisão superior às modalidades individuais
- **SC-003**: Alertas gerados corretamente em casos de alto risco
- **SC-004**: Recomendações são contextualizadas e úteis
- **SC-005**: Processamento paralelo funciona corretamente

---

## Assumptions

- Dependências: US01, US02, US03 (texto, áudio, imagem) implementados
- Late fusion é suficiente para MVP (early fusion seria complexo demais)
- Ponderação por confiança: modalidades com maior confiança têm peso maior
- Resultados individuais são sempre retornados para transparência

---

## Technical Notes

### Algoritmo de Late Fusion
```python
# Ponderação por confiança
peso_texto = confiança_texto / (soma_confianças)
peso_audio = confiança_audio / (soma_confianças)
peso_imagem = confiança_imagem / (soma_confianças)

# Score combinado
score_fusao = (score_texto * peso_texto + 
               score_audio * peso_audio + 
               score_imagem * peso_imagem)
```

### Regras de Alerta
- risco_alto em 1 modalidade: alerta = false (atenção)
- risco_alto em 2+ modalidades: alerta = true (crítico)
- Confiança fusão > 0.8: considerar alta confiabilidade

### Processamento Paralelo
- Usar asyncio.gather() para chamadas independentes
- Tratar exceções individualmente (não falhar tudo)
- Timeout por modalidade: 30s

---

## Melhores Práticas de Implementação

### Processamento Paralelo com Asyncio

```python
import asyncio
from typing import Optional, Dict

class FusionService:
    """Serviço de fusão multimodal com processamento paralelo"""

    def __init__(
        self,
        text_service: TextAnalysisService,
        audio_service: AudioAnalysisService,
        image_service: ImageAnalysisService
    ):
        self.text_svc = text_service
        self.audio_svc = audio_service
        self.image_svc = image_service

    async def analyze(
        self,
        texto: Optional[str] = None,
        audio: Optional[UploadFile] = None,
        imagem: Optional[UploadFile] = None
    ) -> MultimodalResult:
        """
        Processa múltiplas modalidades em paralelo
        """
        tasks = []
        results = {}

        # Cria tasks para cada modalidade presente
        if texto:
            tasks.append(self._analyze_with_timeout(
                "texto", self.text_svc.analyze(texto)
            ))
        if audio:
            tasks.append(self._analyze_with_timeout(
                "audio", self.audio_svc.analyze(audio)
            ))
        if imagem:
            tasks.append(self._analyze_with_timeout(
                "imagem", self.image_svc.analyze(imagem)
            ))

        # Executa em paralelo com tratamento de exceções individuais
        completed = await asyncio.gather(*tasks, return_exceptions=True)

        # Processa resultados
        for result in completed:
            if isinstance(result, Exception):
                logger.warning(f"Modalidade falhou: {result}")
                continue
            results[result["tipo"]] = result

        # Se nenhum resultado, erro
        if not results:
            raise HTTPException(500, "Todas as modalidades falharam")

        # Aplica fusão
        fusion = self._calculate_fusion(results)

        return MultimodalResult(
            fusao=fusion,
            **results
        )

    async def _analyze_with_timeout(
        self,
        modalidade: str,
        coro,
        timeout_secs: int = 30
    ):
        """Executa análise com timeout"""
        try:
            result = await asyncio.wait_for(coro, timeout=timeout_secs)
            result["tipo"] = modalidade
            return result
        except asyncio.TimeoutError:
            logger.error(f"Timeout em {modalidade}")
            raise
```

### Late Fusion com Ponderação

```python
from typing import Dict, List
from dataclasses import dataclass

@dataclass
class ModalidadeResult:
    risco: str  # "baixo", "medio", "alto"
    confiança: float
    score: float  # -1 a 1

class LateFusionCalculator:
    """Calcula fusão usando late fusion ponderada"""

    RISK_VALUES = {"baixo": 0.0, "medio": 0.5, "alto": 1.0}

    def calculate(
        self,
        results: Dict[str, ModalidadeResult]
    ) -> Dict:
        """
        Combina resultados usando ponderação por confiança
        """
        if not results:
            raise ValueError("Nenhum resultado para fusão")

        # Calcula pesos baseados na confiança
        total_confiança = sum(r.confiança for r in results.values())

        if total_confiança == 0:
            # Fallback: pesos iguais
            pesos = {k: 1.0 / len(results) for k in results}
        else:
            pesos = {
                k: r.confiança / total_confiança
                for k, r in results.items()
            }

        # Calcula score ponderado
        score_fusao = sum(
            self.RISK_VALUES[r.risco] * pesos[k]
            for k, r in results.items()
        )

        # Determina risco combinado
        if score_fusao < 0.33:
            risco_fusao = "baixo"
        elif score_fusao < 0.66:
            risco_fusao = "medio"
        else:
            risco_fusao = "alto"

        # Confiança combinada (média ponderada)
        confiança_fusao = sum(
            r.confiança * pesos[k]
            for k, r in results.items()
        )

        # Alerta se 2+ modalidades com risco alto
        riscos_altos = sum(
            1 for r in results.values() if r.risco == "alto"
        )
        alerta = riscos_altos >= 2

        return {
            "risco_violencia": risco_fusao,
            "risco_saude_mental": risco_fusao,
            "confiança": round(confiança_fusao, 2),
            "alerta": alerta,
            "recomendacao": self._generate_recommendation(
                risco_fusao, alerta
            ),
            "scores_por_modalidade": {
                k: {"risco": r.risco, "peso": round(pesos[k], 2)}
                for k, r in results.items()
            }
        }

    def _generate_recommendation(self, risco: str, alerta: bool) -> str:
        """Gera recomendação baseada no risco"""
        if alerta:
            return "Encaminhar para equipe multidisciplinar urgentemente"
        elif risco == "alto":
            return "Acompanhamento prioritário recomendado"
        elif risco == "medio":
            return "Monitorar e reavaliar em consulta seguinte"
        else:
            return "Continuar acompanhamento de rotina"
```

### Tratamento de Falhas Gracioso

```python
from typing import Optional

class GracefulFusionService:
    """Serviço de fusão com fallback para falhas"""

    async def analyze_with_fallback(
        self,
        texto: Optional[str] = None,
        audio: Optional[UploadFile] = None,
        imagem: Optional[UploadFile] = None
    ) -> MultimodalResult:
        """
        Processa com fallback: se uma modalidade falhar,
        continua com as demais
        """
        results = {}
        errors = []

        # Tenta cada modalidade individualmente
        if texto:
            try:
                results["texto"] = await self.text_svc.analyze(texto)
            except Exception as e:
                logger.warning(f"Texto falhou: {e}")
                errors.append("texto")

        if audio:
            try:
                results["audio"] = await self.audio_svc.analyze(audio)
            except Exception as e:
                logger.warning(f"Audio falhou: {e}")
                errors.append("audio")

        if imagem:
            try:
                results["imagem"] = await self.image_svc.analyze(imagem)
            except Exception as e:
                logger.warning(f"Imagem falhou: {e}")
                errors.append("imagem")

        # Se pelo menos uma deu certo, faz fusão
        if results:
            fusion = self._calculate_fusion(results)

            # Adiciona aviso se houve falhas
            if errors:
                fusion["warnings"] = f"Modalidades indisponíveis: {', '.join(errors)}"

            return MultimodalResult(fusao=fusion, **results)

        # Se todas falharam, erro
        raise HTTPException(503, "Todas as modalidades indisponíveis")
```

### Logging de Fusão

```python
import structlog
from time import perf_counter

logger = structlog.get_logger()

async def fusion_with_logging(
    self,
    results: Dict[str, ModalidadeResult]
) -> MultimodalResult:
    start = perf_counter()

    logger.info(
        "fusion_started",
        modalities=list(results.keys()),
        individual_risks={
            k: r.risco for k, r in results.items()
        }
    )

    fusion = self._calculate_fusion(results)
    duration = perf_counter() - start

    logger.info(
        "fusion_completed",
        duration_seconds=duration,
        final_risk=fusion["risco_violencia"],
        confidence=fusion["confiança"],
        alert=fusion["alerta"]
    )

    return fusion
```

### Métricas de Performance

```python
from time import perf_counter
from typing import Dict

class PerformanceTracker:
    """Rastreia performance do processamento multimodal"""

    def __init__(self):
        self.timings: Dict[str, float] = {}

    def track(self, name: str, duration: float):
        self.timings[name] = duration

    def get_summary(self) -> Dict:
        total = sum(self.timings.values())
        return {
            "total_duration_ms": round(total * 1000, 2),
            "modalities": {
                k: round(v * 1000, 2)
                for k, v in self.timings.items()
            },
            "parallel_efficiency": self._calculate_efficiency()
        }

    def _calculate_efficiency(self) -> float:
        """
        Calcula eficiência do processamento paralelo
        (soma individual vs tempo total)
        """
        if not self.timings:
            return 1.0

        total = sum(self.timings.values())
        max_individual = max(self.timings.values())

        # Se total = max, significa que processou em paralelo perfeitamente
        return round(max_individual / total if total > 0 else 1.0, 2)
```

---

## Referências

- Documentação completa: `docs/technical/best-practices.md` (integrado)
- [Asyncio - Python Documentation](https://docs.python.org/3/library/asyncio.html)
- [Multimodal ML Architecture](https://en.wikipedia.org/wiki/Multimodal_learning)
