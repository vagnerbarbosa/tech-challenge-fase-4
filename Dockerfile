# ===========================================
# Dockerfile Multi-stage para FastAPI
# ===========================================

# -------------------------------------------
# Stage 1: Builder (dependências)
# -------------------------------------------
FROM python:3.11-slim as builder

# Variáveis de ambiente
ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    POETRY_NO_INTERACTION=1 \
    POETRY_VIRTUALENVS_CREATE=false

# Instalar dependências do sistema necessárias para compilação
RUN apt-get update \
    && apt-get install -y --no-install-recommends \
        build-essential \
        libffi-dev \
    && rm -rf /var/lib/apt/lists/*

# Instalar Poetry
RUN pip install --no-cache-dir poetry

# Copiar apenas arquivos de dependências primeiro (cache eficiente)
WORKDIR /app
COPY pyproject.toml ./

# Instalar dependências (sem dev)
RUN poetry install --no-root --without dev

# -------------------------------------------
# Stage 2: Runtime (imagem final)
# -------------------------------------------
FROM python:3.11-slim as runtime

# Criar usuário não-root para segurança
RUN groupadd -r appgroup && useradd -r -g appgroup appuser

# Variáveis de ambiente
ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PYTHONFAULTHANDLER=1 \
    APP_HOME=/app \
    PORT=8000

# Instalar dependências de runtime
RUN apt-get update \
    && apt-get install -y --no-install-recommends \
        libgl1-mesa-glx \
        libglib2.0-0 \
        libsm6 \
        libxext6 \
        libxrender-dev \
        libgomp1 \
    && rm -rf /var/lib/apt/lists/*

# Diretório de trabalho
WORKDIR $APP_HOME

# Copiar dependências instaladas do builder
COPY --from=builder /usr/local/lib/python3.11/site-packages /usr/local/lib/python3.11/site-packages
COPY --from=builder /usr/local/bin /usr/local/bin

# Copiar código da aplicação
COPY --chown=appuser:appgroup src/ ./src/

# Mudar para usuário não-root
USER appuser

# Health check
HEALTHCHECK --interval=30s --timeout=10s --start-period=5s --retries=3 \
    CMD python -c "import urllib.request; urllib.request.urlopen('http://localhost:8000/health')" || exit 1

# Expor porta
EXPOSE $PORT

# Comando de inicialização
CMD ["uvicorn", "src.api.main:app", "--host", "0.0.0.0", "--port", "8000"]
