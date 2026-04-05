# Especificação do Produto

## 1. Objetivo (Do Documento Oficial)

**"Realizar a análise e fusão de diferentes tipos de dados médicos específicos da saúde da mulher — incluindo texto, áudio e vídeo."**

### Opções Selecionadas:

1. ✅ **Detectar precocemente riscos em saúde materna e ginecológica**
2. ✅ **Identificar sinais de violência doméstica ou abuso**
4. ✅ **Utilizar serviços em nuvem** (Azure Free Tier)

---

## 2. Resumo Executivo

Sistema **multimodal** que processa **texto, áudio e vídeo** para identificar precocemente:
- Sinais de **violência doméstica**
- Riscos emocionais/psicológicos em **gestantes**
- Indicadores de **saúde mental feminina**

### Público-alvo:
- Profissionais de saúde (médicos, enfermeiros)
- Instituições de saúde
- Equipes de atenção à mulher

---

## 3. Problema

### Contexto:
- Violência doméstica muitas vezes não é relatada explicitamente
- Sinais de risco emocional podem ser sutis em consultas
- Profissionais de saúde não têm ferramentas para detectar padrões em múltiplas modalidades
- Dados médicos estão dispersos em texto, áudio e imagem

### Impacto:
- Casos de violência são subnotificados
- Riscos à saúde materna são identificados tardiamente
- Gestantes em situação de vulnerabilidade não recebem apoio adequado

---

## 4. Solução Proposta

API REST **multimodal** integrada com **Azure AI Services** (free tier) que:

1. **Processa texto**: Análise de sentimento, extração de padrões de violência
2. **Processa áudio**: Transcrição + análise de entonação, pausas, voz tremida
3. **Processa imagem**: Análise de expressões faciais, sinais visuais
4. **Realiza fusão**: Combina resultados das 3 modalidades para identificar riscos

---

## 5. Requisitos Funcionais

### RF01 - Análise de Texto
**Como** profissional de saúde
**Quero** submeter textos (prontuários, diários)
**Para** identificar sinais de violência ou risco emocional

**Critérios de Aceite:**
- [ ] Endpoint POST `/analyze/text`
- [ ] Aceita texto livre em português
- [ ] Retorna: sentimento, score, risco_violencia, risco_saude_mental
- [ ] Identifica palavras-chave indicativas
- [ ] Usa Azure Text Analytics (free tier: 5k requests/mês)

**Exemplo Input:**
```json
{
  "texto": "Estou me sentindo muito ansiosa...",
  "tipo": "diario"
}
```

**Exemplo Output:**
```json
{
  "sentimento": "negativo",
  "score": -0.85,
  "risco_violencia": "alto",
  "risco_saude_mental": "alto",
  "palavras_chave": ["ansiosa", "medo", "casa"]
}
```

### RF02 - Análise de Áudio
**Como** profissional de saúde
**Quero** submeter gravações de consultas
**Para** transcrever e analisar padrões de fala

**Critérios de Aceite:**
- [ ] Endpoint POST `/analyze/audio`
- [ ] Aceita arquivos de áudio (WAV, MP3, OGG)
- [ ] Retorna obrigatoriamente: **risco_violencia**, **risco_saude_mental**
- [ ] Também retorna: transcrição, sentimento, entonação, pausas_suspeitas, voz_tremida
- [ ] Detecta voz tremida ou hesitante
- [ ] Usa Azure Speech Services (free tier: 5h/mês)

**Exemplo Input:**
- Arquivo `consulta.wav`
- Tamanho máximo: 50MB

**Exemplo Output:**
```json
{
  "transcricao": "Doutor, eu não sei se posso contar...",
  "sentimento": "negativo",
  "entonação": "hesitante",
  "voz_tremida": true,
  "pausas_suspeitas": 3,
  "risco_violencia": "alto",
  "risco_saude_mental": "medio"
}
```

### RF03 - Análise de Imagem/Vídeo
**Como** profissional de saúde
**Quero** submeter fotos ou vídeos de consultas
**Para** analisar expressões faciais e sinais visuais

**Critérios de Aceite:**
- [ ] Endpoint POST `/analyze/image`
- [ ] Aceita imagens (JPEG, PNG) e vídeos curtos (MP4, max 30s)
- [ ] Para vídeos: extrair frames automaticamente (1 frame a cada 5s)
- [ ] Analisar frames com Azure AI Vision
- [ ] Retorna obrigatoriamente: **risco_violencia**, **risco_saude_mental**
- [ ] Também retorna: emoção_principal, expressoes, sinais_alertas
- [ ] Usa Azure AI Vision (free tier: 5k transactions/mês)

**Nota Técnica:** Azure AI Vision (free tier) só aceita imagens. Para vídeos:
1. Receber arquivo de vídeo (MP4, max 30s, max 50MB)
2. Extrair frames automaticamente (FFmpeg ou OpenCV)
3. Analisar frames como imagens
4. Combinar resultados dos frames

**Exemplo Input:**
- Arquivo `foto_consulta.jpg`

**Exemplo Output:**
```json
{
  "emoção_principal": "tristeza",
  "confiança": 0.89,
  "expressoes": ["evitando_olho", "expressao_tensa"],
  "sinais_alertas": ["marca_rosto"],
  "risco_violencia": "medio",
  "risco_saude_mental": "alto"
}
```

### RF04 - Análise Multimodal (Fusão)
**Como** profissional de saúde
**Quero** submeter texto + áudio + imagem juntos
**Para** ter uma análise combinada e mais precisa

**Critérios de Aceite:**
- [ ] Endpoint POST `/analyze/multimodal`
- [ ] Aceita os 3 tipos de dados simultaneamente
- [ ] Realiza fusão de features (late fusion)
- [ ] Retorna obrigatoriamente: **risco_violencia**, **risco_saude_mental** (calculados na fusão)
- [ ] Também retorna: score combinado, alerta (boolean), recomendação
- [ ] Confiança baseada na concordância entre modalidades

**Exemplo Output:**
```json
{
  "fusao": {
    "risco_violencia": "alto",
    "confiança": 0.92,
    "alerta": true
  },
  "texto": { "risco": "medio", "confiança": 0.75 },
  "audio": { "risco": "alto", "confiança": 0.88 },
  "imagem": { "risco": "medio", "confiança": 0.70 },
  "recomendacao": "Encaminhar para equipe multidisciplinar"
}
```

### RF05 - Health Check
**Como** operador da API
**Quero** verificar status da aplicação
**Para** garantir disponibilidade

**Critérios de Aceite:**
- [ ] Endpoint GET `/health`
- [ ] Retorna: status, versão, serviços_azure_disponiveis
- [ ] Verifica quota de serviços Azure (se possível)

---

## 6. Requisitos Não-Funcionais

| ID | Requisito | Métrica | Prioridade |
|----|-----------|---------|------------|
| RNF01 | Latência texto | < 2s | Must |
| RNF02 | Latência áudio | < 10s (arquivo 1min) | Must |
| RNF03 | Latência imagem | < 5s | Must |
| RNF04 | Disponibilidade | ≥ 99% | Must |
| RNF05 | Segurança | LGPD compliant | Must |
| RNF06 | Anonimização | Sem dados identificáveis | Must |
| RNF07 | Campos obrigatórios | risco_violencia e risco_saude_mental em todos endpoints | Must |
| RNF08 | Azure Free Tier | Dentro dos limites | Must |

---

## 7. Regras de Negócio

### 7.1 Consentimento Obrigatório
- **TODOS** os dados de áudio/vídeo REQUEREM consentimento explícito
- Armazenar hash do consentimento vinculado ao registro
- Sem consentimento → processamento não autorizado

### 7.2 Campos Obrigatórios em Todas as Respostas
**Todos os endpoints de análise DEVEM retornar obrigatoriamente:**
- `risco_violencia`: enum [baixo, medio, alto]
- `risco_saude_mental`: enum [baixo, medio, alto]

**Justificativa:** Consistência para o consumidor da API e padronização de alertas.

### 7.3 Anonimização
- Nunca armazenar: nome, CPF, endereço, telefone
- Usar `patient_id` hash gerado internamente
- Logs contêm apenas metadados (tamanho arquivo, timestamp)

### 7.3 Limites Azure Free Tier
- Text Analytics: 5k requests/mês
- Speech Services: 5h áudio/mês
- Computer Vision: 5k transactions/mês
- Implementar rate limiting e cache

### 7.4 Alertas
- Risco "alto" em qualquer modalidade → alerta imediato
- Risco "alto" em 2+ modalidades → alerta crítico
- Sistema é ferramenta de apoio, não substitui julgamento profissional

### 7.5 Privacidade
- Dados criptografados em trânsito (TLS 1.3)
- Dados armazenados criptografados (Azure Storage)
- Retenção máxima: 30 dias (configurável)

---

## 8. Escopo do MVP

### Incluído (Obrigatório):
- [ ] Análise de texto (Azure Text Analytics)
- [ ] Análise de áudio (Azure Speech Services)
- [ ] Análise de imagem (Azure AI Vision)
- [ ] Fusão multimodal (combinação de 3)
- [ ] Health check
- [ ] Docker + Docker Compose
- [ ] Testes > 70% cobertura
- [ ] README + vídeo

### Opcional (Se houver tempo):
- [ ] Dashboard de resultados
- [ ] Histórico de análises
- [ ] Notificações (email/SMS)
- [ ] API Key authentication
- [ ] Cache Redis

### Fora de Escopo:
- [ ] Treinamento de modelos customizados
- [ ] Interface web (frontend)
- [ ] Aplicativo mobile
- [ ] Integração com prontuários eletrônicos (HIS)
- [ ] Deploy em produção Azure (fora do free tier)

---

## 9. Métricas de Sucesso

| Métrica | Meta |
|---------|------|
| Precisão detecção | > 80% (validação manual) |
| Latência média | < 5s |
| Uso Azure | < 80% dos limites free tier |
| Cobertura testes | > 70% |
| Uptime | > 99% |
| Satisfação usuário | > 4/5 (demo) |

---

## 10. Riscos e Mitigação

| Risco | Probabilidade | Impacto | Mitigação |
|-------|--------------|---------|-----------|
| Exceder quota Azure | Média | Alto | Monitoramento, cache, rate limit |
| Falsa detecção | Média | Alto | Validação manual, confiança > 0.8 |
| Vazamento dados | Baixa | Crítico | Criptografia, anonimização |
| Latência alta | Média | Médio | Processamento assíncrono |
| API Azure indisponível | Baixa | Alto | Fallback para modelos locais |

---

## 11. Glossário

- **Multimodal**: Combinação de texto, áudio e imagem
- **Azure AI Services**: Serviços de AI da Microsoft
- **Late Fusion**: Combinação de resultados após processamento individual
- **Free Tier**: Nível gratuito de serviços cloud
- **LGPD**: Lei Geral de Proteção de Dados (Brasil)
- **Anonimização**: Remoção de dados identificáveis
