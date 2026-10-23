# syntax=docker/dockerfile:1
FROM python:3.11-slim

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PORT=8090 \
    TZ=America/Sao_Paulo

WORKDIR /app

RUN apt-get update && apt-get install -y --no-install-recommends \
    ffmpeg \
    tzdata \
    curl \
    git \
    && ln -snf /usr/share/zoneinfo/$TZ /etc/localtime && echo $TZ > /etc/timezone \
    && rm -rf /var/lib/apt/lists/*

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Pre-cria os diretorios de uploads e cache
RUN mkdir -p /app/uploads /root/.cache/whisper

COPY . .

EXPOSE 8090

HEALTHCHECK --interval=30s --timeout=5s --start-period=30s --retries=3 \
    CMD curl -f http://localhost:8090/ || exit 1

# Timeout estendido (300s) para processamento de videos e transcricao Whisper
CMD ["gunicorn", "--bind", "0.0.0.0:8090", "--workers", "1", "--timeout", "300", "app:app"]
