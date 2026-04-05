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

### 3. Azure (Microsoft) - **RECOMENDADO**

> **Nota sobre Rebranding (2024-2025)**: Os serviços "Azure Cognitive Services" foram renomeados para **Azure AI Services** e agora fazem parte do **Azure AI Foundry**. Os SDKs Python foram atualizados; o antigo `azure-cognitiveservices-vision-computervision` foi deprecated em nov/2024.

#### Free Tier Inclui (12 meses + Sempre Grátis):
| Serviço | Free Tier | Uso no Projeto | SDK Python |
|---------|-----------|----------------|------------|
| Virtual Machines | 750h B1s | API Server | - |
| Blob Storage | 5GB + 10k operations | Armazenamento | `azure-storage-blob` |
| SQL Database | 250GB + 15 DBs | Banco de dados | `pyodbc` / `asyncpg` |
| Functions | 1M execuções/mês | Serverless functions | `azure-functions` |
| **Azure AI Speech** | 5 horas/mês | Speech-to-text | `azure-cognitiveservices-speech` >=1.48.0 |
| **Azure AI Vision** | 5k transactions/mês | Análise de imagem/vídeo | `azure-ai-vision-imageanalysis` >=1.0.0 |
| **Azure AI Language** (Text Analytics) | 5k requests/mês | NLP/Sentiment | `azure-ai-textanalytics` >=5.4.0 |

> **⚠️ SDK Vision Atualizado**: Usar `azure-ai-vision-imageanalysis` (novo). O antigo `azure-cognitiveservices-vision-computervision` foi deprecated.

#### ✅ VANTAGENS (RECOMENDADO):
- **Azure AI Speech: 5 horas/mês** (vs 60 min dos outros!) - MAIOR LIMITE
- Azure AI Language (Text Analytics) para sentiment analysis
- Azure AI Vision para análise de vídeo
- SQL Database com 250GB (muito espaço)
- Azure Functions serverless
- **SDKs Python atualizados e mantidos**:
  - `azure-ai-textanalytics` 5.4.0+ (ativo)
  - `azure-cognitiveservices-speech` 1.48.0+ (ativo)
  - `azure-ai-vision-imageanalysis` 1.0.0+ (novo SDK, substitui o deprecated)

#### ❌ Desvantagens:
- Menos popular para tutoriais em português
- Rebranding recente pode confundir (Cognitive Services → AI Services → AI Foundry)

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

## Arquitetura com Azure AI Services (Free Tier)

```
┌─────────────────────────────────────────────────────────────────────┐
│                      AZURE AI SERVICES                               │
│                    (Azure AI Foundry)                              │
├─────────────────────────────────────────────────────────────────────┤
│                                                                      │
│  ┌────────────────┐   ┌────────────────────┐   ┌──────────────────┐ │
│  │  Azure App     │   │  Azure AI Speech   │   │  Azure AI Vision │ │
│  │  Service       │◄──┤  (5h/mês free)     │   │  (5k trans/mês)  │ │
│  │  (API REST)    │   │  SDK: azure-cogni- │   │  SDK: azure-ai-  │ │
│  │                │   │  tiveservices-    │   │  vision-image-  │ │
│  │                │   │  speech            │   │  analysis         │ │
│  └───────┬────────┘   └────────────────────┘   └──────────────────┘ │
│          │                                                           │
│  ┌───────▼────────┐   ┌────────────────────────┐                    │
│  │  Azure SQL       │   │  Azure AI Language   │                    │
│  │  Database        │   │  (Text Analytics)    │                    │
│  │  (250GB free)    │   │  (5k requests/mês)   │                    │
│  │                  │   │  SDK: azure-ai-      │                    │
│  │                  │   │  textanalytics       │                    │
│  └──────────────────┘   └──────────────────────┘                    │
│                                                                      │
│  ┌────────────────────────────────────────┐                        │
│  │  Azure Blob Storage (5GB free)         │                        │
│  │  - Áudios temporários                  │                        │
│  │  - Frames de vídeo                     │                        │
│  │  - Logs e metadados                    │                        │
│  │  SDK: azure-storage-blob               │                        │
│  └────────────────────────────────────────┘                        │
│                                                                      │
└─────────────────────────────────────────────────────────────────────┘

**SDKs Python (2025):**
- Texto: azure-ai-textanalytics >=5.4.0
- Áudio: azure-cognitiveservices-speech >=1.48.0
- Visão: azure-ai-vision-imageanalysis >=1.0.0 (novo!)
- Storage: azure-storage-blob >=12.0.0
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

## Configuração Azure AI Services para Projeto

### Serviços Necessários:

```yaml
# azure-services.yaml
recursos:
  - nome: "health-api-app"
    tipo: "App Service"
    tier: "Free (F1)"
    uso: "Hospedar API FastAPI"
    limites: "1GB RAM, 60 min CPU/dia"

  - nome: "health-speech"
    tipo: "Azure AI Speech"
    tier: "Free (F0)"
    uso: "Transcrever consultas de áudio"
    limites: "5 horas áudio/mês"
    sdk: "azure-cognitiveservices-speech>=1.48.0"

  - nome: "health-language"
    tipo: "Azure AI Language" (Text Analytics)
    tier: "Free (F0)"
    uso: "Análise de sentimento em textos"
    limites: "5k requests/mês"
    sdk: "azure-ai-textanalytics>=5.4.0"

  - nome: "health-vision"
    tipo: "Azure AI Vision"
    tier: "Free (F0)"
    uso: "Análise de imagens/vídeos"
    limites: "5k transactions/mês"
    sdk: "azure-ai-vision-imageanalysis>=1.0.0"
    nota: "NÃO usar azure-cognitiveservices-vision-computervision (deprecated)"

  - nome: "health-db"
    tipo: "SQL Database"
    tier: "Free"
    uso: "Armazenar metadados e logs"
    limites: "250GB"

  - nome: "health-storage"
    tipo: "Blob Storage"
    tier: "Standard (LRS)"
    uso: "Arquivos de áudio e vídeo temporários"
    limites: "5GB + $0 egress"
    sdk: "azure-storage-blob>=12.0.0"
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

**Recomendação final: Azure AI Services (Foundry Tools)**

**Justificativa:**
1. Maior quota de Speech-to-Text (5h vs 1h)
2. Serviços integrados para todas as 3 modalidades (Texto, Áudio, Visão)
3. SQL Database generoso (250GB)
4. **SDKs Python atualizados e bem mantidos**:
   - `azure-ai-textanalytics` 5.4.0+ (estável, ativo)
   - `azure-cognitiveservices-speech` 1.48.0+ (estável, ativo)
   - `azure-ai-vision-imageanalysis` 1.0.0+ (novo, substitui SDK deprecated)
5. Fácil deploy de APIs Python (App Service)

**Nota sobre Rebranding:**
Azure Cognitive Services foi renomeado para Azure AI Services (2024) e agora faz parte do Azure AI Foundry (2025). Os serviços permanecem os mesmos, mas os SDKs foram atualizados. O antigo SDK `azure-cognitiveservices-vision-computervision` foi deprecated em novembro 2024; usar `azure-ai-vision-imageanalysis`.

**Custo estimado para MVP:** $0 (dentro do free tier)
**Caso ultrapasse:** ~$5-10/mês para volumes pequenos

---

## Próximos Passos

1. Criar conta Azure (free trial)
2. Provisionar serviços listados acima
3. Configurar variáveis de ambiente
4. Desenvolver integrações
5. Monitorar uso (para não ultrapassar free tier)
