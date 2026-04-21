---
name: Spec Kit - Processo Obrigatório
description: O projeto usa Spec Kit como processo de desenvolvimento. NUNCA pular etapas.
type: feedback
---

## Regra: Seguir o Spec Kit rigorosamente

Toda implementação DEVE seguir o processo do Spec Kit definido em `.specify/memory/constitution.md`:

1. **Especificar** → spec.md na pasta specs/XXX-feature/
2. **Planejar** → plan.md com abordagem técnica
3. **Taskificar** → tasks.md com tarefas executáveis
4. **Implementar** → Executar tasks em ordem
5. **Validar** → Rodar testes, lint, type check
6. **Documentar** → Atualizar README se necessário
7. **Auditar** → Usar `@speckit.clarify` para auditar código

**Why:** A Constitution define que Spec Kit é o processo oficial do projeto. Pular etapas resulta em código sem testes, sem documentação e sem alinhamento com a arquitetura planejada.

**How to apply:**
- NUNCA começar a implementar sem ler o spec.md completo da feature
- Sempre criar/validar plan.md antes de codificar
- Sempre criar tasks.md com checklist antes de implementar
- Só implementar depois de tasks.md criado e validado
- Casos "extremamente pontuais" são exceções raras (hotfix crítico, bug de produção)
- Para features novas: seguir rigorosamente 1→2→3→4→5→6→7
