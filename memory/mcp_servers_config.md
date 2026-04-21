---
name: MCP Servers Configuration
description: Configuração e uso dos MCP Servers (GitHub e Context7)
type: reference
originSessionId: 1ae1b377-6b61-4a01-ad6e-61e0f2454620
---
## MCP Servers Configurados

### 1. GitHub MCP Server

**Comando:** `npx -y @modelcontextprotocol/server-github`

**Token:** Configurado em `env.GITHUB_PERSONAL_ACCESS_TOKEN`

**Uso:**
- Listar PRs, issues, branches
- Criar comentários, reviews
- Buscar código no repositório
- Operações GitHub ricas com contexto estruturado

**Quando usar:**
- Consultas complexas que retornam muitos dados
- Operações que precisam de sessão mantida
- Queries GraphQL

### 2. Context7 MCP Server

**Comando:** `npx -y @upstash/context7-mcp@latest`

**Uso:**
- Buscar documentação atualizada de bibliotecas
- Obter exemplos de código
- Verificar melhores práticas
- Validar padrões de implementação

**Bibliotecas indexadas:**
- FastAPI (framework web)
- Pydantic v2 (validação de dados)
- Azure SDK Python (integração Azure)
- pytest (testes)
- Poetry (gerenciamento de dependências)

## Hook de Implementação

O hook `beforeImplement` está configurado para **consultar automaticamente o Context7** antes de implementar qualquer funcionalidade.

**Buscar no Context7:**
1. FastAPI 0.115+ lifespan and dependency injection patterns
2. Pydantic v2 field validation and serialization
3. YOLOv8 Ultralytics 8.3+ detection optimization
4. Python 3.12 typing improvements and generics
5. Azure SDK Python async best practices 2025-2026
6. OpenCV video processing patterns
7. pytest-asyncio testing patterns

## Configuração Técnica

Arquivo: `.claude/settings.local.json`

```json
{
  "mcpServers": {
    "github": {
      "command": "npx",
      "args": ["-y", "@modelcontextprotocol/server-github"],
      "env": {
        "GITHUB_PERSONAL_ACCESS_TOKEN": "${GITHUB_TOKEN}"
      }
    },
    "context7": {
      "command": "npx",
      "args": ["-y", "@upstash/context7-mcp@latest"]
    }
  },
  "hooks": {
    "beforeImplement": "ANTES de implementar qualquer funcionalidade, consulte o Context7 MCP Server..."
  }
}
```

## Troubleshooting

**Se MCP não funcionar:**
1. Verificar se Node.js está disponível: `node --version`
2. Carregar NVM: `export NVM_DIR="$HOME/.nvm" && . "$NVM_DIR/nvm.sh"`
3. Verificar configuração no settings.local.json

**Para atualizar documentação Context7:**
```bash
npx @upstash/context7-mcp@latest index
```
