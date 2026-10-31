# Tagarela API

Backend (Django REST) do Tagarela: conta, login e capturas (o texto da foto e do áudio chega já extraído pelo app).

Análise com o Gemini: [docs/language_analysis.md](docs/language_analysis.md).

Comece por [CLAUDE.md](CLAUDE.md).

Dois ambientes: `dsv` (local) e `prd`. Cada um tem o seu env: `.env.dsv` e `.env.prd`, fora do git, a partir dos `.example`.

## dsv

```sh
cp .env.dsv.example .env.dsv
docker compose up --build
```

API em http://localhost:8000. E-mails (códigos de cadastro e senha) em http://localhost:8025 (Mailpit).

```sh
curl http://localhost:8000/health
```

## prd

Roteiro do primeiro deploy: [docs/deploy.md](docs/deploy.md).
