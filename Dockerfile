# Usar uma imagem base oficial do Python (versão slim para ser leve)
FROM python:3.12-slim

# Definir o diretório de trabalho dentro do container
WORKDIR /app

# Configurar variáveis de ambiente do Python para evitar gravação de .pyc e garantir logs em tempo real
ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1

# Instalar dependências básicas de sistema se necessário
RUN apt-get update && apt-get install -y --no-install-recommends \
    curl \
    && rm -rf /var/lib/apt/lists/*

# Copiar primeiramente o requirements.txt para aproveitar o cache de camadas do Docker
COPY agentTaskManager/requirements.txt ./agentTaskManager/

# Instalar as dependências do Python
RUN pip install --no-cache-dir -r agentTaskManager/requirements.txt

# Copiar os arquivos restantes do projeto para o container
COPY . .

# Expor a porta padrão (o Cloud Run do Google Cloud irá sobrescrever isso usando a variável PORT)
EXPOSE 8000

# Comando para rodar a aplicação com Uvicorn
# Usamos 'sh -c' para permitir que a porta seja definida dinamicamente pela variável de ambiente PORT (mandatório no Google Cloud Run)
CMD ["sh", "-c", "uvicorn agentTaskManager.main:app --host 0.0.0.0 --port ${PORT:-8000}"]
