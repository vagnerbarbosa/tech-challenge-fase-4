---
name: GitHub Tools Strategy
escription: Quando usar GitHub CLI vs GitHub MCP Server para interações com GitHub
type: feedback
originSessionId: 1ae1b377-6b61-4a01-ad6e-61e0f2454620
---
## Regra: Escolha a ferramenta mais eficiente para cada operação

Ao interagir com GitHub, avaliar o custo/benefício entre GitHub CLI (gh) e GitHub MCP Server.

**Why:** Cada ferramenta tem diferentes trade-offs de latência, token usage e capacidades. Usar a ferramenta errada resulta em respostas mais lentas ou operações mais caras.

**How to apply:**

### Use GitHub MCP Server quando:
- Precisa de operações ricas com contexto estruturado (listar PRs com filtros complexos)
- Necessita de múltiplas operações GitHub em sequência (MCP mantém sessão)
- Vai fazer queries GraphQL complexas
- Precisa de acesso a objetos aninhados (ex: PR + comments + reviews)
- Está em uma sessão longa onde o MCP já está "quente"

### Use GitHub CLI (gh) quando:
- Operações simples e diretas (ex: `gh pr view`, `gh pr checkout`)
- Necessita de saída formatada específica (ex: tabelas, JSON)
- Comandos que serão executados uma única vez (sem overhead de inicialização MCP)
- Operações de write (merge, push, create) onde CLI é mais confiável
- Quando precisa de interatividade (ex: `gh pr create` com prompts)
- Quando MCP não estiver disponível ou configurado

### Use API REST direta (curl) quando:
- Precisa de controle total sobre headers e parâmetros
- Operações pontuais simples (ex: verificar status de um PR específico)
- Scripts que precisam ser portáteis (sem dependências externas)

### Exemplos:

```
# BOM: Usar MCP para listar PRs com filtros
"Liste PRs abertos com label 'bug' ordenados por atualização"

# BOM: Usar CLI para checkout rápido
"Faça checkout do PR #27"
gh pr checkout 27

# BOM: Usar CLI para operações de write
"Merge o PR #27"
gh pr merge 27

# BOM: Usar curl para verificação simples
"Verifique se PR #27 está mergeable"
curl -s https://api.github.com/repos/owner/repo/pulls/27 | jq '.mergeable'
```

### Anti-padrões a evitar:
- ❌ Usar MCP para uma única operação simples (overhead de inicialização)
- ❌ Usar CLI para queries complexas que requerem múltiplas chamadas
- ❌ Tentar usar gh em scripts sem verificar se está instalado
- ❌ Usar API REST direta para operações que MCP/CLI fazem melhor
