# Tagarela API

Backend (Django REST) do Tagarela: recebe foto, extrai o texto (OCR) e devolve as palavras com definição.

Comece por [CLAUDE.md](CLAUDE.md).

```sh
cp .env.example .env
docker compose up --build
docker compose exec api python manage.py migrate
```

API em http://localhost:8000.

```sh
curl http://localhost:8000/health
curl -F "file=@imagem.png" http://localhost:8000/api/v1/images/analyze   # 1ª chamada lenta: carrega o OCR
```
