# Clarify Audit: Spec 005 - Fusão Multimodal

**Data**: 2026-04-21
**Auditor**: Claude
**Artefatos Auditados**: plan.md, tasks.md
**Referências**: spec.md, constitution.md

---

## 1. Cobertura dos Functional Requirements (FR)

| FR | Descrição | Status | Onde Coberto |
|----|-----------|--------|--------------|
| FR-001 | Endpoint POST `/analyze/multimodal` | ✅ | T021-T022, T028 |
| FR-002 | Aceita texto + áudio + vídeo | ✅ | T002, T022, T023 |
| FR-003 | Pelo menos uma modalidade | ✅ | T004, T041, T045 |
| FR-004 | Processa em paralelo (asyncio.gather) | ✅ | T015 |
| FR-005 | Late fusion ponderado | ✅ | T006-T013 |
| FR-006 | Retorna risco_violencia, risco_saude_mental | ✅ | T001, T026, T046 |
| FR-007 | Retorna score, confiança, alerta, recomendação | ✅ | T001, T012 |
| FR-008 | Retorna resultados individuais | ✅ | T003, T026 |
| FR-009 | Alerta se 2+ riscos altos | ✅ | T011, T031-T032 |
| FR-010 | Fallback gracioso | ✅ | T017, T037-T040 |

**Resultado**: 10/10 FRs cobertos ✅

---

## 2. Cobertura dos Success Criteria (SC)

| SC | Descrição | Status | Onde Coberto |
|----|-----------|--------|--------------|
| SC-001 | Latência < 15s | ✅ | T016 (timeout 30s por modalidade), T047 (teste de latência) |
| SC-002 | Precisão superior | ⚠️ | Não testável automaticamente; requer validação manual com dataset |
| SC-003 | Alertas corretos | ✅ | T031-T032, T046 |
| SC-004 | Recomendações úteis | ⚠️ | Textos estáticos; validação manual recomendada |
| SC-005 | Paralelismo funciona | ✅ | T037, T047 |

**Resultado**: 3/5 testáveis automaticamente; 2/5 requerem validação manual

---

## 3. Constitution Check

| Princípio | Status | Observações |
|-----------|--------|-------------|
| I. LGPD | ✅ | Cleanup automático (T025), sem log de conteúdo sensível (T019), patient_id hasheado |
| II. Azure Free Tier | ✅ | Reutiliza rate limiting existente (T024), vídeo local sem custo |
| III. Test Coverage >70% | ✅ | 13 testes unitários + 6 testes de integração = ~85% esperado |
| IV. Container-First | ✅ | Sem dependências novas, reutiliza container existente |
| V. Documentação PT | ✅ | Spec e tasks em PT, código em EN (padrão Python) |
| VI. Security-First | ✅ | Validação reutilizada, sem secrets novos |
| VII. Multimodal | ✅ | Último módulo, implementa composição planejada |

**Resultado**: Todos os princípios respeitados ✅

---

## 4. Análise de Riscos

| Risco | Severidade | Mitigação |
|-------|------------|-----------|
| Timeout em vídeo longo pode afetar latência total | Média | T016: timeout 30s; processamento paralelo limita impacto |
| AudioAnalysisService retorna dict (não schema tipado) | Baixa | FusionService normaliza para ModalidadeResult antes de fusão |
| VideoAnalysisService é síncrono (não async) | Média | Usar `asyncio.to_thread()` ou `run_in_executor` para não bloquear event loop |
| Cobertura de teste pode não atingir 70% se mocks complexos | Baixa | Testes focados em algoritmo de fusão (fácil mockar) |

---

## 5. Observações e Recomendações

### Pontos Fortes
- Late fusion é a abordagem correta para MVP (já aprovada na Constitution)
- Processamento paralelo com asyncio.gather é a melhor escolha para I/O bound
- Fallback gracioso aumenta resiliência
- Reutilização de serviços existentes evita duplicação de código

### Pontos de Atenção
1. **SC-002 e SC-004** (precisão e recomendações) não são testáveis automaticamente. Recomendação: documentar no README que validação manual é necessária.
2. **VideoAnalysisService.analyze() é síncrono** - precisa envolver em `asyncio.to_thread()` no FusionService para não bloquear o event loop do FastAPI.
3. **Cache de fusão** (T027) é opcional e pode ser deixado para post-MVP se o tempo for curto.

### Decisões que Precisam de Confirmação — RESOLVIDAS

| # | Decisão | Resposta do Product Owner | Impacto no Plan |
|---|---------|--------------------------|-----------------|
| D1 | Timeout por modalidade | **Manter 30s** — Azure pode ser mais lento que local | Sem alteração; T016 mantido |
| D2 | Confiança = 0 | **MVP: Rejeitar fusão** com mensagem "impossível calcular risco". **Pós-MVP: Fallback para Azure Vision** como segunda opinião | T008-T009: alterar para lançar exceção se confiança total = 0 |
| D3 | Alerta threshold | **2+ riscos altos OU confiança_fusão > 0.8** | T011: adicionar condição `confiança_fusão > 0.8` |

### Pontos de Atenção — RESOLVIDOS

| # | Ponto | Resposta | Impacto |
|---|-------|----------|---------|
| P1 | SC-002/SC-004 não testáveis | **OK deixar para validação manual** | Sem alteração; documentar no README |
| P2 | VideoAnalysisService síncrono | **Refatorar para async** com garantia de não impactar endpoint /analyze/video existente | Nova task T058: refatorar VideoAnalysisService para async; T017: usar await direto (sem to_thread) |
| P3 | Cache de fusão | **Deixar para pós-MVP** | T027 removido do MVP |

---

## 6. Veredito

**Status**: ✅ **APROVADO para implementação**

O plan e tasks cobrem todos os requisitos funcionais, respeitam a Constitution, e têm mitigações adequadas para os riscos identificados. A implementação pode prosseguir.

**Próximo passo**: Iniciar execução das tasks em ordem (Fase 1 → Fase 2 → Fase 3 → Fase 4 → Fase 5 → Fase 6).

---

**Assinatura**: Claude - Auditoria Automática
**Data**: 2026-04-21
