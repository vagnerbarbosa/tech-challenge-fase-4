# Análise de Serviços Cloud - Free Tier

## Opções Selecionadas pelo Projeto
1. ✅ Detectar precocemente riscos em saúde materna e ginecológica
2. ✅ Identificar sinais de violência doméstica ou abuso
3. ❌ Monitorar bem-estar psicológico feminino
4. ✅ Utilizar serviços em nuvem (FREE TIER)
5. ❌ Aplicar técnicas de detecção de anomalias em tempo real

---

## Comparação de Provedores Cloud - Free Tier

### 1. AWS (Amazon Web Services)

#### Free Tier Inclui (12 meses + Sempre Grátis):
| Serviço | Free Tier | Uso no Projeto |
|---------|-----------|----------------|
| EC2 | 750h/mês (t2.micro) | API Server |
| S3 | 5GB + 20k GET requests | Armazenamento áudio/vídeo |
| RDS PostgreSQL | 750h/mês | Banco de dados |
| Lambda | 1M requests/mês | Processamento serverless |
| Transcribe | 60 minutos/mês | Speech-to-text (limitado) |
| Rekognition | 5k requests/mês | Análise de imagem/vídeo |
| Comprehend | 5k requests/mês | NLP/Sentiment Analysis |
| SageMaker | 250h/mês (studio) | ML (complexo) |

#### ✅ Vantagens:
- Transcribe (speech-to-text) bom para áudio
- Rekognition para análise de vídeo
- Comprehend para NLP
- Documentação extensa em português

#### ❌ Desvantagens:
- Transcribe limitado a 60 min/mês (pouco para MVP)
- Curva de aprendizado alta
- Cobrança fácil de ultrapassar limites

---

### 2. Google Cloud Platform (GCP)

#### Free Tier Inclui (12 meses + Sempre Grátis):
| Serviço | Free Tier | Uso no Projeto |
|---------|-----------|----------------|
| Compute Engine | 1 f1-micro instance | API Server |
| Cloud Storage | 5GB + 1GB egress | Armazenamento |
| Cloud SQL | Não tem free tier direto | Banco (precisa alternativa) |
| Cloud Run | 2M requests/mês | API Server (melhor opção) |
| Speech-to-Text | 60 minutos/mês | Transcrição áudio |
| Vision AI | 1k unidades/mês | Análise de imagem |
| Natural Language | 5k unidades/mês | Sentiment Analysis |
| Firebase | 1GB storage + 10k auth | Banco NoSQL + Auth |

#### ✅ Vantagens:
- **Cloud Run**: Melhor opção para API (serverless, escala automática)
- Speech-to-Text qualidade muito boa
- Vision API para análise facial/emocional
- Firebase gratuito é excelente para startups

#### ❌ Desvantagens:
- Speech-to-text limitado a 60 min/mês
- Cloud SQL não tem free tier

---

### 3. Azure (Microsoft)

#### Free Tier Inclui (12 meses + Sempre Grátis):
| Serviço | Free Tier | Uso no Projeto |
|---------|-----------|----------------|
| Virtual Machines | 750h B1s | API Server |
| Blob Storage | 5GB + 10k operations | Armazenamento |
| SQL Database | 250GB + 15 DBs | Banco de dados |
| Functions | 1M execuções/mês | Serverless functions |
| Speech Services | 5 horas/mês (Standard) | Speech-to-text (MAIOR LIMITE!) |
| Computer Vision | 5k transactions/mês | Análise de imagem + frames de vídeo |
| Text Analytics | 5k requests/mês | NLP/Sentiment |
| Language Service | 5k requests/mês | NLP avançado |

#### ✅ VANTAGENS (RECOMENDADO):
- **Speech Services: 5 horas/mês** (vs 60 min dos outros!) - MAIOR LIMITE
- Text Analytics para sentiment analysis
- Computer Vision para análise de vídeo
- SQL Database com 250GB (muito espaço)
- Azure Functions serverless
- Integração fácil com Python SDK

#### ❌ Desvantagens:
- Menos popular para tutoriais em português

---

### 4. Outros Provedores

#### IBM Cloud:
- Lite plan limitado
- Watson Speech-to-Text: 500 min/mês (BOM!)
- Mas menos serviços integrados

#### Oracle Cloud:
- Free tier generoso (2 ARM instances sempre gratuitas)
- Mas menos serviços de AI/ML

#### Heroku:
- Free tier foi removido em 2022
- Não recomendado

---

## 🏆 RECOMENDAÇÃO: Azure

### Por que Azure é a melhor escolha para este projeto:

1. **Speech-to-Text: 5 horas/mês** vs 1 hora (AWS/GCP)
   - Essencial para processar consultas de áudio
   - 5x mais capacidade que concorrentes

2. **Serviços completos**:
   - Speech Services (áudio)
   - Computer Vision (vídeo)
   - Text Analytics (NLP/sentimento)
   - Tudo integrado

3. **Banco de dados generoso**:
   - SQL Database 250GB
   - Suficiente para logs e metadados

4. **Custo zero para MVP**:
   - Todos os serviços necessários no free tier
   - Fácil de monitorar uso

---

## Arquitetura com Azure (Free Tier)

```
┌─────────────────────────────────────────────────────────────┐
│                         AZURE CLOUD                          │
├─────────────────────────────────────────────────────────────┤
│                                                              │
│  ┌──────────────┐   ┌────────────────┐   ┌──────────────┐ │
│  │  Azure       │   │  Azure Speech  │   │  Azure       │ │
│  │  App Service │   │  Services      │   │  Computer    │ │
│  │  (API REST)  │   │  (5h/mês free) │   │  Vision      │ │
│  └──────┬───────┘   └────────────────┘   └──────────────┘ │
│         │                                                     │
│  ┌──────▼──────┐   ┌────────────────┐                      │
│  │  Azure      │   │  Azure Text    │                      │
│  │  SQL        │   │  Analytics     │                      │
│  │  Database   │   │  (Sentiment)   │                      │
│  └─────────────┘   └────────────────┘                      │
│                                                              │
│  ┌────────────────────────────────────┐                    │
│  │  Azure Blob Storage (5GB free)     │                    │
│  │  - Áudios das consultas            │                    │
│  │  - Vídeos/análises                 │                    │
│  │  - Logs                            │                    │
│  └────────────────────────────────────┘                    │
│                                                              │
└─────────────────────────────────────────────────────────────┘
```

---

## Alternativa: Multi-Cloud (Híbrida)

Se 5h/mês de Azure não for suficiente, estratégia híbrida:

| Tipo de Dado | Serviço | Free Tier |
|--------------|---------|-----------|
| **Texto** | Azure Text Analytics | 5k requests/mês |
| **Áudio** | AWS Transcribe (backup) | 60 min/mês |
| **Vídeo** | Google Vision API | 1k requests/mês |
| **API** | Azure App Service | 750h/mês |
| **Banco** | Azure SQL | 250GB |

**Custo total: $0** (distribuindo carga entre provedores)

---

## Configuração Azure para Projeto

### Serviços Necessários:

```yaml
# azure-services.yaml
recursos:
  - nome: "diabetes-api-app"
    tipo: "App Service"
    tier: "Free (F1)"
    uso: "Hospedar API FastAPI"
    limites: "1GB RAM, 60 min CPU/dia"

  - nome: "diabetes-speech"
    tipo: "Speech Services"
    tier: "Free (F0)"
    uso: "Transcrever consultas de áudio"
    limites: "5 horas áudio/mês"

  - nome: "diabetes-text"
    tipo: "Text Analytics"
    tier: "Free (F0)"
    uso: "Análise de sentimento em textos"
    limites: "5k requests/mês"

  - nome: "diabetes-vision"
    tipo: "Computer Vision"
    tier: "Free (F0)"
    uso: "Análise de imagens/vídeos"
    limites: "5k transactions/mês"

  - nome: "diabetes-db"
    tipo: "SQL Database"
    tier: "Free"
    uso: "Armazenar metadados e logs"
    limites: "250GB"

  - nome: "diabetes-storage"
    tipo: "Blob Storage"
    tier: "Standard (LRS)"
    uso: "Arquivos de áudio e vídeo"
    limites: "5GB + $0 egress"
```

---

## Limitações Free Tier a Considerar

| Serviço | Limite | Impacto | Mitigação |
|---------|--------|---------|-----------|
| Speech-to-Text | 5h/mês | ~300 consultas | Cache, processamento assíncrono |
| Text Analytics | 5k req/mês | Suficiente para MVP | Monitoramento uso |
| Computer Vision | 5k req/mês | ~5k análises de imagem | Compressão de imagens |
| App Service | 60min CPU/dia | Baixo | Otimizar código |
| Blob Storage | 5GB | Limitado | Compressão, retenção curta |

---

## Estratégia de Uso para MVP

### Semana 1-2: Setup + Testes
- Uso: 20% dos limites
- Foco: Configurar serviços

### Semana 3-4: Demo + Validação
- Uso: 50% dos limites
- Foco: Processamento real de dados

### Proteções contra custos:
```python
# Em código Python
MAX_AUDIO_MINUTES = 30  # Guardar 30% de margem
MAX_TEXT_REQUESTS = 4000  # Guardar 20% de margem

def check_usage_limits():
    """Verifica se está próximo do limite"""
    current_usage = get_azure_usage()
    if current_usage > 0.8:  # 80% do limite
        logger.warning("Atingindo 80% do free tier!")
        return False
    return True
```

---

## Conclusão

**Recomendação final: Azure**

**Justificativa:**
1. Maior quota de Speech-to-Text (5h vs 1h)
2. Serviços integrados para todas as 3 modalidades
3. SQL Database generoso (250GB)
4. Documentação Python completa
5. Fácil deploy de APIs Python (App Service)

**Custo estimado para MVP:** $0 (dentro do free tier)
**Caso ultrapasse:** ~$5-10/mês para volumes pequenos

---

## Próximos Passos

1. Criar conta Azure (free trial)
2. Provisionar serviços listados acima
3. Configurar variáveis de ambiente
4. Desenvolver integrações
5. Monitorar uso (para não ultrapassar free tier)
