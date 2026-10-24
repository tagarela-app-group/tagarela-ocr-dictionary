# Tagarela API

Backend (Django REST) do Tagarela: conta, login e capturas (o texto da foto e do áudio chega já extraído pelo app).

Comece por [CLAUDE.md](CLAUDE.md).

```sh
cp .env.example .env
docker compose up --build
```

API em http://localhost:8000. E-mails do dev (códigos de cadastro e senha) em http://localhost:8025 (Mailpit).

```sh
curl http://localhost:8000/health
```
