# Histórias de Usuário

## 1. US01 - Análise de Texto

**Como** profissional de saúde (médico/enfermeiro)
**Quero** analisar textos de prontuários ou diários
**Para** identificar sinais de violência doméstica ou risco emocional

**Critérios de Aceite:**
- [ ] Endpoint POST `/analyze/text` disponível
- [ ] Aceita texto em português (mínimo 10 caracteres, máximo 5000)
- [ ] Retorna sentimento (positivo/negativo/neutro) com score (-1 a 1)
- [ ] Identifica risco_violencia (baixo/medio/alto)
- [ ] Identifica risco_saude_mental (baixo/medio/alto)
- [ ] Extrai palavras-chave indicativas
- [ ] Tempo de resposta < 2s

**Exemplo Request:**
```json
{
  "texto": "Estou me sentindo muito ansiosa e tenho medo quando ele chega em casa",
  "tipo": "diario",
  "patient_id": "uuid-anonimo"
}
```

**Exemplo Response:**
```json
{
  "sentimento": "negativo",
  "score": -0.85,
  "risco_violencia": "alto",
  "risco_saude_mental": "alto",
  "palavras_chave": ["ansiosa", "medo", "casa"],
  "indicadores": ["expressao_medo", "contexto_familiar"]
}
```

**Pontuação**: 5 pontos

---

## 2. US02 - Análise de Áudio

**Como** profissional de saúde
**Quero** submeter gravações de consultas
**Para** transcrever e analisar padrões de fala que indiquen risco

**Critérios de Aceite:**
- [ ] Endpoint POST `/analyze/audio` disponível
- [ ] Aceita arquivos WAV, MP3, OGG (máximo 50MB)
- [ ] Retorna transcrição em português
- [ ] Detecta sentimento na fala (análise da transcrição)
- [ ] Identifica entonação (normal/hesitante/tremida)
- [ ] Conta pausas suspeitas (silêncios longos)
- [ ] Detecta voz_tremida (boolean)
- [ ] Tempo de resposta proporcional ao tamanho do áudio (< 10s para 1min)

**Notas Técnicas:**
- Usar Azure Speech Services (free tier: 5h/mês)
- Implementar upload em chunks para arquivos grandes
- Limpar arquivos após processamento (LGPD)

**Pontuação**: 8 pontos

---

## 3. US03 - Análise de Imagem

**Como** profissional de saúde
**Quero** submeter fotos de consultas
**Para** analisar expressões faciais e sinais visuais de risco

**Critérios de Aceite:**
- [ ] Endpoint POST `/analyze/image` disponível
- [ ] Aceita imagens JPEG, PNG (máximo 20MB)
- [ ] Retorna emoção principal (alegria/tristeza/medo/raiva/neutro)
- [ ] Retorna confiança da análise (0-1)
- [ ] Identifica expressões faciais específicas
- [ ] Detecta possíveis sinais de alerta (marcas, hematomas)
- [ ] Tempo de resposta < 5s

**Exemplo Response:**
```json
{
  "emoção_principal": "tristeza",
  "confiança": 0.89,
  "expressoes": ["evitando_olho", "expressao_tensa"],
  "sinais_alertas": [],
  "risco": "medio"
}
```

**Pontuação**: 8 pontos

---

## 4. US04 - Análise Multimodal (Fusão)

**Como** profissional de saúde
**Quero** submeter texto + áudio + imagem simultaneamente
**Para** ter uma análise combinada mais precisa

**Critérios de Aceite:**
- [ ] Endpoint POST `/analyze/multimodal` disponível
- [ ] Aceita texto + arquivo de áudio + arquivo de imagem
- [ ] Processa cada modalidade individualmente
- [ ] Realiza fusão late (combinação de resultados)
- [ ] Retorna score combinado de risco
- [ ] Gera alerta se risco for "alto" em 2+ modalidades
- [ ] Fornece recomendação de ação

**Exemplo Response:**
```json
{
  "fusao": {
    "risco_violencia": "alto",
    "risco_saude_mental": "alto",
    "confiança": 0.92,
    "alerta": true
  },
  "texto": { "risco": "medio", "confiança": 0.75 },
  "audio": { "risco": "alto", "confiança": 0.88 },
  "imagem": { "risco": "medio", "confiança": 0.70 },
  "recomendacao": "Encaminhar para equipe multidisciplinar urgentemente",
  "patient_id": "uuid-anonimo"
}
```

**Pontuação**: 13 pontos

---

## 5. US05 - Health Check

**Como** operador DevOps
**Quero** verificar o status da API
**Para** garantir que está funcionando corretamente

**Critérios de Aceite:**
- [ ] Endpoint GET `/health` sem autenticação
- [ ] Retorna status (healthy/degraded/unhealthy)
- [ ] Retorna versão da API
- [ ] Verifica conectividade com serviços Azure
- [ ] Retorna quota disponível (se possível obter da API Azure)
- [ ] HTTP 200 se OK, HTTP 503 se crítico

**Exemplo Response:**
```json
{
  "status": "healthy",
  "version": "1.0.0",
  "timestamp": "2026-04-05T14:30:00Z",
  "servicos_azure": {
    "text_analytics": "disponível",
    "speech": "disponível",
    "azure_ai_vision": "disponível"
  },
  "quota_restante": {
    "text_requests": "4800/5000",
    "audio_minutes": "180/300",
    "vision_requests": "4500/5000"
  }
}
```

**Pontuação**: 3 pontos

---

## 6. US06 - Documentação API

**Como** desenvolvedor integrando a API
**Quero** acessar documentação interativa
**Para** entender como usar sem ler o código

**Critérios de Aceite:**
- [ ] Swagger UI em `/docs`
- [ ] Schemas de request/response documentados
- [ ] Descrições em português
- [ ] Exemplos de requisições
- [ ] ReDoc em `/redoc` (opcional)

**Pontuação**: 2 pontos

---

## 7. US07 - Containerização

**Como** desenvolvedor
**Quero** rodar a aplicação em containers
**Para** ambiente consistente entre desenvolvimento e produção

**Critérios de Aceite:**
- [ ] Dockerfile funcional (multi-stage)
- [ ] docker-compose.yml com app e dependências
- [ ] `docker-compose up -d` inicia aplicação sem erros
- [ ] Hot reload funciona em desenvolvimento
- [ ] Non-root user no container

**Pontuação**: 5 pontos

---

## 8. US08 - Testes Automatizados

**Como** desenvolvedor
**Quero** ter testes automatizados
**Para** garantir qualidade e evitar regressões

**Critérios de Aceite:**
- [ ] Testes unitários para serviços de análise
- [ ] Testes de integração para endpoints
- [ ] Testes de carga (Locust)
- [ ] Cobertura de código > 70%
- [ ] CI executa testes automaticamente (opcional)

**Pontuação**: 8 pontos

---

## 9. US09 - Rate Limiting (Proteção Azure)

**Como** operador da API
**Quero** limitar requisições por minuto
**Para** não exceder os limites do Azure Free Tier

**Critérios de Aceite:**
- [ ] Rate limit por endpoint e usuário
- [ ] Limite configurável (default: 10 req/min)
- [ ] Resposta 429 quando excedido
- [ ] Header `X-RateLimit-Remaining` informado

**Pontuação**: 3 pontos

---

## 10. US10 - Logging Estruturado

**Como** desenvolvedor debugando
**Quero** logs em formato estruturado
**Para** rastrear requisições e diagnosticar problemas

**Critérios de Aceite:**
- [ ] Logs em JSON
- [ ] Correlation ID em todas as requisições
- [ ] Campos: timestamp, level, message, correlation_id, endpoint
- [ ] Logs no stdout (Docker-friendly)
- [ ] Nunca logar dados sensíveis ou conteúdo de arquivos

**Pontuação**: 3 pontos

---

## Backlog - Pós-MVP

### US11 - Dashboard Web
**Como** gestor de saúde
**Quero** ver dashboard com estatísticas
**Para** entender padrões de risco

### US12 - Notificações
**Como** profissional de saúde
**Quero** receber alertas por email
**Para** ser notificado de casos urgentes

### US13 - Histórico
**Como** médico
**Quero** ver histórico de análises de uma paciente
**Para** acompanhar evolução

### US14 - Exportação
**Como** administrador
**Quero** exportar relatórios em PDF
**Para** documentação oficial

---

## Priorização

| Rank | História | Pontos | Motivo |
|------|----------|--------|--------|
| 1 | US04 (Multimodal) | 13 | Core - fusão de 3 modalidades |
| 2 | US02 (Áudio) | 8 | Obrigatório - requisito do projeto |
| 3 | US03 (Imagem) | 8 | Obrigatório - requisito do projeto |
| 4 | US08 (Testes) | 8 | Requisito de avaliação |
| 5 | US01 (Texto) | 5 | Obrigatório - requisito do projeto |
| 6 | US07 (Docker) | 5 | Requisito de avaliação |
| 7 | US05 (Health) | 3 | Observabilidade básica |
| 8 | US10 (Logging) | 3 | Debug e monitoramento |
| 9 | US09 (Rate Limit) | 3 | Proteção Azure Free Tier |
| 10 | US06 (Docs) | 2 | UX desenvolvedor |

**Total MVP**: 58 pontos

---

## Dependências

```
US05 (Health) ← US07 (Docker)
US04 (Multimodal) → requer US01 + US02 + US03
US08 (Testes) → requer todos os endpoints
```
