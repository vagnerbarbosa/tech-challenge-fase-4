# Tech Challenge - Fase 4

## Objetivo

**Realizar a análise e fusão de diferentes tipos de dados médicos específicos da saúde da mulher** — incluindo **texto, áudio e vídeo**.

### Opções Selecionadas:
1. ✅ **Detectar precocemente riscos em saúde materna e ginecológica**
2. ✅ **Identificar sinais de violência doméstica ou abuso**
3. ✅ **Utilizar serviços em nuvem** (Azure Free Tier)

### Foco do Projeto: Saúde Mental Feminina

Sistema multimodal para identificação de sinais de **violência doméstica** e **riscos à saúde materna** através da análise de:
- 📝 **Texto**: Prontuários, diários, relatórios
- 🎙️ **Áudio**: Consultas de telemedicina (voz)
- 🎥 **Vídeo/Imagem**: Análise de expressões faciais, linguagem corporal

---

## Visão Geral

Este projeto integra processamento de **texto, áudio e vídeo** para identificar precocemente:
- Sinais de violência doméstica em consultas médicas
- Riscos emocionais/psicológicos em gestantes
- Indicadores de estresse e ansiedade

### Tecnologias Multimodais:

| Tipo | Tecnologia Azure | Uso |
|------|------------------|-----|
| **Texto** | Azure Text Analytics | Análise de sentimento, extração de entidades |
| **Áudio** | Azure Speech Services | Transcrição + análise de entonação/padrões |
| **Vídeo** | Azure Computer Vision | Análise de expressões faciais |

---

## Tecnologias

- **Framework**: FastAPI (Python 3.11+)
- **Cloud**: Azure (Free Tier) - **Deploy em produção obrigatório**
  - App Service: Hospedagem API
  - Speech Services: Transcrição (5h/mês free)
  - Text Analytics: NLP (5k requests/mês free)
  - Computer Vision: Análise de imagem (5k requests/mês free)
  - SQL Database: Metadados (250GB free)
- **ML**: scikit-learn, transformers
- **Vídeo**: FFmpeg/OpenCV (extração de frames)
- **Container**: Docker + Docker Compose
- **Testes**: pytest

---

## Como Executar

### Pré-requisitos

- Python 3.11+
- Conta Azure (free tier)
- Chaves de API Azure configuradas

### 1. Configurar Azure

```bash
# Criar arquivo .env
cp .env.example .env

# Editar com suas credenciais Azure
AZURE_SPEECH_KEY=seu_key_aqui
AZURE_SPEECH_REGION=brazilsouth
AZURE_TEXT_ANALYTICS_KEY=seu_key_aqui
AZURE_COMPUTER_VISION_KEY=seu_key_aqui
```

### 2. Executar com Docker

```bash
# Clonar repositório
git clone https://github.com/vagnerbarbosa/tech-challenge-fase-4.git
cd tech-challenge-fase-4

# Subir aplicação
docker-compose up -d

# Verificar se está funcionando
curl http://localhost:8000/health
```

### 3. Executar Localmente

```bash
# Instalar Poetry
curl -sSL https://install.python-poetry.org | python3 -

# Instalar dependências
poetry install

# Ativar ambiente
poetry shell

# Executar
poetry run uvicorn src.api.main:app --reload
```

---

## Endpoints

| Endpoint | Método | Descrição | Modalidade |
|----------|--------|-----------|------------|
| `/health` | GET | Health check da API | - |
| `/analyze/text` | POST | Análise de texto | 📝 Texto |
| `/analyze/audio` | POST | Análise de áudio | 🎙️ Áudio |
| `/analyze/image` | POST | Análise de imagem ou vídeo | 🎥 Imagem/Vídeo |
| `/analyze/multimodal` | POST | Fusão de 3 modalidades | 📝🎙️🎥 |
| `/docs` | GET | Documentação Swagger | - |

---

## Exemplo de Uso

### Análise de Texto

```bash
curl -X POST "http://localhost:8000/analyze/text" \
  -H "Content-Type: application/json" \
  -d '{
    "texto": "Estou me sentindo muito ansiosa e tenho medo de falar sobre o que acontece em casa...",
    "tipo": "diario"
  }'
```

**Resposta:**
```json
{
  "sentimento": "negativo",
  "score": -0.85,
  "risco_violencia": "alto",
  "risco_saude_mental": "alto",
  "palavras_chave": ["ansiosa", "medo", "casa"],
  "indicadores": ["sinalizacao_isolamento", "expressao_medo"]
}
```

### Análise de Áudio

```bash
curl -X POST "http://localhost:8000/analyze/audio" \
  -H "Content-Type: multipart/form-data" \
  -F "audio=@consulta.wav" \
  -F "metadata={\"tipo_consulta\":\"pré-natal\"}"
```

**Resposta:**
```json
{
  "transcricao": "Doutor, eu não sei se posso contar isso...",
  "sentimento": "negativo",
  "entonação": "hesitante",
  "risco_violencia": "medio",
  "pausas_suspeitas": 3,
  "voz_tremida": true
}
```

### Análise de Imagem/Vídeo

**Imagem:**
```bash
curl -X POST "http://localhost:8000/analyze/image" \
  -H "Content-Type: multipart/form-data" \
  -F "imagem=@foto_consulta.jpg"
```

**Vídeo (frames extraídos automaticamente):**
```bash
curl -X POST "http://localhost:8000/analyze/image" \
  -H "Content-Type: multipart/form-data" \
  -F "imagem=@consulta_video.mp4"
```

**Resposta:**
```json
{
  "emoção_principal": "tristeza",
  "confiança": 0.89,
  "expressoes": ["evitando_olho", "expressao_tensa"],
  "sinais_alertas": [],
  "risco_violencia": "medio"
}
```

### Análise Multimodal

```bash
curl -X POST "http://localhost:8000/analyze/multimodal" \
  -H "Content-Type: multipart/form-data" \
  -F "texto=@relatorio.txt" \
  -F "audio=@consulta.wav" \
  -F "imagem=@foto.jpg"
```

**Resposta:**
```json
{
  "fusao": {
    "risco_violencia": "alto",
    "confiança": 0.92,
    "alerta": true
  },
  "texto": { ... },
  "audio": { ... },
  "imagem": { ... },
  "recomendacao": "Encaminhar para equipe multidisciplinar"
}
```

---

## Modalidades de Dados

### 📝 Texto (Azure Text Analytics)

**Processamento:**
- Análise de sentimento
- Extração de entidades médicas
- Detecção de idioma
- Identificação de padrões de violência

**Exemplos de entrada:**
- Prontuários médicos
- Diários pessoais
- Relatos de consultas
- Questionários

### 🎙️ Áudio (Azure Speech Services)

**Processamento:**
- Speech-to-text (transcrição)
- Análise de entonação
- Detecção de pausas suspeitas
- Identificação de voz tremida

**Exemplos de entrada:**
- Gravações de consultas (com consentimento)
- Telemedicina
- Depoimentos

### 🎥 Imagem/Vídeo (Azure Computer Vision + FFmpeg)

**Processamento:**
- **Imagens**: Análise direta com Azure Computer Vision
- **Vídeos**: Extração automática de frames (1 a cada 5s) + análise
- Análise de expressões faciais
- Detecção de emoções
- Identificação de marcas/sinais

**Exemplos de entrada:**
- Fotos de consulta (JPEG, PNG)
- Vídeos curtos de atendimento (MP4, max 30s)

---

## Azure Free Tier - Limites

| Serviço | Limite Free | Estimativa de Uso |
|---------|-------------|-------------------|
| Speech Services | 5h áudio/mês | ~300 consultas |
| Text Analytics | 5k requests/mês | Suficiente para MVP |
| Computer Vision | 5k transactions/mês | ~5k análises |
| SQL Database | 250GB | Metadados + logs |
| App Service | 60min CPU/dia | API contínua |
| Blob Storage | 5GB | Áudios + imagens |

**Custo total: $0** (dentro do free tier)

---

## Testes

```bash
# Testes unitários e integração
poetry run pytest -v

# Testes de carga (Locust)
cd tests/load
poetry run locust -f locustfile.py
```

---

## Documentação

- [Especificação do Produto](docs/product-spec.md)
- [Histórias de Usuário](docs/user-stories.md)
- [Arquitetura](docs/architecture.md)
- [Análise Cloud Free Tier](docs/technical/cloud-free-tier-analysis.md)
- [API Contracts](docs/api-contracts.md)

---

## Vídeo de Demonstração

📹 [Assista ao vídeo de demonstração no YouTube](LINK_AQUI)

O vídeo demonstra:
- Arquitetura multimodal
- Análise de texto, áudio e vídeo
- Identificação de sinais de alerta
- Dashboard de resultados
- Deploy na Azure

---

## Estrutura do Projeto

```
tech-challenge-fase-4/
├── src/
│   ├── api/               # FastAPI routes
│   ├── core/              # Configurações Azure
│   ├── services/          # Análise multimodal
│   ├── models/            # Schemas Pydantic
│   └── infrastructure/    # Integração Azure
├── tests/
│   ├── unit/
│   ├── integration/
│   └── load/
├── docs/                  # Documentação SDD
├── docker/
├── docker-compose.yml
├── Dockerfile
└── README.md
```

---

## Requisitos de Avaliação

| Critério | Peso | Status |
|----------|------|--------|
| Funcionalidade | 30% | API multimodal funciona |
| Código | 25% | Clean code, type hints |
| Containerização | 20% | Docker + Azure |
| Testes | 15% | >70% cobertura |
| Documentação | 10% | README + vídeo |

---

## Licença

MIT License - Copyright (c) 2026 Equipe Tech Challenge

---

## ⚠️ Notas Importantes

- **Consentimento**: Todos os dados de áudio/vídeo devem ter consentimento explícito
- **LGPD**: Dados sensíveis são anonimizados antes do processamento
- **Ética**: Sistema é ferramenta de apoio, não substitui julgamento médico
- **Free Tier**: Monitorar uso para não ultrapassar limites Azure

---

## Equipe

Este projeto é desenvolvido pela mesma equipe das Fases 1, 2 e 3:

| Nome | GitHub |
|------|--------|
| Adriel Santos | [@AdrielCandido](https://github.com/AdrielCandido) |
| Leticia Nepomuceno | [@LeticiaNepomuceno](https://github.com/LeticiaNepomuceno) |
| Lucas Silva | [@lucfsilva](https://github.com/lucfsilva) |
| Vagner Barbosa | [@vagnerbarbosa](https://github.com/vagnerbarbosa) |

**Curso**: FIAP/Alura - AI para Devs (IADT)
**Fase**: 4 (Análise Multimodal de Dados em Saúde da Mulher)

---

## Fases Anteriores

- [Fase 1 - Diabetes Prediction](https://github.com/vagnerbarbosa/tech-challenge-fase-1)
- [Fase 2 - Otimização com Algoritmos Genéticos](https://github.com/vagnerbarbosa/tech-challenge-fase-2)
- [Fase 3 - Assistente Virtual Médico](https://github.com/vagnerbarbosa/tech-challenge-fase-3)
