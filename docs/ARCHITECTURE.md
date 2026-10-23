# ARCHITECTURE — Tagarela API

## Stack

- Python 3.12, Django 5.2, Django REST Framework 3.15+.
- PostgreSQL 16 (psycopg 3). Redis 7 (só cache).
- OCR: PaddleOCR 3 + PaddlePaddle 3.2.0 CPU (índice extra `paddlepaddle.org.cn` no `requirements.txt`). Pillow valida imagem.
- HTTP externo: httpx.
- Auth: django-allauth 65 headless (cliente `app`), token JWT HS256. Login social: Google e Apple.
- Local: Docker Compose (`api`, `db`, `redis`). Imagem `python:3.12-slim` + libs de sistema `libglib2.0-0 libgl1 libgomp1` (Paddle/OpenCV) e `libpq5` (Postgres).

## Decisão: monólito modular

Um backend Django, responsabilidade separada por app. Sem microserviço: projeto no início, microserviço = complexidade em deploy, comunicação, logs, observabilidade, rede, manutenção, testes. OCR ou áudio precisar escalar separado: extrair o módulo.

Auth: allauth dentro do monólito (app `accounts`). Better Auth descartado: lib TypeScript, exigiria serviço Node separado (2º runtime e deploy). Port Python dele ainda imaturo (1ª versão em 09/2026, 1 mantenedor).

Princípios: local antes de externo (cache → banco → API). Redis descartável, Postgres é a verdade. Estrutura simples, sem camada extra sem necessidade.

## Pastas

```
config/                    settings, urls raiz, health.py (GET /health), tests.py (health), wsgi/asgi
apps/
  accounts/                conta e login (allauth headless)
    models.py              User (login por e-mail, `name`, sem username), UserManager
    forms.py               SignupForm (`name` no cadastro), forms do admin
    adapters.py            AccountAdapter (aviso de conta existente sem link), SocialAccountAdapter (`name` do Google)
    templates/account/email/  e-mails pt-BR (base, código, conta existente)
    admin.py               User no admin
    tests/                 fluxos de auth, model, admin
  ocr/                     imagem → validação → texto. Orquestra a análise
    providers/paddle.py    único lugar que conhece PaddleOCR
    validators.py          validação do upload
    serializers.py         ImageAnalyzeSerializer
    services.py            ImageAnalysisService (OCR + lexical)
    views.py, urls.py      analyze_image
    tests/                 testes do app (images.py: helper de upload)
  lexical/                 texto → palavras → definição
    providers/dictionary.py  único lugar que conhece a API de dicionário
    cache.py               LexicalCache (Redis)
    models.py              LexicalEntry
    services.py            LexicalPreparationService, LexicalLookupService
    admin.py               LexicalEntry no admin
    tests/                 testes do app
docs/                      PRODUCT, ARCHITECTURE
.github/workflows/ci.yml   esteira
pyproject.toml             config do ruff e coverage (sem dependência)
requirements.txt           dependências da app (imagem)
requirements-dev.txt       ruff, coverage, pip-audit (fora da imagem)
```

- Dependência entre apps: `ocr` → `lexical`. Nunca o contrário. `accounts` não depende de ninguém. App que precisar de usuário: `get_user_model()` / `settings.AUTH_USER_MODEL`, nunca import direto de `accounts.models`.
- `lexical` e `accounts` sem rota própria (sem `urls.py`). Rotas do allauth: `include` em `config/urls.py`.
- Stubs vazios do Django: `ocr/models.py`, `ocr/admin.py`, `lexical/views.py`, `lexical/serializers.py`.

## Onde colocar

- Endpoint: view em `apps/<app>/views.py` + `apps/<app>/urls.py` + `include` em `config/urls.py` sob `api/v1/<recurso>/`.
- Validação de entrada: serializer. Regra reutilizável: `validators.py`.
- Regra de negócio, orquestração: `services.py`.
- Lib/serviço externo: `providers/<nome>.py`. Trocar provedor = mexer só no provider.
- Cache: `cache.py` do app.
- Auth (cadastro, login, e-mail, social): config `ACCOUNT_*` / `SOCIALACCOUNT_*` / `HEADLESS_*` em `config/settings.py`. Código só em `apps/accounts/` (adapter, form, template). allauth não aparece fora daí.
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

## Auth (`accounts`)

- allauth headless, cliente `app`. Base: `/api/auth/app/v1`. Formato de resposta, erros e flows: do allauth (`data`, `meta`, `errors[].param`, `data.flows[].is_pending`).
- Usuário: `accounts.User` (`AUTH_USER_MODEL`). E-mail único em minúsculo, `name`, sem username. `display` na resposta = `name` ou, vazio, e-mail.
- Usuário na resposta (`data.user`): campos do allauth (`id`, `display`, `email`, `has_usable_password`) + `name` e `picture` (`HeadlessAdapter.serialize_user`). `picture` = foto da conta social (Google); some quando não há. `name` some quando vazio (Apple sem nome).
- Token: JWT HS256 assinado com `DJANGO_SECRET_KEY`. Access `AUTH_ACCESS_TOKEN_TTL_SECONDS`, refresh `AUTH_REFRESH_TOKEN_TTL_SECONDS`. Refresh rotaciona a cada uso. Trocar `DJANGO_SECRET_KEY` derruba todo login.
- Header: fluxo pendente (verificar e-mail, reset) = `X-Session-Token` (vem em `meta.session_token`). Logado = `Authorization: Bearer <access_token>`.
- Fluxos:
  - Cadastro: `POST auth/signup` `{name, email, password}` → 401, flow `verify_email` pendente, código por e-mail → `POST auth/email/verify` `{key}` → 200 + `meta.access_token`, `meta.refresh_token`.
  - Login: `POST auth/login` `{email, password}` → 200 + tokens. Senha errada → 400. E-mail não verificado → 401 `verify_email` (código novo).
  - Esqueci a senha: `POST auth/password/request` `{email}` → 401, flow `password_reset_by_code` → `GET auth/password/reset` (header `X-Password-Reset-Key: <código>`) valida → `POST auth/password/reset` `{key, password}` → 200 + tokens.
  - Google/Apple: login nativo no app → `POST auth/provider/token` `{provider, process: "login", token: {client_id, id_token}}` → 200 + tokens. Backend valida assinatura e `aud` do `id_token`.
  - Renovar: `POST tokens/refresh` `{refresh_token}` → 200, novo par em `data`.
  - Sessão: `GET auth/session` (Bearer) → usuário. Sair: `DELETE auth/session` (Bearer) → 401, refresh deixa de valer. Access vale até expirar.
- Código: 6 dígitos, vale `AUTH_CODE_TTL_SECONDS`, 3 tentativas (padrão do allauth).
- Senha: validadores padrão do Django (mín. 8, não comum, não só número, não parecida com o e-mail). Mensagem pt-BR.
- Anti-enumeração: cadastro com e-mail existente e reset de e-mail desconhecido respondem igual ao caso normal. E-mail existente recebe aviso sem link. E-mail desconhecido não recebe nada (`ACCOUNT_EMAIL_UNKNOWN_ACCOUNTS = False`). Sem link porque não há frontend web (`HEADLESS_ONLY`).
- Social: provider sem client ID na env fica desligado. `GOOGLE_CLIENT_ID` = client ID web (o `serverClientId` do app; é o `aud` do id_token). `APPLE_CLIENT_ID` = bundle ID do iOS (lista por vírgula). Apple só no iOS: Android exigiria fluxo web + endpoint de callback. E-mail verificado pelo provider = entra na conta que já tem esse e-mail. Nome: Google manda; Apple não manda no token (`name` vazio).
- E-mail: dev manda SMTP pro Mailpit do compose (caixa de entrada em http://localhost:8025, porta SMTP 1025, aceita qualquer login). Produção: SMTP real via `EMAIL_*`. Assunto com prefixo `[Tagarela] `. Templates pt-BR sobrescrevem os do allauth (`apps.accounts` antes do allauth em `INSTALLED_APPS`).
- Templates em `apps/accounts/templates/account/email/`: cada mensagem tem `.txt` e `.html` (multipart; o cliente escolhe). HTML em `base_message.html` (tabelas + estilo inline, cores do design system, sem links), código em `code_block.html`. Cadastro usa `email_confirmation_signup_message.*`, que inclui o `email_confirmation_message.*`. `AccountAdapter.send_mail` põe `code_minutes` (de `AUTH_CODE_TTL_SECONDS`) no contexto. Visual validado no mockup (linha E-mails).
- Rate limit: padrão do allauth, guardado no cache do Django (LocMem, por processo).
- `/api/v1` (OCR) continua sem login.

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

`User` (tabela `accounts_user`): `email` (único), `name` (char 150, pode vazio), `password`, `is_active`, `is_staff`, `is_superuser`, `last_login`, `date_joined`. Tabelas do allauth: `account_emailaddress` (e-mail + `verified`), `socialaccount_socialaccount` (vínculo Google/Apple por `uid`).

Redis:

- Chave `lexical:{lang}:{palavra}` (ex.: `lexical:en:architecture`). Valor JSON `{word, definitions, source}`. TTL `LEXICAL_CACHE_TTL_SECONDS`.
- Redis fora: leitura vira MISS, escrita ignorada. API segue funcionando.

## Endpoints

Sem barra final. Sem throttle. Resposta só JSON. `/api/v1` sem auth. Rotas de auth: seção Auth.

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
| `DJANGO_ALLOWED_HOSTS` | `localhost,127.0.0.1` | separado por vírgula. `.env.example` inclui `10.0.2.2` (emulador Android). Celular físico: IP do PC na rede |
| `POSTGRES_DB`, `_USER`, `_PASSWORD` | `tagarela` | |
| `POSTGRES_HOST`, `_PORT` | `localhost`, `5432` | compose: `db` |
| `REDIS_URL` | `redis://localhost:6379/0` | compose: `redis` |
| `OCR_MAX_IMAGE_SIZE_BYTES` | 10 MB | |
| `LEXICAL_LANGUAGE` | `en` | idioma do dicionário + chave Redis |
| `LEXICAL_CACHE_TTL_SECONDS` | 86400 (24 h) | |
| `DICTIONARY_API_BASE_URL` | `https://api.dictionaryapi.dev/api/v2/entries` | |
| `DICTIONARY_API_TIMEOUT_SECONDS` | 5 | |
| `AUTH_ACCESS_TOKEN_TTL_SECONDS` | 300 (5 min) | |
| `AUTH_REFRESH_TOKEN_TTL_SECONDS` | 2592000 (30 dias) | |
| `AUTH_CODE_TTL_SECONDS` | 900 (15 min) | código de e-mail e de reset |
| `GOOGLE_CLIENT_ID` | vazio (desligado) | client ID web |
| `APPLE_CLIENT_ID` | vazio (desligado) | bundle ID iOS, lista por vírgula |
| `EMAIL_BACKEND` | console | `.env.example`: SMTP (`django.core.mail.backends.smtp.EmailBackend`) pro Mailpit |
| `EMAIL_HOST`, `_PORT`, `_HOST_USER`, `_HOST_PASSWORD`, `_USE_TLS` | `localhost`, 587, vazio, vazio, `True` | `.env.example`: `mailpit`, 1025, `False`. API fora do Docker: `localhost` |
| `DEFAULT_FROM_EMAIL` | `Tagarela <nao-responda@localhost>` | |

Fixo em settings (sem env): content types e formatos aceitos, `LANGUAGE_CODE` pt-br, `TIME_ZONE` America/Sao_Paulo.

## Rodar e inspecionar

Subir: `README.md`. Comandos via `docker compose exec`:

- Testes: `api python manage.py test`. Cobertura: `api sh -c "pip install -r requirements-dev.txt && coverage run manage.py test && coverage report"`.
- Migration: `api python manage.py makemigrations`. `migrate` roda sozinho na subida do `api`.
- Admin: `api python manage.py createsuperuser` (pede e-mail) → http://localhost:8000/admin/.
- Código de verificação/reset no dev: Mailpit em http://localhost:8025 (e-mail renderizado, texto, cabeçalhos e checagem de compatibilidade do HTML).
- Postgres: `db psql -U <POSTGRES_USER> -d <POSTGRES_DB>` → `SELECT id, word, normalized_word, language, source, data, created_at FROM lexical_lexicalentry ORDER BY id DESC;`
- Redis: `redis redis-cli KEYS 'lexical:*'`, `redis redis-cli GET 'lexical:en:<palavra>'`.
- Postman: POST, Body → form-data, key `file` tipo File. Content-Type automático.

Formato e análise: fora do container (ruff não está na imagem). Venv local: `python -m venv .venv` → `pip install -r requirements-dev.txt` → `ruff format .`, `ruff check --fix .`.

Compose: `api` só sobe com `db` healthy. Healthcheck `pg_isready -h 127.0.0.1`: `-h` força TCP, porque no initdb o servidor temporário só aceita socket local e daria falso pronto.

Servidor = `runserver` (dev, hot reload pelo volume `.:/app`). Subida do `api`: `migrate` e depois `runserver`. Migration falhou: container para, erro em `docker compose logs api`. Sem setup de produção (lá, `migrate` vai num passo de deploy, fora do servidor).

## Convenções

- Código (nomes, classes) em inglês. Texto pro usuário (erro) e docs em pt-BR.
- Import absoluto: `apps.<app>.<módulo>`, `config.<módulo>`.
- Formato e análise: ruff (`pyproject.toml`). Regras padrão do ruff, linha 100, migrations fora (geradas pelo Django). RUF012 desligada: Django declara `Meta` (constraints, indexes) com lista.
- Aspas duplas. Type hints nas assinaturas.
- View: função com `@api_view`.
- Nomes: `<X>Provider` (externo), `<X>Service` (regra), `<X>Serializer`, `<X>Cache`.
- Dependência injetável: construtor recebe opcional, padrão real (`self.cache = cache or LexicalCache()`).
- Falha de dependência opcional (Redis, dicionário): provider/cache trata e segue. Não derruba a requisição.

## Testes

- Runner do Django (`manage.py test`). Sem pytest por enquanto. Base: `django.test.TestCase` (banco), `SimpleTestCase` (sem banco), `rest_framework.test.APISimpleTestCase` (endpoint sem banco), `APITestCase` (endpoint com banco).
- Roda no container `api` (precisa do Postgres).
- Arquivo: pacote `apps/<app>/tests/` (`__init__.py` + `test_<módulo>.py`). Transversal (`config/`): `config/tests.py`. Helper compartilhado no pacote do app (ex.: `apps/ocr/tests/images.py`).
- Auth: fluxo inteiro pelo client do Django em `/api/auth/app/v1`. Código lido de `mail.outbox`. `cache.clear()` no `setUp` (rate limit do allauth fica no cache). Google/Apple: `patch` da validação do id_token (`allauth.socialaccount.providers.google.views._verify_and_decode`, `AppleOAuth2Adapter.get_verified_identity_data`).
- Nunca Paddle, rede ou Redis reais: fake via construtor. View: `unittest.mock.patch("apps.ocr.views.ImageAnalysisService")`. Dicionário: `httpx.get` mockado + payload fixo. Paddle: `patch.object(PaddleOCRProvider, "_engine", fake)`. Redis: client `MagicMock`. Health: `patch` de `config.health.connections` e `config.health.Redis`.
- Unit: normalização, validator, parse do provider, lookup (ordem cache → banco → dicionário, `source`).
- API: status + corpo (200, 400).
- Código novo ou alterado: teste junto. Bug corrigido: teste que reproduz o bug.
- Cobertos: normalização, lookup (ordem, `source`, idioma, gravação), cache, provider do dicionário, provider do Paddle (sem engine real), validator, service de imagem, `POST /api/v1/images/analyze`, `GET /health`, auth (cadastro + código, login, e-mail não verificado, reset, refresh, logout, Google, Apple, token inválido, anti-enumeração, e-mails em texto e HTML com o código e a validade), `User` (manager, display, admin). Fora: criação do engine Paddle (carrega modelo real).

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
- Esteira: `.github/workflows/ci.yml`. Roda em todo PR e push na `develop`/`main`. Push novo no mesmo PR cancela a rodada anterior.
  - Formato, análise, migrations e testes: `ruff format --check`, `ruff check` (antes de instalar Paddle: falha rápido), `manage.py check`, `makemigrations --check --dry-run`, `coverage run manage.py test` com Postgres 16 como service (credenciais = padrão do `config/settings.py`, sem env). Cobertura no resumo da rodada + artefato `cobertura` (`coverage.xml`), 7 dias.
  - Dependências vulneráveis: instala `requirements.txt`, congela (`pip freeze`, antes de instalar o pip-audit) e roda `pip-audit` no resultado, transitivas incluídas. Motivo: `requirements.txt` em faixa, então audita o que o pip resolveu. Vulnerabilidade conhecida reprova o PR.
  - Docker: `docker compose up --build --wait` com `.env.example` e volume vazio (passa pelo initdb) + `GET /health` 200. Falhou: logs do compose na rodada.
- Python da esteira = `PYTHON_VERSION` no workflow = imagem do `Dockerfile`. Subiu um: subir o outro junto.
- Sem lockfile: `requirements.txt` em faixa, esteira instala a última versão dentro dela. Release nova de dependência pode quebrar a esteira sem mudança no código.
- Antes do push, rodar local: `ruff format .`, `ruff check .`, `manage.py test`, `makemigrations --check --dry-run`. Mexeu em Docker/compose: `docker compose up` + `/health` 200.
