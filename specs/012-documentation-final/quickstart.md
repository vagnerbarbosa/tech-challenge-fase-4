# Quickstart: Documentação Final

Este documento serve como guia para o avaliador/usuário inicial para colocar o sistema em operação rapidamente.

## Pré-requisitos
- Docker e Docker Compose instalados.
- Chaves de API do Azure (se não for usar Mock Mode).

## Setup Rápido (5 Minutos)

1. **Clonar o Repositório**:
   ```bash
   git clone <repo-url>
   cd tech-challenge-fase-4
   ```

2. **Configurar Ambiente**:
   - Copie o `.env.example` para `.env`.
   - Preencha as credenciais do Azure ou mantenha os defaults para usar o **Mock Mode**.

3. **Subir a API**:
   ```bash
   docker-compose up --build -d
   ```

4. **Validar Saúde**:
   - Acesse `http://localhost:8000/health` para verificar quotas e status dos serviços.

## Primeiros Passos (Testando a API)

### 1. Autenticação
Obtenha sua API Key via endpoint administrativo ou use a chave default do `.env`.
Envie todas as requisições com o header: `X-API-Key: sua_chave_aqui`.

### 2. Primeira Análise (Texto)
```bash
curl -X POST "http://localhost:8000/analyze/text" \
     -H "X-API-Key: sua_chave" \
     -H "Content-Type: application/json" \
     -d '{"text": "Sinto muita ansiedade e medo constante", "patient_id": "123"}'
```

### 3. Acessando a Documentação Interativa
Abra no navegador: `http://localhost:8000/docs`
