# Quickstart: Deploy Azure

Guia rápido para deploy da API no Azure Container Instances (ACI).

## Status

✅ **DEPLOY CONCLUÍDO** (2026-05-01)

**URL de Produção**: `http://20.226.206.126:8000` (substitua pelo IP atribuído pelo Azure após deploy)

---

## Arquitetura

A aplicação está rodando em **Azure Container Instances** com os seguintes componentes:

- **Container**: `tech-challenge-api` (imagem: ghcr.io/vagnerbarbosa/tech-challenge-fase4)
- **Recursos Cognitivos**: Azure AI Services (Text, Speech, Vision)
- **Registro**: GitHub Container Registry (ghcr.io)
- **CI/CD**: GitHub Actions

---

## Scripts de Diagnóstico

```bash
# Verificar status completo do deploy
./scripts/check-azure.sh check

# Ver logs do container
./scripts/check-azure.sh logs

# Ver status detalhado
./scripts/check-azure.sh status

# Fazer deploy manual (se necessário)
./scripts/check-azure.sh deploy

# Limpar todos os recursos (CUIDADO!)
./scripts/check-azure.sh delete
```

---

## CI/CD Pipeline

O deploy automático é feito via GitHub Actions (`.github/workflows/deploy-azure.yml`):

### Workflow Steps

1. **Check Image** - Verifica cache de imagem Docker
2. **Build** - Constrói imagem multi-stage
3. **Push** - Envia para ghcr.io
4. **Deploy** - Cria/recursos Azure e Container Instance
5. **Health Check** - Valida que a API responde

### Trigger

Push na branch `main` dispara deploy automático:

```bash
git add .
git commit -m "feat: minha nova feature"
git push origin main
```

---

## Acesso aos Serviços

| Endpoint | URL |
|----------|-----|
| API Base | `http://20.226.206.126:8000` |
| Health | `http://20.226.206.126:8000/health` |
| Swagger | `http://20.226.206.126:8000/docs` |
| ReDoc | `http://20.226.206.126:8000/redoc` |

> **Nota**: Substitua `20.226.206.126` pelo IP público atribuído pelo Azure Container Instances.

---

## Configuração do Ambiente

### Variáveis Configuradas (via CI/CD)

```bash
ENVIRONMENT=production
LOG_LEVEL=INFO
AZURE_TEXT_ENDPOINT=<auto-configured>
AZURE_TEXT_KEY=<auto-configured>
AZURE_SPEECH_KEY=<auto-configured>
AZURE_SPEECH_REGION=brazilsouth
AZURE_VISION_ENDPOINT=<auto-configured>
AZURE_VISION_KEY=<auto-configured>
DATABASE_URL=sqlite:///tmp/app.db
REDIS_ENABLED=false
SECURITY_API_KEY=<from secrets>
SECURITY_ADMIN_KEY=<from secrets>
SECRET_KEY=<from secrets>
```

### GitHub Secrets Necessários

Configurados em Settings > Secrets and variables > Actions:

- `AZURE_CREDENTIALS` - Service Principal para Azure
- `API_KEY` - Chave de API para autenticação
- `ADMIN_KEY` - Chave admin para endpoints administrativos
- `SECRET_KEY` - Secret key para FastAPI/session

---

## Troubleshooting

### Container não inicia

```bash
# Ver logs via Azure CLI
az container logs --resource-group rg-tech-challenge-fase4 --name tech-challenge-api

# Ou usar o script
./scripts/check-azure.sh logs
```

### Health check falha

```bash
# Verificar status do container
./scripts/check-azure.sh status

# Verificar se variáveis estão configuradas
az container show --resource-group rg-tech-challenge-fase4 --name tech-challenge-api \
  --query 'containers[0].environmentVariables'
```

### Recriar container manualmente

```bash
# Deletar e recriar via script
./scripts/check-azure.sh deploy
```

---

## Azure CLI Commands

### Ver Resource Group

```bash
az group show --name rg-tech-challenge-fase4
```

### Ver Container Instance

```bash
az container show --resource-group rg-tech-challenge-fase4 --name tech-challenge-api
```

### Ver AI Services

```bash
az cognitiveservices account list --resource-group rg-tech-challenge-fase4
```

### Ver Logs

```bash
az container logs --resource-group rg-tech-challenge-fase4 --name tech-challenge-api
```

---

## Limpar Recursos (CUIDADO!)

```bash
# Deletar Container Instance
az container delete --resource-group rg-tech-challenge-fase4 \
  --name tech-challenge-api --yes

# Deletar AI Services
for service in tech-challenge-text tech-challenge-speech tech-challenge-vision; do
  az cognitiveservices account delete --name $service \
    --resource-group rg-tech-challenge-fase4
done

# Deletar Resource Group (apaga TUDO!)
az group delete --name rg-tech-challenge-fase4 --yes --no-wait
```

---

## Collection/Environment

Importe o arquivo `docs/collection.json` no Postman/Insomnia:

**Environments disponíveis:**
- **Local**: http://localhost:8000 (api_key: test-api-key)
- **Azure Production**: `http://20.226.206.126:8000` (api_key: demo-api-key)

---

## Recursos

- [Azure Container Instances Docs](https://docs.microsoft.com/azure/container-instances/)
- [Azure AI Services](https://docs.microsoft.com/azure/cognitive-services/)
- [GitHub Actions Azure](https://docs.github.com/actions/deployment/deploying-to-azure)
- [Docker Build Push Action](https://github.com/marketplace/actions/build-and-push-docker-images)
