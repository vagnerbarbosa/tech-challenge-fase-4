# Tarefas: Fusão Multimodal

**Funcionalidade**: Endpoint de Fusão Multimodal
**Branch**: `005-multimodal-fusion`
**Gerado em**: 2026-04-21

---

## Fase 1: Fundação (Schemas e Modelos)

**Objetivo**: Definir estruturas de dados necessárias para a fusão multimodal

### Schemas Pydantic

- [X] T001 [P] Criar FusionResult schema: Adicionar `FusionResult` em `src/models/schemas.py` com campos: risco_violencia, risco_saude_mental, confiança, alerta, recomendacao, scores_por_modalidade
- [X] T002 [P] Criar MultimodalRequest schema: Adicionar `MultimodalRequest` em `src/models/schemas.py` com campos opcionais: texto (str), audio (UploadFile), video (UploadFile), patient_id (str | None)
- [X] T003 [P] Criar MultimodalResponse schema: Adicionar `MultimodalResponse` em `src/models/schemas.py` com: fusao (FusionResult), texto (TextAnalysisResponse | None), audio (AudioAnalysisResponse | None), video (VideoAnalysisResponse | None), metadata (AnalysisMetadata)
- [X] T004 [P] Adicionar validação MultimodalRequest: Validador que garante pelo menos uma modalidade foi fornecida (FR-003)
- [X] T005 [P] Adicionar metadata de fusão: Campo `modalidades_processadas` no metadata indicando quais modalidades foram enviadas/processadas

**Ponto de Verificação**: Schemas prontos - implementação dos serviços pode começar

---

## Fase 2: Serviço de Fusão (Core Algorithm)

**Objetivo**: Implementar algoritmo de late fusion e orquestração

### LateFusionCalculator

- [X] T006 [P] Criar LateFusionCalculator: Implementar `src/services/multimodal_fusion.py` com classe `LateFusionCalculator` contendo método `calculate()` que recebe dict de ModalidadeResult e retorna FusionResult
- [X] T007 [P] Implementar mapeamento de risco para score: Método interno `_risk_to_score()` mapeando {"baixo": 0.0, "medio": 0.5, "alto": 1.0}
- [X] T008 [P] Implementar cálculo de pesos por confiança: Pesos = confiança / soma_confianças; se confiança total = 0, lançar exceção "Impossível calcular risco: confiança insuficiente em todas as modalidades"
- [X] T009 [P] Implementar score_fusao ponderado: score_fusao = sum(score_modalidade * peso_modalidade)
- [X] T010 [P] Implementar determinação de risco combinado: score < 0.33 → baixo; < 0.66 → medio; else → alto
- [X] T011 [P] Implementar alerta (2+ riscos altos OU confiança > 0.8): `alerta = True` se 2+ modalidades com risco == "alto" OU confiança_fusão > 0.8
- [X] T012 [P] Implementar geração de recomendação: `_generate_recommendation()` com 4 níveis (alerta=True → encaminhamento urgente; alto → acompanhamento prioritário; medio → monitorar; baixo → acompanhamento rotina)
- [X] T013 [P] Implementar confiança combinada: Média ponderada das confianças individuais

### FusionService

- [X] T014 [P] Criar FusionService: Implementar classe `FusionService` em `src/services/multimodal_fusion.py` com dependências dos 3 serviços existentes
- [X] T015 [P] Implementar processamento paralelo: Método `analyze()` usa `asyncio.gather()` com `return_exceptions=True` para processar modalidades em paralelo
- [X] T016 [P] Implementar timeout por modalidade: Usar `asyncio.wait_for(coro, timeout=30)` para cada modalidade
- [X] T017 [P] Implementar tratamento de falhas gracioso: Se uma modalidade falhar (Exception/TimeoutError), logar warning e continuar com as demais (FR-010). Usar `await` direto para vídeo (após T058 refatorar para async)
- [X] T018 [P] Implementar validação de entrada: Verificar se pelo menos uma modalidade foi fornecida; retornar HTTP 400 se nenhuma
- [X] T019 [P] Implementar logging estruturado: Logar início/fim da fusão, modalidades processadas, riscos individuais, tempo total (sem logar conteúdo sensível - LGPD)
- [X] T020 [P] Implementar PerformanceTracker: Classe interna para rastrear tempo de cada modalidade e eficiência do paralelismo

**Ponto de Verificação**: FusionService pronto - endpoint pode ser implementado

---

## Fase 3: Endpoint Multimodal

**Objetivo**: Expor funcionalidade via API REST

### Rota FastAPI

- [X] T021 [P] Criar rota multimodal: Implementar `src/api/routes/multimodal.py` com router prefix="/analyze"
- [X] T022 [P] Implementar POST /analyze/multimodal: Endpoint aceita multipart/form-data com campos opcionais: texto (str), audio (UploadFile), video (UploadFile), patient_id (str)
- [X] T023 [P] Implementar validação de arquivos: Reutilizar `validate_audio_file()` e `validate_video_file()` quando arquivos forem fornecidos
- [X] T024 [P] Implementar rate limiting multimodal: Verificar quota para texto e áudio (reutilizar `check_and_increment_quota`); vídeo não consome quota
- [X] T025 [P] Implementar LGPD cleanup: Salvar arquivos temporários em temp_dir; cleanup em `finally` block
- [X] T026 [P] Implementar montagem de resposta: Montar MultimodalResponse com fusao + resultados individuais + metadata
- [ ] ~~T027 [P] Implementar cache de fusão~~: **PÓS-MVP** — cache individual já existe; cache de fusão deixado para pós-MVP (decisão clarify)

### Refatoração Prévia (Garantia de não-impacto)

- [X] T057 [P] Refatorar VideoAnalysisService para async: Converter `VideoAnalysisService.analyze()` para `async def analyze()` sem alterar comportamento do endpoint `/analyze/video` existente
- [X] T058 [P] Verificar não-regressão do endpoint vídeo: Rodar testes existentes de vídeo (`tests/unit/services/test_video_analysis.py`, `tests/integration/test_video_endpoint.py`) e garantir 100% passando após refatoração

### Integração com App

- [X] T028 [P] Registrar rota no app: Importar e incluir router em `src/api/main.py`

**Ponto de Verificação**: Endpoint funcional - testes podem ser escritos

---

## Fase 4: Testes Unitários

**Objetivo**: Garantir correção do algoritmo de fusão

### Testes LateFusionCalculator

- [X] T029 [P] Testar fusão com 3 modalidades: Criar `tests/unit/services/test_multimodal_fusion.py` - teste com texto=alto, audio=medio, video=baixo → verificar risco_fusao
- [X] T030 [P] Testar ponderação por confiança: Verificar que modalidade com maior confiança tem peso maior
- [X] T031 [P] Testar alerta (2+ riscos altos): 2 modalidades com risco=alto → alerta=True
- [X] T032 [P] Testar sem alerta (1 risco alto): 1 modalidade com risco=alto → alerta=False
- [X] T033 [P] Testar rejeição de confiança zero: Todas confianças = 0 → lançar exceção com mensagem "Impossível calcular risco: confiança insuficiente"
- [X] T034 [P] Testar recomendações: Verificar 4 cenários de recomendação (alerta, alto, medio, baixo)
- [X] T035 [P] Testar fusão com 2 modalidades: Texto + áudio (sem vídeo) → fusão deve funcionar
- [X] T036 [P] Testar fusão com 1 modalidade: Apenas texto → fallback, retorna risco do texto

### Testes FusionService

- [X] T037 [P] Testar processamento paralelo: Mock dos 3 serviços; verificar que foram chamados
- [X] T038 [P] Testar timeout: Simular timeout em uma modalidade; verificar que outras continuam
- [X] T039 [P] Testar falha graciosa: Simular exceção em uma modalidade; verificar que outras continuam e resultado parcial é retornado
- [X] T040 [P] Testar falha total: Todas modalidades falham → HTTPException 503
- [X] T041 [P] Testar validação sem modalidade: Nenhuma modalidade fornecida → HTTPException 400

**Ponto de Verificação**: Testes unitários passando

---

## Fase 5: Testes de Integração

**Objetivo**: Validar endpoint end-to-end

- [X] T042 [P] Testar endpoint com texto apenas: POST /analyze/multimodal com texto=string → 200
- [X] T043 [P] Testar endpoint com texto + áudio: Multipart com texto e arquivo de áudio → 200
- [X] T044 [P] Testar endpoint com 3 modalidades: Multipart com texto, áudio e vídeo → 200, verificar estrutura da resposta
- [X] T045 [P] Testar endpoint sem modalidade: POST sem nenhuma modalidade → 400
- [X] T046 [P] Testar campos obrigatórios na resposta: Verificar que response sempre contém risco_violencia e risco_saude_mental na fusao
- [X] T047 [P] Testar latência < 15s: Medir tempo de resposta com 3 modalidades mockadas

**Ponto de Verificação**: Testes de integração passando

---

## Fase 6: Qualidade e Documentação

**Objetivo**: Garantir qualidade e documentar

- [X] T048 [P] Rodar Ruff: `ruff check src/ tests/` - zero erros
- [X] T049 [P] Rodar mypy: `mypy src/services/multimodal_fusion.py src/api/routes/multimodal.py` - zero erros
- [X] T050 [P] Verificar cobertura >70%: `pytest tests/unit/services/test_multimodal_fusion.py --cov=src/services/multimodal_fusion --cov-report=term`
- [X] T051 [P] Atualizar README.md: Adicionar seção "Análise Multimodal" com exemplo de request/response
- [X] T052 [P] Atualizar docs/PROJECT_STATUS.md: Mudar status de Spec 005 para "✅ Concluído"
- [X] T053 [P] Atualizar specs/README.md: Mudar status de Spec 005 para "✅ Concluído"
- [X] T059 [P] Atualizar collections da API: Adicionar endpoint `/analyze/multimodal` em `docs/collection.json` (Postman/Insomnia/Bruno) com exemplos de request/response para 1, 2 e 3 modalidades

**Ponto de Verificação**: Qualidade validada e documentação atualizada

---

## Checklist de Finalização

- [X] T054 Executar testes Docker: `./scripts/test-docker.sh unit` passando
- [X] T055 Executar auditoria @speckit.clarify: Revisar implementação contra spec e constitution
- [X] T056 Criar PR para branch main: Título em português, descrição com o que foi implementado

---

## Dependências entre Tarefas

```
T001-T005 (Schemas)
    ↓
T006-T013 (LateFusionCalculator)
    ↓
T014-T020 (FusionService)
    ↓
T021-T028 (Endpoint)
    ↓
T029-T041 (Testes Unitários)  ←  pode começar após T006-T013
    ↓
T042-T047 (Testes Integração)  ←  pode começar após T021-T028
    ↓
T048-T056 (Qualidade e Docs)
```

---

## Notas

- **Prioridade P1**: Tarefas marcadas com [P] são obrigatórias para MVP
- **Mock de áudio**: Usar fixture de áudio de teste existente (`tests/`) para testes de integração
- **Mock de vídeo**: Usar fixture de vídeo de teste existente ou criar vídeo fake com OpenCV
- **Timeout**: Configurável via variável de ambiente `MULTIMODAL_TIMEOUT_SECONDS` (padrão: 30)
