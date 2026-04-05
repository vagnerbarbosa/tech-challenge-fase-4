# Mock Server para Azure AI Services
FROM python:3.11-slim

WORKDIR /app

# Instalar dependências
RUN pip install --no-cache-dir fastapi uvicorn pydantic

# Copiar código
COPY main.py .

# Expor portas
EXPOSE 3001 3002 3003

# Comando para iniciar
CMD ["python", "-m", "uvicorn", "main:app", "--host", "0.0.0.0", "--port", "3001", "--reload"]
