# Mock Server para Azure AI Services
FROM python:3.11-slim

WORKDIR /app

# Instalar dependências
RUN pip install --no-cache-dir fastapi uvicorn pydantic python-multipart

# Copiar código
COPY main.py .

# Expor portas
EXPOSE 3001 3002 3003

# Comando para iniciar (inicia 3 servidores nas portas 3001, 3002, 3003)
CMD ["python", "main.py"]
