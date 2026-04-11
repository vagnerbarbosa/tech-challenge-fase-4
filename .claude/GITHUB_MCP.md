# GitHub MCP Server Configuration

O GitHub MCP Server está configurado neste projeto para permitir que o Claude acesse a API do GitHub diretamente.

---

## O que é GitHub MCP?

O Model Context Protocol (MCP) é um protocolo da Anthropic que permite integração entre Claude e ferramentas externas. O GitHub MCP Server fornece acesso à API do GitHub, permitindo:

- Criar e gerenciar issues
- Criar e revisar pull requests
- Buscar código no repositório
- Gerenciar branches
- Verificar status de CI/CD
- Listar commits e releases

## Configuração Atual

O servidor MCP está configurado em `.claude/settings.local.json`:

```json
{
  "mcpServers": {
    "github": {
      "command": "npx",
      "args": ["-y", "@modelcontextprotocol/server-github"],
      "env": {
        "GITHUB_PERSONAL_ACCESS_TOKEN": "${GITHUB_TOKEN}"
      }
    }
  }
}
```

---

## Configuração

> **⚠️ IMPORTANTE**: O GitHub MCP é uma ferramenta do **ambiente de desenvolvimento** (Claude Code), não faz parte da aplicação. O token é configurado como variável de ambiente do sistema, não no `.env` do projeto.

### 1. Gerar Token de Acesso

1. Acesse: https://github.com/settings/tokens
2. Clique em **Generate new token (classic)**
3. Dê um nome descritivo (ex: "Claude MCP Token")
4. Selecione as seguintes permissões:
   - ✅ `repo` (acesso completo aos repositórios)
   - ✅ `read:org` (ler organizações)
   - ✅ `read:user` (ler informações do usuário)
   - ✅ `workflow` (acesso a workflows/actions)
5. Clique em **Generate token**
6. **Copie o token imediatamente** (não será mostrado novamente)

### 2. Configurar como Variável de Ambiente

Configure no seu sistema operacional:

```bash
# Windows (PowerShell)
$env:GITHUB_TOKEN="ghp_seu_token_aqui"

# Windows (CMD)
set GITHUB_TOKEN=ghp_seu_token_aqui

# Linux/macOS
export GITHUB_TOKEN=ghp_seu_token_aqui
```

Ou configure permanentemente no Windows:
1. Painel de Controle → Sistema → Configurações Avançadas do Sistema
2. Variáveis de Ambiente → Novo
3. Nome: `GITHUB_TOKEN`
4. Valor: seu token

---

## Configuração no Claude Code

O servidor MCP já está configurado em `.claude/settings.local.json`:

```json
{
  "mcpServers": {
    "github": {
      "command": "npx",
      "args": [
        "-y",
        "@anthropic/mcp-github-server@latest"
      ],
      "env": {
        "GITHUB_PERSONAL_ACCESS_TOKEN": "${GITHUB_TOKEN}"
      }
    }
  }
}
```

---

## Exemplos de Uso

### Issues

```
"Crie uma issue para implementar o endpoint de análise de áudio"
"Liste todas as issues abertas do projeto"
"Feche a issue #10 com o comentário 'Resolvido na PR #15'"
```

### Pull Requests

```
"Crie uma PR para a branch feature/text-analysis"
"Mostre o status das PRs abertas"
"Revise a PR #20 e deixe um comentário sobre os testes"
```

### Repositório

```
"Busque código relacionado a 'risk_detector'"
"Liste os últimos 10 commits"
"Mostre o diff entre main e a branch atual"
```

### Branches

```
"Liste todas as branches"
"Crie uma branch feature/audio-endpoint a partir da main"
"Delete a branch antiga"
```

---

## Segurança

⚠️ **IMPORTANTE**:

- **Nunca commite seu token** no repositório
- Use `.env` (já está no `.gitignore`)
- Regenere o token se houver suspeita de vazamento
- Tokens com permissão `repo` têm acesso total aos seus repositórios
- Para repositórios da organização, use token com escopo da organização

---

## Troubleshooting

### Erro: "GITHUB_TOKEN não definido"

```bash
# Verifique se a variável está definida
echo $GITHUB_TOKEN  # Linux/macOS
$env:GITHUB_TOKEN    # Windows PowerShell
```

### Erro: "Bad credentials"

- O token pode ter expirado
- Regenere em https://github.com/settings/tokens

### Erro: "Resource not accessible by personal access token"

- O token não tem permissões suficientes
- Adicione as permissões `repo` ao token

---

## Referências

- [GitHub MCP Server](https://github.com/anthropics/mcp-github-server)
- [MCP Documentation](https://modelcontextprotocol.io)
- [GitHub Tokens Documentation](https://docs.github.com/en/authentication/keeping-your-account-and-data-secure/creating-a-personal-access-token)

---

**Configurado em**: 2026-04-11
**Última atualização**: 2026-04-11
