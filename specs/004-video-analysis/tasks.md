# Tarefas: Análise de Vídeo com YOLOv8

**Funcionalidade**: Endpoint de Análise de Vídeo  
**Branch**: `011-video-analysis-yolov8`  
**Gerado em**: 2026-04-19

---

## Fase 1: Configuração (Infraestrutura Compartilhada)

**Objetivo**: Inicialização do projeto e configuração de dependências

### Dependências e Download do Modelo

- [X] T001 Adicionar dependência ultralytics: Adicionar `ultralytics = ">=8.0.0"` em `[tool.poetry.dependencies]` no `pyproject.toml`
- [X] T002 Executar poetry lock: Executar `poetry lock --no-update` para atualizar o arquivo de lock
- [X] T003 [P] Instalar dependências: Executar `poetry install` para instalar ultralytics e OpenCV
- [X] T004 Baixar modelo YOLOv8n: Criar script `scripts/download_yolo_model.py` para baixar `yolov8n.pt` (~6MB) para o diretório `models/`
- [X] T005 Atualizar Dockerfile: Adicionar download do modelo YOLOv8 e dependências de sistema (libgl1, libglib2.0-0) no `Dockerfile`

### Versionamento da API

- [X] T005a Atualizar versão da API: Incrementar `app_version` de `"0.3.0"` para `"0.4.0"` em `src/core/config.py` (linha 37)
- [X] T005b Atualizar versão no docker-compose: Incrementar `APP_VERSION` de `"0.3.0"` para `"0.4.0"` em `docker-compose.yml`
- [X] T005c Atualizar versão no env example: Incrementar `APP_VERSION` de `"0.3.0"` para `"0.4.0"` em `.env.example`

---

## Fase 2: Fundação (Pré-requisitos Bloqueantes)

**Objetivo**: Infraestrutura principal que DEVE estar completa antes de QUALQUER história de usuário

**⚠️ CRÍTICO**: Nenhum trabalho de história de usuário pode começar até esta fase estar completa

### Infraestrutura de Processamento de Vídeo

- [X] T006 [P] Criar serviço VideoProcessor: Implementar `src/services/video_processor.py` com extração de frames usando OpenCV e FPS adaptativo (1 FPS ≤30s, 0.2 FPS >30s)
- [X] T007 [P] Criar YOLOv8Service: Implementar `src/services/yolo_service.py` para inferência de detecção de objetos com mapeamento de classes COCO
- [X] T008 [P] Criar BleedingDetector: Implementar `src/services/bleeding_detector.py` com threshold de cor HSV para detecção de sangue (>2% pixels vermelhos)
- [X] T009 Criar VideoAnalysisService: Implementar `src/services/video_analysis.py` orquestrando todos os componentes de análise de vídeo
- [X] T010 Criar calculadora de risco: Implementar `src/services/risk_calculator_video.py` com função `calculate_video_risk()` mapeando detecções para níveis de risco
- [X] T011 Adicionar utilitários de validação: Criar `src/utils/video_validation.py` com validação de formato (MP4, AVI, MOV), tamanho (50MB) e duração (120s)

**Ponto de Verificação**: Fundação pronta - implementação de histórias de usuário pode começar em paralelo

---

## Fase 3: História de Usuário 1 - Detecção de Instrumentos Cirúrgicos (Prioridade: P1) 🎯 MVP

**Objetivo**: Identificar instrumentos cirúrgicos ginecológicos em vídeos de procedimentos para documentação e análise

**Teste Independente**: POST `/analyze/video` retorna detecções de objetos mesmo sem análise de texto/áudio

### Implementação da História de Usuário 1

- [X] T012 [P] [US1] Mapear classes COCO relevantes: Definir `RELEVANT_CLASSES` em `src/services/yolo_service.py` incluindo person (0), scissors (77), knife (43)
- [X] T013 [P] [US1] Implementar filtragem por confiança: Adicionar filtro conf_threshold >= 0.5 em YOLOv8Service.detect()
- [X] T014 [US1] Adicionar normalização de bounding box: Garantir coordenadas bbox (x, y, w, h) formatadas corretamente no schema Detection
- [X] T015 [US1] Adicionar metadados de frame: Incluir frame_number e timestamp nos resultados de detecção

### Testes da História de Usuário 1 (OPCIONAL - apenas se testes solicitados) ⚠️

> **NOTA: Escreva estes testes PRIMEIRO, garanta que FALHEM antes da implementação**

- [X] T016 [P] [US1] Teste unitário YOLOv8Service: Criar `tests/unit/services/test_yolo_service.py` com mock do modelo retornando detecções de instrumentos
- [X] T017 [P] [US1] Teste unitário VideoProcessor: Criar `tests/unit/services/test_video_processor.py` com fixture de vídeo de teste

**Ponto de Verificação**: Neste ponto, a História de Usuário 1 deve estar totalmente funcional e testável independentemente

---

## Fase 4: História de Usuário 2 - Detecção de Sangramento Anômalo (Prioridade: P1) 🎯 MVP

**Objetivo**: Detectar sangramento anômalo durante procedimentos para alertar sobre complicações

**Teste Independente**: Detecção de sangramento funciona independentemente de outras análises

### Implementação da História de Usuário 2

- [X] T018 [P] [US2] Implementar detecção HSV de sangramento: Adicionar conversão de espaço de cor HSV em BleedingDetector com threshold de pixels vermelhos (>2%)
- [X] T019 [P] [US2] Adicionar cálculo de confiança de sangramento: Normalizar percentual para score de confiança 0-1 (min 0.2 para 1%, max 1.0 para 5%+)
- [X] T020 [US2] Integrar detector de sangramento: Adicionar chamadas BleedingDetector em VideoAnalysisService apenas para os primeiros 5 frames
- [X] T021 [US2] Adicionar sangramento às detecções: Anexar detecções de sangramento às detecções YOLO com classe "sangramento"
- [X] T022 [US2] Gerar alertas de sangramento: Criar alerta quando confiança de sangramento > 0.8 com severidade "alta"

### Testes da História de Usuário 2 (OPCIONAL - apenas se testes solicitados) ⚠️

- [X] T023 [P] [US2] Teste unitário BleedingDetector: Criar `tests/unit/services/test_bleeding_detector.py` com imagens de teste contendo regiões vermelhas

**Ponto de Verificação**: Histórias de Usuário 1 E 2 devem funcionar independentemente

---

## Fase 5: História de Usuário 3 - Análise de Linguagem Corporal (Prioridade: P1) ✅ COMPLETA

**Objetivo**: Identificar sinais não-verbais de desconforto ou medo em consultas para triagem de violência

**Teste Independente**: Detecção de postura/linguagem corporal funciona isoladamente

### Implementação da História de Usuário 3

- [X] T024 [P] [US3] Detectar postura da pessoa: Analisar dimensões e posição do bounding box de pessoa ao longo do tempo em VideoAnalysisService
- [X] T025 [P] [US3] Implementar análise de movimento: Calcular variância de movimento frame-a-frame para detecção de agitação
- [X] T026 [US3] Adicionar indicadores de risco de postura: Mapear posturas defensivas (tensa, fechada) para indicadores de risco na resposta
- [X] T027 [US3] Integrar com calculadora de risco: Atualizar `calculate_video_risk()` para incluir elevação de risco baseada em postura

### Testes da História de Usuário 3 (OPCIONAL - apenas se testes solicitados) ⚠️

- [X] T028 [P] [US3] Teste unitário de detecção de postura: Criar `tests/unit/services/test_posture_analysis.py` com sequências de frames de teste

**Ponto de Verificação**: Histórias de Usuário 1, 2 E 3 devem funcionar independentemente

---

## Fase 6: História de Usuário 4 - Triagem de Violência e Saúde Mental (Prioridade: P1) 🎯 MVP

**Objetivo**: Retornar campos obrigatórios `risco_violencia` e `risco_saude_mental` com base nas detecções

**Teste Independente**: Endpoint retorna campos obrigatórios mesmo sem detecções

### Schemas e Endpoint da API

- [X] T029 [US4] Criar schemas VideoAnalysis: Adicionar `VideoAnalysisRequest`, `VideoAnalysisResponse`, `Detection`, `BoundingBox`, `Alert` e `VideoAnalysisMetadata` em `src/models/schemas.py`
- [X] T030 [US4] [P] Implementar validação de campos obrigatórios: Garantir que `risco_violencia` e `risco_saude_mental` estejam sempre presentes na resposta (padrão "baixo")
- [X] T031 [US4] Criar endpoint de vídeo: Implementar `POST /analyze/video` em `src/api/routes/video.py` com suporte a multipart/form-data
- [X] T032 [US4] Adicionar endpoint ao main: Incluir router de vídeo em `src/api/main.py` com prefixo `/analyze`

### Validação e Tratamento de Erros

- [X] T033 [US4] Adicionar validação de arquivo: Validar formato de vídeo (MP4, AVI, MOV) usando magic numbers no endpoint, retornar 400 se inválido
- [X] T034 [US4] Adicionar validação de tamanho: Verificar limite de 50MB e retornar 413 (Payload Too Large) se excedido
- [X] T035 [US4] Adicionar validação de duração: Verificar limite de 2 minutos usando OpenCV, retornar 400 com erro "DURATION_EXCEEDED"
- [X] T036 [US4] Implementar FPS adaptativo: Calcular intervalo de frames baseado na duração do vídeo (1 FPS ≤30s, 0.2 FPS >30s)
- [X] T037 [US4] Adicionar tratamento de timeout: Cancelar processamento após timeout de 30s e retornar erro 504

### Integração e Cross-Cutting

- [X] T038 [US4] Adicionar integração com cache: Reusar AnalysisCache existente para resultados de vídeo com chave de cache baseada no hash do arquivo
- [X] T039 [US4] Adicionar limpeza LGPD: Garantir remoção de arquivos temporários em blocos try/finally com `shutil.rmtree(temp_dir, ignore_errors=True)`
- [X] T040 [US4] Adicionar logging estruturado: Usar structlog para tracking de correlation_id (sem dados sensíveis no log)
- [X] T041 [US4] Adicionar rate limiting: Aplicar rate limiting existente ao endpoint de vídeo para proteger quotas

### Testes da História de Usuário 4 (OPCIONAL - apenas se testes solicitados) ⚠️

- [X] T042 [P] [US4] Teste unitário VideoAnalysisService: Criar `tests/unit/services/test_video_analysis.py`
- [X] T043 [P] [US4] Teste de integração do endpoint: Criar `tests/integration/test_video_endpoint.py` com uploads de vídeo de teste
- [X] T044 [P] [US4] Testar campos obrigatórios: Verificar que `risco_violencia` e `risco_saude_mental` estão sempre presentes na resposta

**Ponto de Verificação**: Todas as histórias de usuário devem estar funcionalmente independentes

---

## Fase 7: História de Usuário 5 - Integração com Azure Vision (Prioridade: P3 - Pós-MVP)

**Objetivo**: Usar Azure Vision como fallback quando YOLOv8 não tem certeza

**Status**: Não implementar no MVP. Avaliar necessidade após testes em produção.

**⚠️ PULAR PARA MVP** - Esta história de usuário está explicitamente marcada como Pós-MVP

---

## Fase 8: Polimento e Preocupações Transversais

**Objetivo**: Melhorias que afetam múltiplas histórias de usuário

### Performance e Otimização

- [X] T045 [P] Otimizar inferência YOLOv8: Adicionar parâmetro imgsz=320 para inferência mais rápida em CPU no YOLOv8Service
- [ ] T046 [P] Adicionar processamento em batch: Processar múltiplos frames em batch quando possível no VideoProcessor
- [X] T047 Adicionar endpoint de formatos de vídeo: Criar `GET /analyze/video/formats` em `src/api/routes/video.py` retornando limites e formatos suportados

### Documentação e Deploy

- [X] T048 [P] Atualizar CLAUDE.md: Adicionar endpoint de vídeo ao status de implementação em `CLAUDE.md`
- [X] T049 [P] Atualizar README.md: Adicionar exemplos de análise de vídeo à documentação da API em `README.md`
- [X] T050 Testar build Docker: Verificar se `docker-compose build` funciona com ultralytics
- [X] T051 Testar execução Docker: Verificar se endpoint de vídeo funciona no container com `docker-compose up -d`

### Qualidade de Código

- [X] T052 [P] Executar linting: Executar `poetry run ruff check src/` e corrigir quaisquer problemas
- [X] T053 [P] Executar type checking: Executar `poetry run mypy src/` e corrigir quaisquer erros de tipo
- [X] T054 Executar testes: Executar `poetry run pytest tests/ -v` e garantir cobertura >70% (atingido: ~85%)

---

## Dependências e Ordem de Execução

### Dependências de Fase

- **Configuração (Fase 1)**: Sem dependências - pode começar imediatamente
- **Fundação (Fase 2)**: Depende da conclusão da Configuração - BLOQUEIA todas as histórias de usuário
- **Histórias de Usuário (Fase 3-7)**: Todas dependem da conclusão da Fase Fundação
  - Histórias podem então prosseguir em paralelo (se houver capacidade de equipe)
  - Ou sequencialmente em ordem de prioridade (P1 → P2 → P3)
- **Polimento (Fase Final)**: Depende de todas as histórias de usuário desejadas estarem completas

### Dependências entre Histórias de Usuário

- **História de Usuário 1 (P1)**: Pode começar após Fundação (Fase 2) - Sem dependências em outras histórias
- **História de Usuário 2 (P2)**: Pode começar após Fundação (Fase 2) - Pode integrar com US1 mas deve ser testável independentemente
- **História de Usuário 3 (P3)**: Pode começar após Fundação (Fase 2) - Pode integrar com US1/US2 mas deve ser testável independentemente
- **História de Usuário 4 (P1)**: Pode começar após Fundação (Fase 2) - Depende de componentes US1-US3 mas endpoint é testável independentemente
- **História de Usuário 5 (P3)**: PÓS-MVP - Pular para implementação inicial

### Dentro de Cada História de Usuário

- Testes (se incluídos) DEVEM ser escritos e FALHAR antes da implementação
- Models antes de services
- Services antes de endpoints
- Implementação core antes de integração
- História completa antes de prosseguir para próxima prioridade

### Oportunidades de Paralelismo

- **Fase 1**: T001-T005 podem ser executadas em sequência
- **Fase 2**: T006-T011 podem ser executadas em paralelo (serviços independentes)
- **Testes Fase 3**: T016-T017 podem ser executadas em paralelo com T012-T015
- **Testes Fase 4**: T023 pode ser executada em paralelo com T018-T022
- **Testes Fase 6**: T042-T044 podem ser executadas em paralelo após T031
- **Fase 8**: T045-T054 marcadas [P] podem ser executadas em paralelo

---

## Exemplo de Paralelismo: História de Usuário 1

```bash
# Iniciar todos os testes da História de Usuário 1 juntos (se testes solicitados):
Tarefa: "Teste unitário YOLOv8Service em tests/unit/services/test_yolo_service.py"
Tarefa: "Teste unitário VideoProcessor em tests/unit/services/test_video_processor.py"

# Iniciar todos os models da História de Usuário 1 juntos:
Tarefa: "Mapear classes COCO relevantes em src/services/yolo_service.py"
Tarefa: "Implementar filtragem por confiança em src/services/yolo_service.py"
```

---

## Estratégia de Implementação

### MVP Primeiro (Histórias de Usuário 1, 2, 4)

1. Completar Fase 1: Configuração
2. Completar Fase 2: Fundação (CRÍTICO - bloqueia todas as histórias)
3. Completar Fase 3: História de Usuário 1 (Instrumentos)
4. Completar Fase 4: História de Usuário 2 (Sangramento)
5. Completar Fase 6: História de Usuário 4 (Triagem - endpoint com campos obrigatórios)
6. **PARAR E VALIDAR**: Testar Histórias de Usuário 1, 2, 4 independentemente
7. Deploy/demo se estiver pronto

### Escopo Estendido (Adicionar História de Usuário 3)

8. Completar Fase 5: História de Usuário 3 (Linguagem Corporal)
9. Testar independentemente
10. Deploy/Demo

### Pós-MVP (História de Usuário 5)

11. Completar Fase 6: História de Usuário 5 (Azure Vision fallback) - apenas se necessário após testes em produção

### Entrega Incremental

1. Completar Configuração + Fundação → Fundação pronta
2. Adicionar História de Usuário 1 → Testar independentemente → Deploy/Demo (MVP - detecção básica de objetos)
3. Adicionar História de Usuário 2 → Testar independentemente → Deploy/Demo (MVP + detecção de sangramento)
4. Adicionar História de Usuário 4 → Testar independentemente → Deploy/Demo (MVP + campos obrigatórios de risco)
5. Adicionar História de Usuário 3 → Testar independentemente → Deploy/Demo (Estendido - análise de postura)
6. Cada história adiciona valor sem quebrar histórias anteriores

### Estratégia de Equipe Paralela

Com múltiplos desenvolvedores:

1. Equipe completa Configuração + Fundação juntos
2. Assim que Fundação estiver pronta:
   - Desenvolvedor A: História de Usuário 1 (detecção YOLO)
   - Desenvolvedor B: História de Usuário 2 (detecção de sangramento)
   - Desenvolvedor C: História de Usuário 4 (endpoint API)
3. Histórias completam e integram independentemente
4. Finalmente adicionar História de Usuário 3 (requer coordenação com US1/US2)

---

## Resumo de Contagem de Tarefas

| Fase | Tarefas | Descrição |
|------|---------|-----------|
| Fase 1 | 8 | Configuração e dependências (inclui versionamento) |
| Fase 2 | 6 | Infraestrutura fundacional |
| Fase 3 | 6 | US1: Instrumentos cirúrgicos |
| Fase 4 | 6 | US2: Sangramento anômalo |
| Fase 5 | 4 | US3: Linguagem corporal |
| Fase 6 | 16 | US4: Triagem (endpoint + testes) |
| Fase 8 | 10 | Polimento e transversal |
| **Total** | **56** | **(US5 pulada - Pós-MVP)** |

**Tarefas MVP**: 42 (Fases 1, 2, 3, 4, 6, 7 parcial)
**Tarefas Estendidas**: 4 (Fase 5 - US3)
**Tarefas Pós-MVP**: 0 (Fase 6 pulada)

---

## Notas

- Tarefas [P] = arquivos diferentes, sem dependências em tarefas incompletas
- Rótulo [História] mapeia tarefa para história de usuário específica para rastreabilidade
- Cada história de usuário deve ser completável e testável independentemente
- Verifique que testes falham antes de implementar
- Faça commit após cada tarefa ou grupo lógico
- Pare em qualquer ponto de verificação para validar história independentemente
- Evite: tarefas vagas, conflitos no mesmo arquivo, dependências entre histórias que quebram independência
