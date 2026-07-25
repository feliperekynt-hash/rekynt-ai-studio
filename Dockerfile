# Dockerfile de Produção para Hugging Face Spaces / Render / Railway
FROM python:3.11-slim

# Instalar dependências de sistema (FFmpeg, fontes e suporte de vídeo)
RUN apt-get update && apt-get install -y --no-install-recommends \
    ffmpeg \
    fonts-dejavu-core \
    libsm6 \
    libxext6 \
    git \
    curl \
    && rm -rf /var/lib/apt-get/lists/*

WORKDIR /app

# Copiar requirements e instalar dependências em Python
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copiar todo o código da plataforma
COPY . .

# Permissões e pastas de ativos
RUN mkdir -p assets/drive_uploads assets/output assets/temp assets/audio assets/logos config

# Definir porta do container (Hugging Face utiliza 7860 por padrão, Render usa PORT)
ENV PORT=7860
EXPOSE 7860

# Comando para iniciar o servidor web da Rekynt
CMD ["python", "web/server.py"]
