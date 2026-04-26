---
name: MCP Auto-load
escription: Configuração para carregar MCPs e variáveis automaticamente no início das sessões
type: reference
---

## Hooks Configurados

O arquivo `.claude/settings.local.json` possui um hook `SessionStart` que executa automaticamente no início de cada sessão:

```json
"hooks": {
  "SessionStart": [
    {
      "matcher": "",
      "hooks": [
        {
          "type": "command",
          "command": "export GITHUB_TOKEN=\"$(gh auth token 2>/dev/null || cat ~/.github-token 2>/dev/null || echo '')\"",
          "statusMessage": "Carregando GITHUB_TOKEN..."
        }
      ]
    }
  ]
}
```

## O que isso faz

1. **Exporta GITHUB_TOKEN** automaticamente no início de cada sessão
2. Tenta obter o token via `gh auth token` (GitHub CLI)
3. Fallback para arquivo `~/.github-token` se existir
4. O MCP GitHub agora está sempre autenticado

## MCPs Configurados

- **github**: `@modelcontextprotocol/server-github`
- **context7**: `@upstash/context7-mcp@latest`

Ambos são carregados automaticamente via `.mcp.json` e ativados via `enabledMcpjsonServers`.
