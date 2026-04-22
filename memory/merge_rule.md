---
name: Regra de Merge — Nunca mergear direto na main
description: SEMPRE abrir PR antes de mergear na main. Merge direto é proibido, mesmo que todos os checks estejam passando localmente.
type: feedback
---

## Regra: Nunca mergear direto na main

**NUNCA** executar `git merge` diretamente na branch `main` localmente ou via script. SEMPRE abrir uma Pull Request (PR) e aguardar aprovação/revisão antes de mergear.

### O que é proibido
- ❌ `git checkout main && git merge feature-branch`
- ❌ `git push origin main` com commits de feature
- ❌ Qualquer merge direto sem PR aberto

### O que é obrigatório
- ✅ Abrir PR via GitHub (web ou CLI: `gh pr create`)
- ✅ Aguardar todos os checks da CI passarem
- ✅ Aguardar aprovação de code review quando houver reviewers
- ✅ Mergear apenas via interface do GitHub (merge button)

### Por que esta regra existe
A branch `main` é a fonte da verdade. Merge direto:
- Circunda a CI/CD e checks automatizados
- Evita code review obrigatório
- Pode quebrar produção sem registro de aprovação
- Perde o histórico de discussão e decisões

### Como aplicar
1. Finalizar implementação na branch de feature
2. `git push -u origin feature-branch`
3. Abrir PR: `gh pr create --base main --head feature-branch` (ou via web)
4. Aguardar checks passarem
5. Mergear via GitHub UI (squash/merge/rebase conforme padrão do projeto)
6. Só então deletar a branch de feature

### Se merge direto acontecer por engano
1. **Reverter imediatamente**: `git revert -m 1 HEAD --no-edit`
2. **Recriar a branch de feature**: `git branch feature-branch ORIGINAL_MERGE_COMMIT`
3. **Abrir PR corretamente**
4. **Registrar o incidente** na memória do projeto
