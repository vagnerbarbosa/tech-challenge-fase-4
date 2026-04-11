# Constitution - Tech Challenge Fase 4

**Versão**: 1.0
**Data**: 2026-04-11
**Projeto**: Tech Challenge Fase 4 - API Multimodal para Saúde da Mulher

---

## Propósito

Este documento define os princípios, restrições e padrões que guiam o desenvolvimento do projeto. Serve como referência para tomada de decisões e revisão de código.

---

## Princípios Fundamentais

### 1. LGPD First
- **Nunca** armazenar dados pessoais identificáveis
- **Sempre** anonimizar patient_id com hash
- **Sempre** deletar arquivos de mídia após processamento
- **Nunca** logar conteúdo sensível

### 2. Azure Free Tier Protection
- **Nunca** exceder quotas do Azure Free Tier
- **Sempre** implementar rate limiting e hard stop
- **Sempre** monitorar uso em health check
- **Nunca** deixar serviço exposto sem proteção

### 3. Campos Obrigatórios
- **TODAS** as respostas de análise DEVEM incluir:
  - `risco_violencia`: [baixo, medio, alto]
  - `risco_saude_mental`: [baixo, medio, alto]

### 4. Qualidade de Código
- Type hints obrigatórios em todas as funções públicas
- Ruff para linting (line length: 88)
- mypy em modo strict
- Testes > 70% cobertura

### 5. Documentação
- Código em **inglês** (variáveis, funções, classes)
- Documentação em **português** (contexto brasileiro)
- Commits em português (conventional commits)
- PRs em português

---

## Restrições Técnicas

### Obrigatório (MUST HAVE)
- Python 3.11+
- FastAPI + Uvicorn
- Poetry para dependências
- Docker + Docker Compose
- Azure AI Services (Text Analytics, Speech, Vision)
- pytest para testes
- Deploy Azure App Service Free Tier

### Proibido (MUST NOT)
- Expor secrets Azure em código
- Armazenar dados pessoais sem anonimização
- Exceder quotas Azure Free Tier
- Logar conteúdo de arquivos de mídia
- Processar sem consentimento explícito

---

## Decisões de Arquitetura

### Aprovadas ✅
- Async/await para I/O
- Dependency injection com FastAPI Depends()
- Late fusion para combinação multimodal
- Azure Blob Storage para arquivos temporários
- Redis para cache (opcional)

### Rejeitadas ❌
- Early fusion (complexidade excessiva)
- Modelos locais (requer GPU, custo)
- Frontend web (fora de escopo)
- Treinamento customizado (fora de escopo)

---

## Checklist de Review

Antes de considerar uma feature completa:

- [ ] Código passa em `ruff check .`
- [ ] Código passa em `mypy src/`
- [ ] Testes unitários implementados
- [ ] Testes de integração implementados
- [ ] Cobertura > 70%
- [ ] Campos obrigatórios presentes em responses
- [ ] Validação de entrada implementada
- [ ] Rate limiting implementado (se usar Azure)
- [ ] Logging estruturado (sem dados sensíveis)
- [ ] Documentação atualizada

---

## Processo de Desenvolvimento

1. **Especificar**: Criar spec.md na pasta specs/XXX-feature/
2. **Planejar**: Criar plan.md com abordagem técnica
3. **Taskificar**: Criar tasks.md com tarefas executáveis
4. **Implementar**: Executar tasks em ordem
5. **Validar**: Rodar testes, lint, type check
6. **Documentar**: Atualizar README se necessário

---

## Contato e Responsabilidades

- **Autores**: Grupo 27
  - Adriel Santos ([@AdrielCandido](https://github.com/AdrielCandido))
  - Leticia Nepomuceno ([@LeticiaNepomuceno](https://github.com/LeticiaNepomuceno))
  - Lucas Silva ([@lucfsilva](https://github.com/lucfsilva))
  - Vagner Barbosa ([@vagnerbarbosa](https://github.com/vagnerbarbosa))
- **Projeto**: FIAP/Alura - AI para Devs
- **Fase**: 4 (Multimodal AI)
- **Repositório**: vagnerbarbosa/tech-challenge-fase-4
