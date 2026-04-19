# Feature Specification: Análise de Vídeo com YOLOv8 para Detecção de Riscos Visuais

**Feature Branch**: `011-video-analysis-yolov8`  
**Created**: 2026-04-19  
**Status**: Draft  
**Input**: User description: "Implementar análise de vídeo usando YOLOv8 para detectar sinais visuais de risco em consultas de telemedicina"

## User Scenarios & Testing *(mandatory)*

### User Story 1 - Upload e Análise de Vídeo de Consulta (Priority: P1)

Como profissional de saúde, quero fazer upload de vídeos de consultas de telemedicina para que o sistema analise automaticamente sinais visuais de risco em saúde da mulher.

**Why this priority**: Esta é a funcionalidade core da feature - sem ela, não há valor entregue. Permite detectar sinais visuais que podem indicar riscos de violência doméstica ou problemas de saúde mental.

**Independent Test**: Pode ser testado enviando um vídeo de consulta para o endpoint `/analyze/video` e verificando se o sistema retorna análise com detecção de objetos e riscos identificados.

**Acceptance Scenarios**:

1. **Given** um vídeo de consulta médica em formato MP4, **When** o profissional faz upload via API, **Then** o sistema processa o vídeo e retorna análise com objetos detectados e nível de risco avaliado
2. **Given** um vídeo contendo sinais visuais de agitação (movimentos rápidos), **When** processado pelo sistema, **Then** o sistema identifica alto nível de agitação e reporta como possível indicador de ansiedade
3. **Given** um vídeo sem conteúdo relevante, **When** processado, **Then** o sistema retorna "nenhum sinal detectado" sem erro

---

### User Story 2 - Detecção de Objetos de Risco (Priority: P2)

Como profissional de saúde, quero que o sistema identifique objetos potencialmente relacionados a riscos (como instrumentos perigosos, sinais de constrangimento) durante a análise do vídeo.

**Why this priority**: Adiciona valor à análise ao identificar elementos visuais específicos que podem indicar situações de risco, aumentando a precisão da avaliação.

**Independent Test**: Pode ser testado fornecendo vídeos com objetos específicos e verificando se o YOLOv8 os detecta corretamente.

**Acceptance Scenarios**:

1. **Given** um vídeo contendo objetos potencialmente perigosos visíveis, **When** analisado pelo YOLOv8, **Then** o sistema lista os objetos detectados com nível de confiança
2. **Given** um vídeo com múltiplos frames, **When** processado frame a frame, **Then** o sistema agrega as detecções e apresenta resultado consolidado

---

### User Story 3 - Análise de Linguagem Corporal (Priority: P3)

Como profissional de saúde, quero que o sistema analise a linguagem corporal da paciente (postura, gestos) para identificar sinais de nervosismo ou constrangimento.

**Why this priority**: Complementa a detecção de objetos com análise comportamental, fornecendo indicadores adicionais para avaliação de riscos psicossociais.

**Independent Test**: Pode ser testado com vídeos demonstrando diferentes posturas e verificando se o sistema classifica corretamente comportamentos.

**Acceptance Scenarios**:

1. **Given** um vídeo onde a paciente demonstra postura recolhida e gestos defensivos, **When** analisado, **Then** o sistema reporta possíveis indicadores de constrangimento
2. **Given** um vídeo com movimentos normais de consulta, **When** analisado, **Then** o sistema reporta comportamento dentro de parâmetros normais

---

### Edge Cases

- **Vídeo corrompido ou formato inválido**: Sistema deve retornar erro 400 com mensagem clara sobre formato não suportado
- **Vídeo muito longo (> 10 minutos)**: Sistema deve processar amostras representativas ou retornar erro de limite excedido
- **Resolução muito baixa**: Sistema deve informar que a qualidade pode afetar a precisão da detecção
- **Ausência de pessoas no vídeo**: Sistema deve retornar "nenhuma pessoa detectada" sem erro
- **Múltiplas pessoas no vídeo**: Sistema deve focar na pessoa principal (maior área) ou analisar todas
- **Falha no modelo YOLOv8**: Sistema deve fallback para modo de análise simplificada ou retornar erro apropriado

## Requirements *(mandatory)*

### Functional Requirements

- **FR-001**: O sistema DEVE aceitar upload de vídeos nos formatos MP4, AVI e MOV via endpoint REST
- **FR-002**: O sistema DEVE extrair frames do vídeo a intervalos regulares (ex: a cada 1 segundo) para análise
- **FR-003**: O sistema DEVE utilizar YOLOv8 para detecção de objetos em cada frame extraído
- **FR-004**: O sistema DEVE classificar objetos detectados usando classes padrão COCO do YOLOv8 (pessoa, faca, tesoura, garfo, etc.), mapeando automaticamente objetos potencialmente perigosos para níveis de risco (alto, médio, baixo)
- **FR-005**: O sistema DEVE analisar movimentação e postura para identificar sinais de agitação ou nervosismo
- **FR-006**: O sistema DEVE retornar resultado com: objetos detectados, nível de risco geral, confiança da análise, e tempo de processamento
- **FR-007**: O sistema DEVE respeitar limite de tamanho de arquivo (máximo 100MB por vídeo)
- **FR-008**: O sistema DEVE processar vídeo de forma assíncrona se durar mais que 30 segundos
- **FR-009**: O sistema DEVE incluir os campos obrigatórios `risco_violencia` e `risco_saude_mental` em TODAS as respostas
- **FR-010**: O sistema DEVE remover arquivos temporários após processamento (LGPD compliance)

### Key Entities

- **VideoAnalysisRequest**: Representa uma requisição de análise de vídeo contendo arquivo, paciente_id (opcional), e metadados
- **DetectedObject**: Objeto detectado pelo YOLOv8 com atributos: classe, confiança, bounding box, timestamp no vídeo
- **VideoAnalysisResult**: Resultado completo da análise com objetos detectados, níveis de risco, metadados de processamento
- **FrameAnalysis**: Análise individual de um frame extraído, contendo detecções e métricas

## Success Criteria *(mandatory)*

### Measurable Outcomes

- **SC-001**: O sistema deve processar vídeos de até 2 minutos em menos de 30 segundos (em hardware local/container)
- **SC-002**: A detecção de objetos deve atingir precisão mínima de 70% em cenários de teste conhecidos
- **SC-003**: O endpoint deve aceitar arquivos de até 100MB sem timeout
- **SC-004**: 100% das respostas devem conter os campos obrigatórios `risco_violencia` e `risco_saude_mental`
- **SC-005**: O sistema deve suportar simultaneamente pelo menos 5 análises de vídeo sem degradação significativa
- **SC-006**: O consumo de memória durante processamento não deve exceder 2GB por vídeo analisado

## Clarifications

### Session 2026-04-19

- **Q**: Quais categorias específicas de objetos o YOLOv8 deve priorizar na detecção de risco? → **A**: Usar classes padrão COCO do YOLOv8 (pessoa, faca, tesoura, etc.) - mais simples, classes pré-treinadas disponíveis

## Assumptions

- O modelo YOLOv8 será executado localmente no container (custo zero, sem chamadas à Azure)
- Vídeos de entrada serão gravados em consultas de telemedicina com iluminação e ângulo adequados
- A análise é complementar às modalidades de texto e áudio já existentes no sistema
- Será utilizado YOLOv8 pré-treinado (não será treinamento customizado nesta fase)
- O processamento será síncrono para vídeos curtos (< 30s) e assíncrono para vídeos mais longos
- Os campos de risco seguirão o mesmo padrão das análises de texto e áudio já implementadas
