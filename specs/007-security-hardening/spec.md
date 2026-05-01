# Feature Specification: Security Hardening 2026

**Feature Branch**: `007-security-hardening`  
**Created**: 2026-04-22  
**Status**: ✅ COMPLETED  
**Input**: User description: "Implementar hardening de segurança completo para API FastAPI de saúde, incluindo: autenticação API Key, rate limiting contra DDoS, validação de uploads com magic bytes, sanitização de logs LGPD-compliant, headers de segurança OWASP, proteção BOLA, e auditoria LGPD. Seguir OWASP API Top 10 2023/2026 e compliance LGPD para dados de saúde."

---

## Clarifications

### Session 2026-04-22
- **Q**: Qual o nível de autenticação necessário para o MVP?  
  **A**: API Key mínima para MVP, com estrutura para evoluir para OAuth2/JWT
- **Q**: Devemos implementar criptografia em repouso para dados sensíveis ou apenas em trânsito?  
  **A**: Criptografia em trânsito (TLS 1.3) obrigatória; em repouso para dados sensíveis (AES-256) quando possível
- **Q**: Qual o prazo para notificação de incidentes LGPD?  
  **A**: Implementar capacidade de notificação em até 72 horas (recomendado ANPD 2026)

---

## User Scenarios & Testing

### User Story 1 - Autenticação e Autorização Segura (Priority: P1)

Como sistema de saúde, quero garantir que apenas usuários autorizados acessem dados de pacientes para proteger a privacidade LGPD.

**Why this priority**: Autenticação é a primeira linha de defesa. OWASP API1 (Broken Object Level Authorization) e LGPD Art. 46 exigem controles robustos.

**Independent Test**: Endpoint `/health` com API Key retorna 401 sem chave válida; endpoints protegidos retornam 403 para acesso não autorizado.

**Acceptance Scenarios**:

1. **Given** requisição sem API Key, **When** acessar endpoint protegido, **Then** retorna HTTP 401 com mensagem genérica
2. **Given** API Key válida, **When** acessar recurso de outro usuário (BOLA), **Then** retorna HTTP 403 (proteção BOLA)
3. **Given** token expirado, **When** submeter requisição, **Then** retorna HTTP 401 com prompt para renovar
4. **Given** usuário sem permissão de admin, **When** tentar acessar endpoint admin, **Then** retorna HTTP 403

---

### User Story 2 - Validação de Uploads e Prevenção de Injeção (Priority: P1)

Como sistema, quero validar rigorosamente uploads de mídia (áudio/vídeo) para prevenir malware, path traversal e execução remota.

**Why this priority**: Uploads são vetor de ataque crítico (RCE, path traversal). OWASP API6 e LGPD Art. 46 exigem integridade dos dados.

**Independent Test**: Upload de arquivo malicioso é rejeitado; arquivo com path traversal no nome é sanitizado; tipo MIME verificado via magic bytes.

**Acceptance Scenarios**:

1. **Given** arquivo .exe renomeado para .mp3, **When** submetido, **Then** rejeitado após validação de magic bytes
2. **Given** arquivo com nome `../../../etc/passwd`, **When** submetido, **Then** nome sanitizado para nome seguro
3. **Given** arquivo maior que 50MB, **When** submetido, **Then** rejeitado antes de upload completo (streaming)
4. **Given** arquivo com conteúdo script embutido, **When** submetido, **Then** bloqueado por análise de conteúdo

---

### User Story 3 - Sanitização e Proteção de Dados Sensíveis (Priority: P1)

Como operador LGPD-compliant, quero garantir que dados pessoais e de saúde nunca sejam expostos em logs, erros ou responses.

**Why this priority**: LGPD Art. 46, Art. 50 e OWASP API3 (Excessive Data Exposure) exigem minimização e proteção de dados.

**Independent Test**: Logs não contêm patient_id real, Azure keys, ou conteúdo de mídia; erros 500 não expõem stack trace em produção.

**Acceptance Scenarios**:

1. **Given** erro de conexão Azure, **When** logado, **Then** não contém a key (mask: `****-****-****-KEY`)
2. **Given** exceção não tratada, **When** ocorrer em produção, **Then** retorna mensagem genérica (stack trace apenas em dev)
3. **Given** patient_id real no request, **When** logado, **Then** substituído por hash SHA256
4. **Given** resposta de análise, **When** retornada, **Then** contém apenas campos necessários (sem dados brutos de mídia)

---

### User Story 4 - Rate Limiting e Proteção contra DDoS (Priority: P1)

Como sistema, quero limitar requisições por IP/usuário para prevenir abuso, DDoS e credential stuffing.

**Why this priority**: OWASP API4 (Unrestricted Resource Consumption) e LGPD exigem disponibilidade e controle de acesso.

**Independent Test**: Após exceder limite de requisições, cliente recebe HTTP 429 com header Retry-After; limites diferentes para endpoints autenticados vs públicos.

**Acceptance Scenarios**:

1. **Given** 100 requisições/min de um IP, **When** limite é 60, **Then** requisições 61+ retornam 429
2. **Given** endpoint de login, **When** 5 tentativas falhas/min, **Then** IP bloqueado por 15 minutos
3. **Given** endpoint /analyze/multimodal, **When** processamento pesado, **Then** limite mais restritivo que /health
4. **Given** múltiplos IPs atacando, **When** detectado padrão, **Then** rate limit aplicado por bloco de IP

---

### User Story 5 - Headers de Segurança HTTP (Priority: P2)

Como sistema, quero incluir headers de segurança em todas as respostas HTTP para proteger contra XSS, clickjacking e sniffing.

**Why this priority**: OWASP API8 (Security Misconfiguration) - headers de segurança são defesa em profundidade básica.

**Independent Test**: Resposta de qualquer endpoint contém X-Content-Type-Options, X-Frame-Options, Strict-Transport-Security, CSP.

**Acceptance Scenarios**:

1. **Given** qualquer resposta, **When** recebida, **Then** inclui `X-Content-Type-Options: nosniff`
2. **Given** qualquer resposta, **When** recebida, **Then** inclui `X-Frame-Options: DENY`
3. **Given** qualquer resposta, **When** recebida, **Then** inclui `Strict-Transport-Security: max-age=31536000; includeSubDomains`
4. **Given** qualquer resposta, **When** recebida, **Then** inclui `Content-Security-Policy: default-src 'self'`

---

### User Story 6 - Auditoria e Logging de Segurança (Priority: P2)

Como auditor LGPD, quero logs estruturados de todos os acessos e modificações em dados de pacientes.

**Why this priority**: LGPD Art. 46, §3 exige logs de auditoria; Art. 48 exige notificação de incidentes.

**Independent Test**: Cada acesso a dados de paciente gera log estruturado com timestamp, IP, ação, resultado; logs são imutáveis.

**Acceptance Scenarios**:

1. **Given** acesso a dados de paciente, **When** realizado, **Then** log estruturado gerado (sem dados sensíveis)
2. **Given** tentativa de acesso não autorizado, **When** ocorrer, **Then** log de alerta de segurança gerado
3. **Given** falha de autenticação, **When** ocorrer, **Then** log com IP, timestamp e tipo de falha
4. **Given** incidente de segurança, **When** detectado, **Then** sistema pode gerar relatório para ANPD em 72h

---

### User Story 7 - CORS Restritivo (Priority: P2)

Como sistema, quero configurar CORS de forma restritiva para prevenir CSRF e ataques cross-origin.

**Why this priority**: OWASP API8 - CORS aberto é vulnerabilidade comum; LGPD exige controle de acesso.

**Independent Test**: Requisições de origens não permitidas são bloqueadas; apenas origens whitelist podem acessar.

**Acceptance Scenarios**:

1. **Given** requisição de origem `https://evil.com`, **When** submetida, **Then** bloqueada pelo CORS
2. **Given** requisição de origem `https://app-healthcare.com`, **When** submetida, **Then** permitida
3. **Given** requisição sem origin header, **When** submetida, **Then** tratada como não confiável
4. **Given** modo debug ativo, **When** CORS configurado, **Then** loga warning se `*` permitido

---

### Edge Cases

- **EC-001**: Sistema inicia sem variáveis de ambiente obrigatórias → falha rápida (fail secure) com mensagem clara
- **EC-002**: Processo crasha durante upload → arquivos temp são limpos automaticamente pelo sistema operacional
- **EC-003**: Key de API vazada → sistema pode revogar via hot-reload sem restart
- **EC-004**: Ataque de força bruta em lote → rate limiting por IP com cooldown progressivo
- **EC-005**: Requisição com payload malformado → validação Pydantic rejeita com erro 400 (não 500)

---

## Requirements

### Functional Requirements

#### Autenticação e Autorização
- **FR-001**: Sistema DEVE requerer API Key em todos os endpoints exceto `/health` (configurável)
- **FR-002**: Sistema DEVE validar BOLA (Broken Object Level Authorization) em acessos a recursos
- **FR-003**: Sistema DEVE implementar RBAC básico (admin, user, readonly)
- **FR-004**: Sistema DEVE permitir rotação de API Keys sem downtime

#### Validação e Sanitização
- **FR-005**: Sistema DEVE validar tipo MIME via magic bytes (não apenas extensão)
- **FR-006**: Sistema DEVE sanitizar filenames (remover path traversal, caracteres especiais)
- **FR-007**: Sistema DEVE validar tamanho de upload antes de processar (streaming)
- **FR-008**: Sistema DEVE bloquear arquivos executáveis (.exe, .sh, .bat, .cmd)

#### Proteção de Dados
- **FR-009**: Sistema DEVE mascarar secrets em logs (Azure keys, API keys)
- **FR-010**: Sistema DEVE hashear patient_id em logs (SHA256)
- **FR-011**: Sistema DEVE minimizar dados em responses (sem dados brutos de mídia)
- **FR-012**: Sistema DEVE anonimizar texto transcrito antes de logging

#### Rate Limiting e Throttling
- **FR-013**: Sistema DEVE implementar rate limiting por IP (60 req/min padrão)
- **FR-014**: Sistema DEVE implementar rate limiting por API Key (100 req/min padrão)
- **FR-015**: Sistema DEVE ter limites mais restritivos para endpoints de autenticação (5 req/min)
- **FR-016**: Sistema DEVE retornar HTTP 429 com header Retry-After quando limite excedido

#### Headers de Segurança
- **FR-017**: Sistema DEVE incluir `X-Content-Type-Options: nosniff` em todas respostas
- **FR-018**: Sistema DEVE incluir `X-Frame-Options: DENY` em todas respostas
- **FR-019**: Sistema DEVE incluir `Strict-Transport-Security` (HSTS) em produção
- **FR-020**: Sistema DEVE incluir `Content-Security-Policy` configurável
- **FR-021**: Sistema DEVE incluir `Referrer-Policy: strict-origin-when-cross-origin`
- **FR-022**: Sistema DEVE incluir `X-XSS-Protection: 1; mode=block`

#### CORS
- **FR-023**: Sistema DEVE configurar CORS com whitelist explícita (nunca `*` em produção)
- **FR-024**: Sistema DEVE logar warning se CORS permitir `*` em ambiente não-local
- **FR-025**: Sistema DEVE suportar múltiplas origens permitidas via configuração

#### Logging e Auditoria
- **FR-026**: Sistema DEVE logar todos os acessos a dados de pacientes (estruturado)
- **FR-027**: Sistema DEVE logar falhas de autenticação (IP, timestamp, motivo)
- **FR-028**: Sistema DEVE garantir imutabilidade de logs de auditoria
- **FR-029**: Sistema DEVE suportar exportação de logs para análise de incidentes LGPD

#### Criptografia
- **FR-030**: Sistema DEVE usar TLS 1.2+ (preferencialmente 1.3) em trânsito
- **FR-031**: Sistema DEVE usar AES-256 para criptografia em repouso de dados sensíveis
- **FR-032**: Sistema DEVE hashear dados sensíveis com SHA256 quando possível

#### Resiliência
- **FR-033**: Sistema DEVE implementar timeout em todas chamadas externas (30s padrão)
- **FR-034**: Sistema DEVE ocultar detalhes de erro em produção (mensagens genéricas)
- **FR-035**: Sistema DEVE implementar circuit breaker para serviços externos (Azure)

### Key Entities

- **SecurityMiddleware**: Middleware FastAPI que aplica headers, valida CORS, rate limiting
- **AuthValidator**: Validação de API Key e permissões RBAC
- **FileValidator**: Validação de uploads (MIME, tamanho, conteúdo)
- **LogSanitizer**: Sanitização de logs (mascaramento de secrets, hashing de IDs)
- **AuditLogger**: Logger estruturado para eventos de auditoria LGPD
- **RateLimiter**: Controle de taxa de requisições (token bucket)
- **BOLAProtector**: Proteção contra Broken Object Level Authorization

---

## Success Criteria

### Measurable Outcomes

- **SC-001**: Zero vulnerabilidades CRÍTICAS/ALTAS em security scan automatizado (Bandit, Safety)
- **SC-002**: Cobertura de 100% em testes de autenticação (unauthorized, forbidden, invalid key)
- **SC-003**: Rate limiting funciona: 100% de requisições após limite retornam 429
- **SC-004**: Headers de segurança presentes em 100% das respostas HTTP
- **SC-005**: Secrets nunca expostos: verificação via grep em logs de teste
- **SC-006**: BOLA protegido: tentativa de acesso a recurso de outro usuário retorna 403
- **SC-007**: Latência de segurança < 10ms overhead por requisição (middleware otimizado)
- **SC-008**: LGPD compliance: logs de auditoria exportáveis em formato estruturado

---

## Assumptions

- **A-001**: Projeto já possui estrutura FastAPI com middlewares configuráveis
- **A-002**: Stack Python 3.11+ com suporte a `functools.lru_cache` e async/await
- **A-003**: Redis disponível para rate limiting distribuído (fallback: memória local)
- **A-004**: `python-magic` pode ser adicionado para validação MIME (magic bytes)
- **A-005**: `python-jose` ou similar disponível para JWT se necessário
- **A-006**: Infraestrutura suporta TLS 1.2+ (nginx/Azure Front Door)
- **A-007**: Secrets gerenciados via variáveis de ambiente (nunca hardcoded)
- **A-008**: Ambiente de produção identificável via variável `ENVIRONMENT=production`
- **A-009**: Logs centralizados via structlog já configurado

---

## Vulnerabilidades Mitigadas (OWASP API Top 10 2023/2026)

| OWASP | Vulnerabilidade | Mitigação no Escopo |
|-------|----------------|---------------------|
| API1 | Broken Object Level Authorization | ✅ FR-002: BOLAProtector |
| API2 | Broken Authentication | ✅ FR-001: API Key required |
| API3 | Broken Object Property Level Authorization | ✅ FR-011: Data minimization |
| API4 | Unrestricted Resource Consumption | ✅ FR-013/014: Rate limiting |
| API5 | Broken Function Level Authorization | ✅ FR-003: RBAC básico |
| API6 | Unrestricted Access to Sensitive Business Flows | ✅ FR-015: Auth rate limits |
| API7 | Server-Side Request Forgery (SSRF) | ✅ FR-033: Timeouts, validação |
| API8 | Security Misconfiguration | ✅ FR-017/022: Security headers |
| API9 | Improper Inventory Management | ⚠️ Fora de escopo (API versioning) |
| API10 | Unsafe Consumption of APIs | ✅ FR-033: Circuit breaker |

---

## Requisitos LGPD Atendidos

| Artigo | Requisito | Implementação |
|--------|-----------|---------------|
| Art. 46 | Segurança (técnicas + administrativas) | ✅ Headers, criptografia, rate limiting |
| Art. 46, §1 | Boas práticas | ✅ OWASP, Privacy by Design |
| Art. 46, §2 | Privacy by Design | ✅ Minimização de dados, anonimização |
| Art. 46, §3 | Logs de auditoria | ✅ FR-026/028: AuditLogger |
| Art. 48 | Notificação de incidentes | ✅ FR-029: Exportação de logs |
| Art. 50 | Anonimização de dados | ✅ FR-010: Hash de patient_id |

---

## Technical References

- [OWASP API Security Top 10 2023](https://owasp.org/www-project-api-security/)
- [OWASP FastAPI Cheat Sheet](https://github.com/OWASP/CheatSheetSeries/blob/master/cheatsheets/FastAPI_Security_Cheat_Sheet.md)
- [LGPD Lei 13.709/2018](http://www.planalto.gov.br/ccivil_03/_ato2015-2018/2018/lei/l13709.htm)
- [ANPD Orientações 2026](https://www.gov.br/anpd/pt-br)
- [FastAPI Security Docs](https://fastapi.tiangolo.com/tutorial/security/)
- [NIST Cybersecurity Framework 2.0](https://www.nist.gov/cybersecurity-framework)

---

## Fontes de Pesquisa 2026

- [OWASP API Security Best Practices 2026](https://webcoderspeed.com/blog/scaling/api-security-2026)
- [FastAPI Security 2026 - Toxigon](https://toxigon.com/securing-fastapi-applications)
- [API Security Best Practices 2026](https://securebin.ai/blog/api-security-best-practices-2026/)
- [HIPAA-Compliant Python APIs](https://www.accountablehq.com/post/fastapi-healthcare-security-configuration-hipaa-ready-setup-guide)
- [LGPD Compliance Técnico](https://middlebrick.com/regulations/lgpd)
- [LGPD API Requirements](https://ancora1.com/noticias/api-lgpd-e-mensagens-em-2026-o-que-empresas-podem-ou-no-fazer-na-comunicao-digital)
