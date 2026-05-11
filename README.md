# 🏥💜 Tech Challenge Fase 4 - Sistema multimodal de análise de saúde da mulher

[![Python](https://img.shields.io/badge/Python-3.11+-3776AB?style=flat-square&logo=python&logoColor=white)](https://www.python.org/)
[![FastAPI](https://img.shields.io/badge/FastAPI-0.115+-009688?style=flat-square&logo=fastapi&logoColor=white)](https://fastapi.tiangolo.com/)
[![Pydantic](https://img.shields.io/badge/Pydantic-v2-E92063?style=flat-square&logo=pydantic&logoColor=white)](https://docs.pydantic.dev/)
[![Azure](https://img.shields.io/badge/Azure%20AI-0089D6?style=flat-square&logo=microsoft-azure&logoColor=white)](https://azure.microsoft.com/)
[![Docker](https://img.shields.io/badge/Docker-2496ED?style=flat-square&logo=docker&logoColor=white)](https://www.docker.com/)
[![Spec Kit](https://img.shields.io/badge/Spec%20Kit-SDD-2ea44f?style=flat-square)](https://github.com/github/spec-kit)
[![Claude Code](https://img.shields.io/badge/Claude%20Code-ff6b35?style=flat-square&logo=anthropic&logoColor=white)](https://claude.ai/code)
[![License](https://img.shields.io/badge/License-MIT-yellow.svg?style=flat-square)](LICENSE)

[![Unit and Integration Tests](https://github.com/vagnerbarbosa/tech-challenge-fase-4/workflows/Unit%20and%20Integration%20Tests/badge.svg)](https://github.com/vagnerbarbosa/tech-challenge-fase-4/actions/workflows/ci.yml)
[![E2E Tests](https://github.com/vagnerbarbosa/tech-challenge-fase-4/workflows/E2E%20Tests/badge.svg)](https://github.com/vagnerbarbosa/tech-challenge-fase-4/actions/workflows/e2e.yml)

**Análise multimodal de saúde da mulher usando Azure AI Services e YOLOv8 local**

> **📅 Atualizado**: 2026-05-10 | **Versão**: 1.0.0 | **Status**: Produção

---

## 🎯 Objetivo

Sistema para identificação precoce de riscos em saúde materna e sinais de violência doméstica através da análise de **texto, áudio e vídeo**.

### Tecnologias

| Modalidade | Tecnologia | SDK |
|------------|------------|-----|
| 📝 **Texto** | Azure AI Language | `azure-ai-textanalytics` |
| 🎙️ **Áudio** | Azure AI Speech | `azure-cognitiveservices-speech` |
| 🎥 **Vídeo** | **YOLOv8** (local) | `ultralytics` + `opencv-python` |
| 🌍 **Multilíngue** | Azure AI Content Safety | `azure-ai-contentsafety` |

> **Nota**: YOLOv8 roda localmente (custo zero), cumprindo requisito obrigatório do PDF.

---

## 🚀 Deploy

[![Deploy Status](https://img.shields.io/badge/Deploy-Azure%20Container%20Instances-0089D6?style=flat-square&logo=microsoft-azure)](http://<your-azure-ip>:8000/health)

✅ **API Online**: `http://<your-azure-ip>:8000` (substitua pelo IP da sua implantação Azure)

### Endpoints

| Endpoint | URL | Ambiente |
|----------|-----|----------|
| Health | `http://<your-azure-ip>:8000/health` | Todos |
| OpenAPI | `http://<your-azure-ip>:8000/openapi.json` | Todos |
| Swagger UI | `http://localhost:8000/docs` | Apenas local |
| ReDoc | `http://localhost:8000/redoc` | Apenas local |

**Nota:** Swagger UI e ReDoc estão desabilitados em produção (HTTP sem HTTPS causa Mixed Content errors). Use `openapi.json` com Postman/Insomnia.

---

## ⚡ Quick Start

```bash
# Clone e execute com Docker
git clone https://github.com/vagnerbarbosa/tech-challenge-fase-4.git
cd tech-challenge-fase-4
./scripts/run-mock.sh

# Teste
curl http://localhost:8000/health
```

📖 Veja o [guia completo](docs/RUNNING.md) para outras opções.

---

## 🔒 Segurança e Autenticação

API com hardening completo (OWASP API Top 10 + LGPD):

### Como Autenticar
Todas as requisições protegidas devem incluir a API Key no header:
`X-API-Key: sua-api-key-aqui`

- **Desenvolvimento**: Use `dev-api-key`.
- **Produção**: Use chaves geradas via `/admin/api-key` ou configuradas no `.env`.

### Camadas de Proteção
- ✅ **Rate Limiting**: Proteção contra DDoS e abuso de quota Azure.
- ✅ **Uploads**: Validação rigorosa via magic bytes.
- ✅ **Logs**: Sanitização automática de PII (LGPD).
- ✅ **Headers**: CSP, HSTS, X-Frame-Options.

📖 Detalhes: [Guia de Segurança](docs/technical/security-guide.md)

---

## 📡 Guia de Requisições (API Guide)

### 1. Análise de Texto
**Endpoint**: `POST /analyze/text`  
**Payload**: `{"texto": "Sinto medo", "patient_id": "id123"}`
```bash
curl -X POST "http://localhost:8000/analyze/text" \
     -H "X-API-Key: dev-api-key" \
     -H "Content-Type: application/json" \
     -d '{"texto": "Estou me sentindo muito ansiosa", "patient_id": "123"}'
```

### 2. Análise de Áudio
**Endpoint**: `POST /analyze/audio`  
**Formatos**: WAV, MP3, OGG (Max 50MB)
```bash
curl -X POST "http://localhost:8000/analyze/audio" \
     -H "X-API-Key: dev-api-key" \
     -F "file=@audio.wav" \
     -F "patient_id=123"
```

### 3. Análise de Vídeo
**Endpoint**: `POST /analyze/video`  
**Formatos**: MP4, AVI, MOV (Max 2min)
```bash
curl -X POST "http://localhost:8000/analyze/video" \
     -H "X-API-Key: dev-api-key" \
     -F "video=@video.mp4" \
     -F "patient_id=123"
```

### 4. Análise Multimodal (Fusão)
**Endpoint**: `POST /analyze/multimodal`
```bash
curl -X POST "http://localhost:8000/analyze/multimodal" \
     -H "X-API-Key: dev-api-key" \
     -H "Content-Type: application/json" \
     -d '{"text": "texto", "audio_file": "audio.wav"}'
```

### ⚠️ Tratamento de Erros
| Código | Significado | Ação |
|--------|-------------|-------|
| `401` | Unauthorized | Verifique a `X-API-Key` |
| `429` | Too Many Requests | Aguarde o tempo no header `Retry-After` |
| `400` | Bad Request | Verifique o formato do payload/arquivo |

---

## 🎥 Vídeo de Demonstração

O vídeo demonstra:
- Análise de texto, áudio e vídeo
- Análise multimodal
- Identificação de sinais de alerta
- Deploy na Azure

📹 **Link do vídeo**: [YouTube - Tech Challenge Fase 4](https://www.youtube.com/watch?v=dQw4w9WgXcQ)

---

## 🛠️ Scripts e Configuração

### Scripts Disponíveis
| Script | Descrição |
|--------|-----------|
| `./scripts/run-mock.sh` | Inicia com Docker + Mocks (Recomendado) |
| `./scripts/run.sh` | Inicia localmente com Poetry |
| `./scripts/test-docker.sh` | Executa testes via Docker |
| `./scripts/lint.sh` | Verifica código (Ruff + mypy) |
| `./scripts/check-azure.sh` | Verifica credenciais Azure |

### Variáveis de Ambiente (`.env`)
| Variável | Descrição | Padrão (Dev) |
|----------|-----------|---------------|
| `SECURITY_API_KEY` | Chave mestra de autenticação | `dev-api-key` |
| `SECURITY_ENVIRONMENT` | Ambiente da aplicação | `development` |
| `AZURE_TEXT_KEY` | Key do Azure Text Analytics | `your-key` |
| `AZURE_TEXT_ENDPOINT` | Endpoint do Azure Text | `https://...` |
| `AZURE_SPEECH_KEY` | Key do Azure Speech | `your-key` |
| `AZURE_SPEECH_REGION` | Região do Azure Speech | `eastus` |
| `CONTENT_SAFETY_ENABLED` | Habilita Azure Content Safety | `true` |

---

## 📚 Documentação

| Documento | Descrição |
|-----------|-----------|
| [Como Executar](docs/RUNNING.md) | Passo a passo completo |
| [Segurança](docs/technical/security-guide.md) | Arquitetura de segurança |
| [API Contracts](docs/api-contracts.md) | Contratos e exemplos |
| [Arquitetura](docs/architecture.md) | Visão técnica |
| [Specs](specs/README.md) | Índice de especificações |

### Specs Kit (Status)

| ID | Feature | Status |
|----|---------|--------|
| 001-009 | Core + Deploy | ✅ Concluído |
| 010 | Content Safety Multilíngue | ✅ Concluído |
| 011 | Testing Strategy E2E | ✅ Concluído |
| 012 | Documentação Final | ✅ Concluído |

---

## 📂 Estrutura Simplificada

```
tech-challenge-fase-4/
├── src/                    # Código fonte
│   ├── api/               # FastAPI app
│   ├── core/              # Config, security
│   ├── services/          # Lógica de negócio
│   └── infrastructure/    # Clientes Azure
├── tests/                 # Testes ([guia](docs/testing.md))
├── docs/                  # Documentação
├── specs/                 # Especificações
├── scripts/               # Utilitários
└── README.md             # Este arquivo
```

---

## 👥 Integrantes Grupo 27

| Nome | GitHub |
|------|--------|
| Adriel Santos | [@AdrielCandido](https://github.com/AdrielCandido) |
| Leticia Nepomuceno | [@LeticiaNepomucena](https://github.com/LeticiaNepomucena) |
| Lucas Silva | [@lucfsilva](https://github.com/lucfsilva) |
| Vagner Barbosa | [@vagnerbarbosa](https://github.com/vagnerbarbosa) |

**Curso**: FIAP/Alura - AI para Devs (IADT)

---

## 📜 Licença

MIT License - Copyright (c) 2026 Grupo 27
