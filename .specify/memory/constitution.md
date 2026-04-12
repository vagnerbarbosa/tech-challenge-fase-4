# Tech Challenge Fase 4 Constitution

## Core Principles

### I. LGPD Compliance (NON-NEGOTIABLE)
Toda implementação deve garantir conformidade com a Lei Geral de Proteção de Dados (LGPD):
- **Anonimização**: Patient IDs devem ser hasheados (SHA256) antes de uso em logs ou filenames
- **Consentimento**: Dados só são processados com consentimento explícito (quando aplicável)
- **Minimização**: Coletar apenas dados necessários para a análise
- **Temporariedade**: Arquivos temporários são removidos imediatamente após processamento (try/finally)
- **Nunca logar**: Conteúdo de mídia (áudio, vídeo) ou texto identificável não deve ser logado

### II. Azure Free Tier Protection
Proteção rigorosa contra exceder limites do Azure Free Tier:
- **Rate Limiting**: QuotaManager com persistência para tracking diário/mensal
- **Hard Limits**: Requisições são rejeitadas antes de consumir Azure quando quota excedida
- **Health Check**: Endpoint `/health` expõe quotas restantes
- **Mock Mode**: Funciona sem credenciais Azure para desenvolvimento
- **Limites Atuais**:
  - Text Analytics: 160 requests/dia (5.000/mês)
  - Speech Services: 10 minutos/dia (300/mês)
  - Computer Vision: 160 requests/dia (5.000/mês)

### III. Test Coverage >70% (TDD Preferred)
Qualidade de código através de testes comprehensivos:
- **Unit Tests**: Todos os services e utilities devem ter testes unitários
- **Integration Tests**: Endpoints devem ter testes de integração
- **Coverage**: Mínimo 70% de cobertura (report via pytest-cov)
- **Linting**: Ruff (line length: 88) deve passar sem erros
- **Type Check**: mypy em modo strict para código novo

### IV. Container-First
Toda funcionalidade deve funcionar em containers Docker:
- **Multi-stage Build**: Dockerfile otimizado para produção
- **Non-root User**: Containers rodam como usuário não-privilegiado
- **Health Checks**: Implementados no Dockerfile e docker-compose
- **FFmpeg/Dependências**: Todas as dependências sistema embarcadas no container
- **Docker Test**: Script `scripts/test-docker.sh` para validação

### V. Documentação em Português
Contexto brasileiro (FIAP/Alura) requer documentação localizada:
- **README**: Em português, com exemplos de uso
- **Specs**: Toda especificação em português
- **Commits**: Conventional commits em português
- **Comentários de Código**: Em inglês (padrão Python)
- **PRs**: Título e descrição em português obrigatório

### VI. Security-First
Hardening de segurança em todas as camadas:
- **Secrets**: Nunca commitar secrets (usar .env)
- **Validação**: Magic numbers para validação de arquivos (não só extensão)
- **Input Sanitization**: Todos os inputs validados antes de processamento
- **Error Handling**: Nunca expor detalhes internos em mensagens de erro
- **CORS/HTTPS**: Configuração segura para produção

### VII. Multimodal Architecture
Arquitetura preparada para processamento de múltiplas modalidades:
- **Independência**: Cada modalidade (texto, áudio, vídeo) pode funcionar isoladamente
- **Composição**: Endpoint `/analyze/multimodal` combina resultados
- **Extensibilidade**: Nova modalidade não requer mudanças nas existentes
- **Fallback**: Quando uma modalidade falha, outras continuam funcionando

## Additional Constraints

### Technology Stack (Locked)
- **Core**: Python 3.11+, FastAPI, Pydantic v2
- **Package Manager**: Poetry (pyproject.toml)
- **Azure**: azure-ai-textanalytics, azure-cognitiveservices-speech, azure-ai-vision
- **Audio/Video**: librosa, ultralytics (YOLOv8), opencv-python
- **Database**: SQLite (dev) / Azure SQL (prod)
- **Cache**: Redis (optional)

### API Standards
- **REST**: Endpoints seguem padrão RESTful
- **OpenAPI**: Documentação automática via FastAPI
- **Versioning**: URL path (`/v1/...`) quando necessário
- **Response Format**: JSON consistente com `risco_violencia` e `risco_saude_mental` obrigatórios

### Data Model Standards
- **Schemas**: Pydantic models em `src/models/schemas.py`
- **Validation**: Field validators para regras de negócio
- **Documentation**: docstrings em todas as classes públicas

## Development Workflow

### Branch Strategy
- **Main**: `main` - código de produção
- **Features**: `NNN-feature-name` - especs do Spec Kit
- **PRs**: Requer review antes de merge

### Quality Gates
1. **Pre-commit**: Ruff check passando
2. **Tests**: pytest com coverage >70%
3. **Type Check**: mypy sem erros
4. **Docker**: Build e testes em container funcionando

### Definition of Done
- [ ] Código implementado seguindo princípios acima
- [ ] Testes unitários cobrindo casos principais
- [ ] Testes de integração para endpoints
- [ ] Documentação atualizada (README, CLAUDE.md)
- [ ] Docker build funcionando
- [ ] Linting e type check passando
- [ ] Spec.md atualizado se necessário

## Governance

Esta Constitution é a fonte da verdade para decisões arquiteturais do projeto. Em caso de conflito:
1. Constitution > Spec > Implementation
2. Alterações requerem documentação e aprovação
3. Novos princípios são adicionados via PR com justificativa

**Version**: 1.0  
**Ratified**: 2026-04-12  
**Last Amended**: 2026-04-12
