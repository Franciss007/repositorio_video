# Guia de Execução Docker - Repositório de Vídeos e Tutoriais

## 1. Objetivo do Projeto
Plataforma web de streaming e catalogação de vídeos de procedimentos internos e tutoriais de TI, com geração automatizada de legendas e transcrição via OpenAI Whisper e edição com MoviePy.

## 2. Tecnologias Utilizadas
- **Linguagem**: Python 3.11 (estável para PyTorch e Whisper)
- **Framework Web**: Flask 3.x
- **Inteligência Artificial / Transcrição**: OpenAI Whisper (modelo `base`)
- **Processamento de Mídia**: `ffmpeg` (binário nativo do sistema) e `moviepy`
- **Banco de Dados**: Arquivo local `database.json`
- **Servidor WSGI**: Gunicorn com timeout expandido (300s)

## 3. Particularidades de Infraestrutura
- O container instala o utilitário de sistema `ffmpeg` via APT.
- O modelo do Whisper é armazenado no volume persistente `whisper_cache` em `/root/.cache/whisper`, garantindo que o modelo não seja baixado novamente a cada reinicialização do container.
- Os vídeos e legendas em `uploads/` e a base `database.json` são mapeados via volume persistente.

## 4. Estrutura dos Arquivos Docker
- `Dockerfile`: Imagem com `ffmpeg` e dependências PyTorch instaladas.
- `compose.yaml`: Serviço web mapeado na porta externa 5030 (porta interna 8090) com volumes para `uploads`, `database.json` e `whisper_cache`.
- `.dockerignore`: Ignora arquivos temporários, caches e ambientes virtuais.
- `.env.example`: Modelo de configuração de portas e ambiente.

## 5. Como Iniciar no Windows 11
```powershell
docker compose build
docker compose up -d
```

## 6. Como Iniciar no Servidor Linux (Headless)
```bash
docker compose build
docker compose up -d
```

## 7. Como Acessar a Aplicação
- URL local / Linux: [http://localhost:5030](http://localhost:5030)

## 8. Monitoramento e Logs
```bash
docker compose logs -f web
docker compose ps
```

## 9. Atualização de Código
```bash
git pull
docker compose build --no-cache
docker compose up -d --force-recreate
```

## 10. Persistência e Backup
- **Vídeos e Legendas**: Mapeados para a pasta local `./uploads`.
- **Catálogo de Vídeos**: Mapeado para o arquivo `./database.json`.
- Backup simples:
  ```bash
  tar -czvf backup_videos_$(date +%Y%m%d).tar.gz uploads database.json
  ```
