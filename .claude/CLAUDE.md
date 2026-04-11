# Configuração Claude Code - Tech Challenge Fase 4

## MCP Servers Configurados

Este projeto utiliza dois servidores MCP (Model Context Protocol):

### 1. Context7 MCP Server

O Context7 está configurado para fornecer acesso à documentação atualizada das bibliotecas utilizadas.

### 2. GitHub MCP Server

O GitHub MCP Server está configurado para acesso à API do GitHub diretamente pelo Claude.

Para usar, configure seu token:
```bash
# Crie o arquivo .env com seu token
cp .env.example .env
# Edite e adicione: GITHUB_TOKEN=ghp_seu_token_aqui
```

Veja [GITHUB_MCP.md](GITHUB_MCP.md) para instruções completas.

---

## Context7 MCP Server

### O que é Context7?

Context7 é um servidor MCP (Model Context Protocol) que indexa documentação de bibliotecas e frameworks, permitindo que o Claude acesse informações atualizadas sobre:
- APIs e métodos
- Melhores práticas
- Exemplos de código
- Changelogs

### Como Usar

Quando estiver trabalhando no código, você pode pedir ao Claude para consultar o Context7:

```
"Consulte o Context7 sobre: FastAPI dependency injection"
"Busque no Context7: Pydantic v2 field validators"
"Verifique no Context7: Azure SDK Python best practices"
```

### Bibliotecas Indexadas

O Context7 possui documentação atualizada para:
- **FastAPI** - Framework web async
- **Pydantic v2** - Validação de dados
- **Azure SDK Python** - Integração com Azure
- **pytest** - Framework de testes
- **Poetry** - Gerenciamento de dependências

### Comandos Úteis

```bash
# Atualizar índice do Context7
npx @upstash/context7-mcp@latest index

# Verificar status
npx @upstash/context7-mcp@latest status
```

### Exemplos de Uso

#### Exemplo 1: Consultar sobre FastAPI
```
Usuário: "Preciso criar um middleware no FastAPI para logging"
Claude: Consulta Context7 sobre FastAPI middleware pattern...
```

#### Exemplo 2: Consultar sobre Pydantic
```
Usuário: "Como validar campos opcionais no Pydantic v2?"
Claude: Consulta Context7 sobre Pydantic v2 optional fields...
```

#### Exemplo 3: Consultar sobre Azure
```
Usuário: "Qual o padrão singleton para Azure TextAnalyticsClient?"
Claude: Consulta Context7 sobre Azure SDK Python singleton pattern...
```

### Configuração do MCP

A configuração está em `.claude/settings.local.json`:

```json
{
  "mcpServers": {
    "context7": {
      "command": "npx",
      "args": ["-y", "@upstash/context7-mcp@latest"]
    }
  }
}
```

### Requisitos

- Node.js 18+ instalado
- Conexão com internet para atualizar índices

### Dicas

1. **Sempre consulte o Context7 antes de implementar** funcionalidades usando bibliotecas externas
2. **Use para validar padrões** - Context7 ajuda a seguir as melhores práticas oficiais
3. **Verifique compatibilidade** - Context7 informa sobre versões e breaking changes
4. **Economize tokens** - Context7 retorna informações precisas sem precisar ler toda a documentação

### Integração com Spec Kit

Quando usar `/speckit.implement`, o Context7 é automaticamente consultado para:
- Validar padrões de código
- Sugerir implementações seguindo as melhores práticas
- Verificar compatibilidade entre bibliotecas

### Documentação Oficial

- Context7: https://github.com/upstash/context7
- MCP Protocol: https://modelcontextprotocol.io
