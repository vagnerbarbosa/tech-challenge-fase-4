# Memory Index

- [GitHub Tools Strategy](github_tools_strategy.md) — Quando usar MCP vs CLI vs API REST
- [MCP Servers Config](mcp_servers_config.md) — Configuração dos MCP Servers (GitHub e Context7)
- [Spec Kit Processo](spec_kit_processo.md) — Processo obrigatório de desenvolvimento
- [Regra de Merge](merge_rule.md) — NUNCA mergear direto na main; sempre abrir PR

## Status das Ferramentas

### ✅ Configurados e Funcionais

| Ferramenta | Versão | Localização | Uso |
|------------|--------|-------------|-----|
| **Node.js** | v22.22.2 | via NVM (~/.nvm) | Runtime para MCPs |
| **npm/npx** | 10.9.7 | via NVM | Package manager |
| **GitHub CLI (gh)** | 2.44.1 | ~/.local/bin/gh | Operações GitHub |
| **GitHub MCP** | latest | npx @modelcontextprotocol/server-github | API GitHub rica |
| **Context7 MCP** | latest | npx @upstash/context7-mcp@latest | Documentação de libs |

### 🔧 Arquivos de Configuração

- `.claude/settings.local.json` — MCP servers e hooks configurados
- Token GitHub configurado no MCP server
- Hook `beforeImplement` para consultar Context7 antes de implementar

### 📝 Como Usar

**GitHub CLI:**
```bash
export PATH="$HOME/.local/bin:$PATH"
gh pr view 27
```

**MCP Servers (automático via Claude Code):**
- Disponíveis quando usando Claude Code com settings configurados
- GitHub MCP: operações ricas com repositórios, PRs, issues
- Context7 MCP: documentação atualizada de FastAPI, Pydantic, Azure SDK, etc.
