# ARCHITECTURE — Tagarela API

## Stack

- Python 3.12, Django 5.2, Django REST Framework 3.15+.
- PostgreSQL 16 (psycopg 3). Redis 7 (só cache).
- OCR: PaddleOCR 3 + PaddlePaddle 3.2.0 CPU (índice extra `paddlepaddle.org.cn` no `requirements.txt`). Pillow valida imagem.
- HTTP externo: httpx.
- Local: Docker Compose (`api`, `db`, `redis`). Imagem `python:3.12-slim` + libs de sistema `libglib2.0-0 libgl1 libgomp1` (Paddle/OpenCV) e `libpq5` (Postgres).

## Decisão: monólito modular

Um backend Django, responsabilidade separada por app. Sem microserviço: projeto no início, microserviço = complexidade em deploy, comunicação, logs, observabilidade, rede, manutenção, testes. OCR ou áudio precisar escalar separado: extrair o módulo.

Princípios: local antes de externo (cache → banco → API). Redis descartável, Postgres é a verdade. Estrutura simples, sem camada extra sem necessidade.

## Pastas

```
config/                    settings, urls raiz, health.py (GET /health), wsgi/asgi
apps/
  ocr/                     imagem → validação → texto. Orquestra a análise
    providers/paddle.py    único lugar que conhece PaddleOCR
    validators.py          validação do upload
    serializers.py         ImageAnalyzeSerializer
    services.py            ImageAnalysisService (OCR + lexical)
    views.py, urls.py      analyze_image
  lexical/                 texto → palavras → definição
    providers/dictionary.py  único lugar que conhece a API de dicionário
    cache.py               LexicalCache (Redis)
    models.py              LexicalEntry
    services.py            LexicalPreparationService, LexicalLookupService
    admin.py               LexicalEntry no admin
docs/                      PRODUCT, ARCHITECTURE
.github/workflows/ci.yml   esteira
pyproject.toml             config do ruff e coverage (sem dependência)
requirements.txt           dependências da app (imagem)
requirements-dev.txt       ruff, coverage, pip-audit (fora da imagem)
```

- Dependência entre apps: `ocr` → `lexical`. Nunca o contrário.
- `lexical` sem rota própria (sem `urls.py`).
- Stubs vazios do Django: `ocr/models.py`, `ocr/admin.py`, `lexical/views.py`, `lexical/serializers.py`, `*/tests.py`.

## Onde colocar

- Endpoint: view em `apps/<app>/views.py` + `apps/<app>/urls.py` + `include` em `config/urls.py` sob `api/v1/<recurso>/`.
- Validação de entrada: serializer. Regra reutilizável: `validators.py`.
- Regra de negócio, orquestração: `services.py`.
- Lib/serviço externo: `providers/<nome>.py`. Trocar provedor = mexer só no provider.
- Cache: `cache.py` do app.
- Tabela: `models.py` + migration + registro em `admin.py`.
- Setting: env → `config/settings.py` → `.env.example` + tabela Config abaixo.
- Transversal (health, settings, urls raiz): `config/`.
- Módulo novo (ex.: áudio): app novo `apps/<nome>/` em `INSTALLED_APPS`, mesma estrutura dos atuais.

## Fluxo

`analyze_image` (view) → `ImageAnalyzeSerializer` (valida) → `ImageAnalysisService.analyze` → `PaddleOCRProvider.extract_text` → `LexicalLookupService.analyze_text` → resposta.

Lookup, em lote:

1. Redis `MGET`. HIT → `source: cache`.
2. MISS → Postgres (`normalized_word__in`). HIT → `source: database`, regrava no Redis.
3. MISS → dicionário, 1 chamada por palavra, sequencial. Upsert no Postgres + Redis, `source: dictionary`.

## OCR (`ocr`)

- Validação em ordem: tamanho ≤ `OCR_MAX_IMAGE_SIZE_BYTES` → `content_type` JPEG/PNG/WEBP → Pillow abre + `verify()` → formato real JPEG/PNG/WEBP. Extensão do nome não garante nada. Erro = 400, mensagem pt-BR.
- Engine PaddleOCR: um por processo, criado na 1ª requisição (lazy, com lock), reutilizado. 1ª chamada lenta (carrega modelos). Ideal: carregar no startup.
- Paddle lê de caminho: grava arquivo temporário, apaga no fim. Desligado: orientação de documento, unwarping, orientação de linha.
- Texto = `rec_texts` unidos por espaço.

## Lexical (`lexical`)

- Normalização: regex `\b[\w'-]+\b` → NFKC → `casefold` → tira `-` e `'` das bordas → dedup → ordem alfabética. Ex.: "The quick brown fox" → brown, fox, quick, the. Número também vira palavra (`\w` pega dígito).
- Dicionário: `GET {DICTIONARY_API_BASE_URL}/{lang}/{palavra}` (dictionaryapi.dev), timeout `DICTIONARY_API_TIMEOUT_SECONDS`. Usa só `meanings[].definitions[].definition`.
- Sem definição (404, erro de rede, timeout, resposta vazia): `definitions: []`, salvo igual no Postgres e Redis. Erro transitório fica gravado.
- Idioma: `LEXICAL_LANGUAGE`. `analyze_text(text, language)` já aceita idioma; view ainda não passa.

## Dados

`LexicalEntry` (tabela `lexical_lexicalentry`):

| Campo | Tipo |
| --- | --- |
| `word`, `normalized_word` | char 255 |
| `language` | char 10 |
| `data` | JSON `{"definitions": [...]}` |
| `source` | char 100 (`dictionary`) |
| `created_at`, `updated_at` | auto |

- Único (`normalized_word`, `language`). Índice (`language`, `normalized_word`).
- Grava com `bulk_create` + upsert (`update_conflicts`).
- `data` em JSON: guarda formato de qualquer provedor sem criar tabela nova.

Redis:

- Chave `lexical:{lang}:{palavra}` (ex.: `lexical:en:architecture`). Valor JSON `{word, definitions, source}`. TTL `LEXICAL_CACHE_TTL_SECONDS`.
- Redis fora: leitura vira MISS, escrita ignorada. API segue funcionando.

## Endpoints

Sem barra final. Sem auth, sem throttle. Resposta só JSON.

`GET /health` → 200 `{"status": "ok", "checks": {"database": true, "redis": true}}`. Algum `false` → 503, `"status": "unhealthy"`. Redis com timeout 1 s.

`POST /api/v1/images/analyze`: `multipart/form-data`, campo `file`.

```json
{
  "ocr": { "text": "The quick fox" },
  "words": [
    { "word": "fox", "definitions": ["..."], "source": "dictionary" }
  ]
}
```

- `words` em ordem alfabética. `source`: `cache` | `database` | `dictionary`.
- 400: `{"file": ["<mensagem pt-BR>"]}`.

`/admin/`: Django admin. `LexicalEntry` com busca por palavra, filtro por idioma e fonte.

## Config (env)

`.env` criado do `.env.example`, fora do git. Env lido só em `config/settings.py`; código usa `django.conf.settings`.

| Var | Padrão | Nota |
| --- | --- | --- |
| `DJANGO_SECRET_KEY` | inseguro, só dev | |
| `DJANGO_DEBUG` | `False` | |
| `DJANGO_ALLOWED_HOSTS` | `localhost,127.0.0.1` | separado por vírgula |
| `POSTGRES_DB`, `_USER`, `_PASSWORD` | `tagarela` | |
| `POSTGRES_HOST`, `_PORT` | `localhost`, `5432` | compose: `db` |
| `REDIS_URL` | `redis://localhost:6379/0` | compose: `redis` |
| `OCR_MAX_IMAGE_SIZE_BYTES` | 10 MB | |
| `LEXICAL_LANGUAGE` | `en` | idioma do dicionário + chave Redis |
| `LEXICAL_CACHE_TTL_SECONDS` | 86400 (24 h) | |
| `DICTIONARY_API_BASE_URL` | `https://api.dictionaryapi.dev/api/v2/entries` | |
| `DICTIONARY_API_TIMEOUT_SECONDS` | 5 | |

Fixo em settings (sem env): content types e formatos aceitos, `LANGUAGE_CODE` pt-br, `TIME_ZONE` America/Sao_Paulo.

## Rodar e inspecionar

Subir: `README.md`. Comandos via `docker compose exec`:

- Testes: `api python manage.py test`. Cobertura: `api sh -c "pip install -r requirements-dev.txt && coverage run manage.py test && coverage report"`.
- Migration: `api python manage.py makemigrations` / `migrate`.
- Admin: `api python manage.py createsuperuser` → http://localhost:8000/admin/.
- Postgres: `db psql -U <POSTGRES_USER> -d <POSTGRES_DB>` → `SELECT id, word, normalized_word, language, source, data, created_at FROM lexical_lexicalentry ORDER BY id DESC;`
- Redis: `redis redis-cli KEYS 'lexical:*'`, `redis redis-cli GET 'lexical:en:<palavra>'`.
- Postman: POST, Body → form-data, key `file` tipo File. Content-Type automático.

Formato e análise: fora do container (ruff não está na imagem). Venv local: `python -m venv .venv` → `pip install -r requirements-dev.txt` → `ruff format .`, `ruff check --fix .`.

Servidor = `runserver` (dev, hot reload pelo volume `.:/app`). Sem setup de produção.

## Convenções

- Código (nomes, classes) em inglês. Texto pro usuário (erro) e docs em pt-BR.
- Import absoluto: `apps.<app>.<módulo>`, `config.<módulo>`.
- Formato e análise: ruff (`pyproject.toml`). Regras padrão do ruff (menos RUF012), linha 100, migrations fora.
- Aspas duplas. Type hints nas assinaturas.
- View: função com `@api_view`.
- Nomes: `<X>Provider` (externo), `<X>Service` (regra), `<X>Serializer`, `<X>Cache`.
- Dependência injetável: construtor recebe opcional, padrão real (`self.cache = cache or LexicalCache()`).
- Falha de dependência opcional (Redis, dicionário): provider/cache trata e segue. Não derruba a requisição.

## Testes

- Runner do Django (`manage.py test`). Sem pytest por enquanto. Base: `django.test.TestCase` (banco), `SimpleTestCase` (sem banco), `rest_framework.test.APITestCase` (endpoint).
- Roda no container `api` (precisa do Postgres).
- Arquivo: `apps/<app>/tests.py`. Cresceu: pacote `apps/<app>/tests/` (`__init__.py` + `test_<módulo>.py`).
- Nunca Paddle, rede ou Redis reais: fake via construtor. View: `unittest.mock.patch("apps.ocr.views.ImageAnalysisService")`. Dicionário: `httpx` mockado + payload fixo.
- Unit: normalização, validator, parse do provider, lookup (ordem cache → banco → dicionário, `source`).
- API: status + corpo (200, 400).
- Código novo ou alterado: teste junto. Bug corrigido: teste que reproduz o bug.
- Hoje: nenhum teste.

## Dependências

- Antes de adicionar pacote: checar PyPI (último release, manutenção), issues abertas, compatibilidade com Python 3.12 e Paddle. Contar ao usuário antes de instalar. Pacote nativo, pesado ou pouco mantido: perguntar.
- `requirements.txt` com faixa `>=x,<y`. Exceção: `paddlepaddle` fixo.
- `requirements-dev.txt`: ferramenta de dev e esteira, nunca na imagem. `ruff` fixo (versão nova muda formatação): subiu = `ruff format .` + `ruff check .` no mesmo PR.
- Lib de sistema nova: `Dockerfile` junto.

## Git e CI

- Repo `tagarela-app-group/tagarela-ocr-dictionary`.
- Branches: `main` = produção. `develop` = integração. Cada mudança = branch nova a partir da `develop`: `feat/`, `fix/`, `docs/`, `ci/`, `chore/` + nome curto.
- Fluxo: branch → commit → push → PR pra `develop`. Esteira verde → squash merge, branch apagada. Release: PR `develop` → `main` (merge commit), aprovado pelo usuário.
- Commit: Conventional Commits em pt-BR (ex.: `feat: análise de áudio`).
- Esteira: `.github/workflows/ci.yml`. Roda em todo PR e push na `develop`/`main`.
  - Formato, análise, migrations e testes: `ruff format --check`, `ruff check` (antes de instalar Paddle: falha rápido), `manage.py check`, `makemigrations --check --dry-run`, `coverage run manage.py test` com Postgres 16 como service. Cobertura no resumo da rodada + artefato `cobertura` (`coverage.xml`), 7 dias.
  - Dependências vulneráveis: instala `requirements.txt`, congela (`pip freeze`) e roda `pip-audit` no resultado, transitivas incluídas. Vulnerabilidade conhecida reprova o PR.
  - Docker: `docker compose up --build --wait` com `.env.example` e volume vazio (passa pelo initdb) + `GET /health` 200. Falhou: logs do compose na rodada.
- Python da esteira = `PYTHON_VERSION` no workflow = imagem do `Dockerfile`. Subiu um: subir o outro junto.
- Sem lockfile: `requirements.txt` em faixa, esteira instala a última versão dentro dela. Release nova de dependência pode quebrar a esteira sem mudança no código.
- Antes do push, rodar local: `ruff format .`, `ruff check .`, `manage.py test`, `makemigrations --check --dry-run`. Mexeu em Docker/compose: `docker compose up` + `/health` 200.
