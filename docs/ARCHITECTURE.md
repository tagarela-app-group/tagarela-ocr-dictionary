# ARCHITECTURE — Tagarela API

## Stack

- Python 3.12, Django 5.2, Django REST Framework 3.15+.
- PostgreSQL 16 (psycopg 3).
- Auth: django-allauth 65 headless (cliente `app`), token JWT HS256. Login social: Google e Apple.
- Local: Docker Compose (`api`, `db`, `mailpit`). Imagem `python:3.12-slim` + lib de sistema `libpq5` (Postgres).

## Decisão: monólito modular

Um backend Django, responsabilidade separada por app. Sem microserviço: projeto no início, microserviço = complexidade em deploy, comunicação, logs, observabilidade, rede, manutenção, testes.

Auth: allauth dentro do monólito (app `accounts`). Better Auth descartado: lib TypeScript, exigiria serviço Node separado (2º runtime e deploy). Port Python dele ainda imaturo (1ª versão em 09/2026, 1 mantenedor).

Texto da foto e do áudio: extraído no celular (repo do app). A API recebe só o texto, nunca arquivo. OCR (PaddleOCR), transcrição (faster-whisper), fila (Celery + Redis) e dicionário saíram em 2026-10-24: o app parou de usar, e a imagem carregava GBs de modelo. Trabalho pesado novo (ex.: IA da ficha do termo): decidir fila na hora.

Princípios: Postgres é a verdade. Estrutura simples, sem camada extra sem necessidade.

## Pastas

```
config/                    settings, urls raiz, health.py (GET /health), tests.py (health), wsgi/asgi
apps/
  common/                  peças compartilhadas sem model
    serializers.py         StrictSerializer (campo desconhecido = 400)
  accounts/                conta e login (allauth headless)
    models.py              User (login por e-mail, `name`, sem username), UserManager
    forms.py               SignupForm (`name` no cadastro), forms do admin
    adapters.py            AccountAdapter (aviso de conta existente sem link), SocialAccountAdapter (`name` do Google)
    templates/account/email/  e-mails pt-BR (base, código, conta existente)
    admin.py               User no admin
    tests/                 fluxos de auth, model, admin
  captures/                rascunho do que a pessoa capturou (texto, foto, áudio) até confirmar a análise
    models.py              Capture, CaptureTerm
    serializers.py         entrada (estrita) e saída
    services.py            CaptureService (criar, editar, confirmar, descartar), CaptureConflict (409)
    views.py, urls.py      rotas /api/v1/captures
    admin.py               Capture (termos inline) no admin
    tests/                 testes do app (helpers.py: usuário, captura)
docs/                      PRODUCT, ARCHITECTURE
.github/workflows/ci.yml   esteira
pyproject.toml             config do ruff e coverage (sem dependência)
requirements.txt           dependências da app (imagem)
requirements-dev.txt       ruff, coverage, pip-audit (fora da imagem)
```

- Dependência entre apps: `captures` → `common`. `common` não depende de ninguém. `accounts` não depende de ninguém. App que precisar de usuário: `get_user_model()` / `settings.AUTH_USER_MODEL`, nunca import direto de `accounts.models`.
- `accounts` sem rota própria (sem `urls.py`). Rotas do allauth: `include` em `config/urls.py`.

## Onde colocar

- Endpoint: view em `apps/<app>/views.py` + `apps/<app>/urls.py` + `include` em `config/urls.py` sob `api/v1/<recurso>/`.
- Validação de entrada: serializer herdando `StrictSerializer` (`apps.common.serializers`): campo desconhecido = 400, junto com os outros erros. Vale pra body e query. Regra reutilizável: `validators.py`. Limite: setting.
- Regra de negócio, orquestração: `services.py`.
- Lib/serviço externo: `providers/<nome>.py`. Trocar provedor = mexer só no provider.
- Auth (cadastro, login, e-mail, social): config `ACCOUNT_*` / `SOCIALACCOUNT_*` / `HEADLESS_*` em `config/settings.py`. Código só em `apps/accounts/` (adapter, form, template). allauth não aparece fora daí.
- Tabela: `models.py` + migration + registro em `admin.py`.
- Setting: env → `config/settings.py` → `.env.example` + tabela Config abaixo.
- Transversal (health, settings, urls raiz): `config/`.
- Módulo novo (ex.: `vocabulary`): app novo `apps/<nome>/` em `INSTALLED_APPS`, mesma estrutura dos atuais.

## Fluxo

Captura: app cria com o texto (`POST captures` com `text`; foto e áudio: texto já extraído no celular) → `ready`. Arquivo nunca sobe. Depois: app salva texto editado e termos (`PATCH`) → confirma (`POST confirm`, `analyzed`).

## Captura (`captures`)

- Rascunho do que a pessoa capturou. Offline first: nasce no celular, o app sincroniza quando tiver internet. `id` = UUID gerado no app: mesmo `id` de novo = 200 com o que já existe (envio repetido não duplica). `id` de outro usuário = 409.
- Status: `ready` → `analyzed` (confirmou a análise). Nasce sempre `ready`, com o texto (digitado ou extraído no celular).
- Texto e termos: `text` = atual (editável), `original_text` = o que veio do celular (digitado ou extraído). Termo = trecho do texto (`text`, `start`, `end` em caracteres). Palavra e expressão que a contém coexistem ("mind" e "mind the gap"). `PATCH` com `terms` troca a lista toda; só `text` mantém os termos que ainda batem no mesmo lugar. Edita só em `ready`.
- Confirmar: exige 1+ termo → `analyzed` (`analyzed_at`). De novo em `analyzed`: 200. A IA que monta a ficha de cada termo entra depois.
- Descartar: só marca `discarded_at`. Registro fica no banco; some da lista e do detalhe. Sincronização (`updated_since`) traz o descarte, pro outro aparelho apagar.

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
- Rotas `/api/v1`: exigem `Authorization: Bearer <access_token>`. Padrão do DRF em `REST_FRAMEWORK`: `JWTTokenAuthentication` do allauth + `IsAuthenticated`. Sem token, token inválido ou vencido: 401 (`WWW-Authenticate: Bearer`). Rota nova nasce protegida; aberta só com `AllowAny` explícito.
- Abertas: `/health` (monitoramento, sem dado de usuário), `/admin/` (login próprio do Django), `/api/auth/*` (o próprio login).

## Dados

`User` (tabela `accounts_user`): `email` (único), `name` (char 150, pode vazio), `password`, `is_active`, `is_staff`, `is_superuser`, `last_login`, `date_joined`. Tabelas do allauth: `account_emailaddress` (e-mail + `verified`), `socialaccount_socialaccount` (vínculo Google/Apple por `uid`).

`Capture` (tabela `captures_capture`): `id` (UUID do app), `user`, `source` (`text`, `audio`, `photo`), `status`, `original_text`, `text`, `captured_at` (hora no celular), `processed_at`, `analyzed_at`, `discarded_at`, `created_at`, `updated_at`. Índice (`user`, `updated_at`).

`CaptureTerm` (tabela `captures_captureterm`): `capture`, `text` (char 255), `start`, `end`. Único (`capture`, `start`, `end`). Ordem: `start`, depois o maior primeiro.

Migration `captures.0002`: apagou as capturas sem texto (`waiting_file`, `processing`, `failed`, só do dev) e a tabela `lexical_lexicalentry` do dicionário que saiu.

## Endpoints

Sem barra final. Sem throttle. Resposta só JSON. `/api/v1` exige login (Bearer, seção Auth). Rotas de auth: seção Auth.

`GET /health` → 200 `{"status": "ok", "checks": {"database": true}}`. Algum `false` → 503, `"status": "unhealthy"`.

Captura (`/api/v1/captures`). Erro de validação: 400 `{"campo": ["<mensagem pt-BR>"]}`. Conflito de estado: 409 `{"detail": "..."}`. De outro usuário ou descartada: 404.

| Rota | Corpo | Resposta |
| --- | --- | --- |
| `POST /api/v1/captures` | JSON `{id, source, captured_at, text}`. `text` obrigatório em qualquer `source`, até `CAPTURE_MAX_TEXT_LENGTH` (foto e áudio: texto extraído no celular). Nasce `ready` | 201 nova, 200 já existia, 409 `id` de outro usuário |
| `GET /api/v1/captures` | query `updated_since?` (ISO 8601), `cursor?` | 200 `{next, previous, results}`. Mais recente (`updated_at`) primeiro, `CAPTURE_PAGE_SIZE` por página. Sem `updated_since`: sem as descartadas. Com: tudo que mudou desde então, descartadas incluídas |
| `GET /api/v1/captures/{id}` | | 200 |
| `PATCH /api/v1/captures/{id}` | JSON `{text?, terms?: [{text, start, end}]}`, ao menos um. Até `CAPTURE_MAX_TERMS` termos de até `CAPTURE_MAX_TERM_LENGTH` | 200. 400 termo que não bate com o texto ou repetido. 409 já `analyzed` |
| `POST /api/v1/captures/{id}/confirm` | | 200 `analyzed` (de novo: 200). 400 sem termo |
| `DELETE /api/v1/captures/{id}` | | 204, mesmo se já descartada |

Captura na resposta:

```json
{
  "id": "0b8f…", "source": "photo", "status": "ready",
  "text": "MIND THE GAP", "original_text": "MIND THE GAP",
  "terms": [{ "text": "MIND THE GAP", "start": 0, "end": 12 }],
  "captured_at": "…", "processed_at": "…", "analyzed_at": null,
  "discarded_at": null, "created_at": "…", "updated_at": "…"
}
```

`/admin/`: Django admin. `Capture` com busca por texto e e-mail, filtro por tipo e status, termos na própria tela.

## Config (env)

`.env` criado do `.env.example`, fora do git. Env lido só em `config/settings.py`; código usa `django.conf.settings`.

| Var | Padrão | Nota |
| --- | --- | --- |
| `DJANGO_SECRET_KEY` | inseguro, só dev | |
| `DJANGO_DEBUG` | `False` | |
| `DJANGO_ALLOWED_HOSTS` | `localhost,127.0.0.1` | separado por vírgula. `.env.example` inclui `10.0.2.2` (emulador Android). Celular físico: IP do PC na rede |
| `POSTGRES_DB`, `_USER`, `_PASSWORD` | `tagarela` | |
| `POSTGRES_HOST`, `_PORT` | `localhost`, `5432` | compose: `db` |
| `CAPTURE_MAX_TEXT_LENGTH` | 2000 | texto digitado, extraído ou editado |
| `CAPTURE_MAX_TERMS` | 50 | termos por captura |
| `CAPTURE_MAX_TERM_LENGTH` | 100 | caracteres por termo |
| `CAPTURE_PAGE_SIZE` | 50 | |
| `AUTH_ACCESS_TOKEN_TTL_SECONDS` | 300 (5 min) | |
| `AUTH_REFRESH_TOKEN_TTL_SECONDS` | 2592000 (30 dias) | |
| `AUTH_CODE_TTL_SECONDS` | 900 (15 min) | código de e-mail e de reset |
| `GOOGLE_CLIENT_ID` | vazio (desligado) | client ID web |
| `APPLE_CLIENT_ID` | vazio (desligado) | bundle ID iOS, lista por vírgula |
| `EMAIL_BACKEND` | console | `.env.example`: SMTP (`django.core.mail.backends.smtp.EmailBackend`) pro Mailpit |
| `EMAIL_HOST`, `_PORT`, `_HOST_USER`, `_HOST_PASSWORD`, `_USE_TLS` | `localhost`, 587, vazio, vazio, `True` | `.env.example`: `mailpit`, 1025, `False`. API fora do Docker: `localhost` |
| `DEFAULT_FROM_EMAIL` | `Tagarela <nao-responda@localhost>` | |

Fixo em settings (sem env): `LANGUAGE_CODE` pt-br, `TIME_ZONE` America/Sao_Paulo.

## Rodar e inspecionar

Subir: `README.md`. Comandos via `docker compose exec`:

- Testes: `api python manage.py test`. Cobertura: `api sh -c "pip install -r requirements-dev.txt && coverage run manage.py test && coverage report"`.
- Migration: `api python manage.py makemigrations`. `migrate` roda sozinho na subida do `api`.
- Admin: `api python manage.py createsuperuser` (pede e-mail) → http://localhost:8000/admin/.
- Código de verificação/reset no dev: Mailpit em http://localhost:8025 (e-mail renderizado, texto, cabeçalhos e checagem de compatibilidade do HTML).
- Capturas: `db psql -U <POSTGRES_USER> -d <POSTGRES_DB>` → `SELECT id, source, status, text, updated_at FROM captures_capture ORDER BY updated_at DESC;`
- Ambiente de antes da limpeza (com `worker` e `redis`): `docker compose up --build --remove-orphans`. Volumes velhos: `docker volume rm api_capture_uploads api_whisper_models`.

Formato e análise: fora do container (ruff não está na imagem). Venv local: `python -m venv .venv` → `pip install -r requirements-dev.txt` → `ruff format .`, `ruff check --fix .`.

Compose: `api` só sobe com `db` healthy. Healthcheck `pg_isready -h 127.0.0.1`: `-h` força TCP, porque no initdb o servidor temporário só aceita socket local e daria falso pronto.

Servidor = `runserver` (dev, hot reload pelo volume `.:/app`). Subida do `api`: `migrate` e depois `runserver`. Migration falhou: container para, erro em `docker compose logs api`. Sem setup de produção (lá, `migrate` vai num passo de deploy, fora do servidor).

## Convenções

- Código (nomes, classes) em inglês. Texto pro usuário (erro) e docs em pt-BR.
- Import absoluto: `apps.<app>.<módulo>`, `config.<módulo>`.
- Formato e análise: ruff (`pyproject.toml`). Regras padrão do ruff, linha 100, migrations fora (geradas pelo Django). RUF012 desligada: Django declara `Meta` (constraints, indexes) com lista.
- Aspas duplas. Type hints nas assinaturas.
- View: função com `@api_view` (um método) ou `APIView` (vários métodos na mesma rota).
- Nomes: `<X>Provider` (externo), `<X>Service` (regra), `<X>Serializer`.
- Dependência injetável: construtor recebe opcional, padrão real (`self.provider = provider or XProvider()`).
- Falha de serviço externo opcional: provider trata e segue. Não derruba a requisição.

## Testes

- Runner do Django (`manage.py test`). Sem pytest por enquanto. Base: `django.test.TestCase` (banco), `SimpleTestCase` (sem banco), `rest_framework.test.APISimpleTestCase` (endpoint sem banco), `APITestCase` (endpoint com banco).
- Roda no container `api` (precisa do Postgres).
- Arquivo: pacote `apps/<app>/tests/` (`__init__.py` + `test_<módulo>.py`). Transversal (`config/`): `config/tests.py`. Helper compartilhado no pacote do app (ex.: `apps/captures/tests/helpers.py`).
- Auth: fluxo inteiro pelo client do Django em `/api/auth/app/v1`. Código lido de `mail.outbox`. `cache.clear()` no `setUp` (rate limit do allauth fica no cache). Google/Apple: `patch` da validação do id_token (`allauth.socialaccount.providers.google.views._verify_and_decode`, `AppleOAuth2Adapter.get_verified_identity_data`).
- Nunca rede real: fake via construtor ou `patch`. Health: `patch` de `config.health.connections`.
- Captura: `make_user`, `make_capture` em `apps/captures/tests/helpers.py`.
- API: status + corpo (200, 400, 401). Endpoint com login: `self.client.force_authenticate(get_user_model()(email=...))` no `setUp`; Bearer de verdade só no teste de auth.
- Código novo ou alterado: teste junto. Bug corrigido: teste que reproduz o bug.
- Cobertos: `GET /health`, auth (cadastro + código, login, e-mail não verificado, reset, refresh, logout, Google, Apple, token inválido, anti-enumeração, Bearer nas rotas `/api/v1` (401 sem token ou token inválido, 200 com o access do login), e-mails em texto e HTML com o código e a validade), `User` (manager, display, admin), `StrictSerializer`, captura (criar, sem texto em qualquer fonte, id repetido e de outro usuário, campos e valores inválidos, lista com cursor e `updated_since`, detalhe, termos com palavra dentro de expressão, editar texto mantendo termos, termo que não bate, 409 em `analyzed`, confirmar, descartar).

## Dependências

- Antes de adicionar pacote: checar PyPI (último release, manutenção), issues abertas, compatibilidade com Python 3.12. Contar ao usuário antes de instalar. Pacote nativo, pesado ou pouco mantido: perguntar.
- `requirements.txt` com faixa `>=x,<y`.
- `requirements-dev.txt`: ferramenta de dev e esteira, nunca na imagem. `ruff` fixo (versão nova muda formatação): subiu = `ruff format .` + `ruff check .` no mesmo PR.
- Lib de sistema nova: `Dockerfile` junto.

## Git e CI

- Repo `tagarela-app-group/tagarela-ocr-dictionary`.
- Branches: `main` = produção. `develop` = integração. Cada mudança = branch nova a partir da `develop`: `feat/`, `fix/`, `docs/`, `ci/`, `chore/` + nome curto.
- Fluxo: branch → commit → push → PR pra `develop`. Esteira verde → squash merge, branch apagada. Release: PR `develop` → `main` (merge commit), aprovado pelo usuário.
- Commit: Conventional Commits em pt-BR (ex.: `feat: análise de áudio`).
- Esteira: `.github/workflows/ci.yml`. Roda em todo PR e push na `develop`/`main`. Push novo no mesmo PR cancela a rodada anterior.
  - Formato, análise, migrations e testes: `ruff format --check`, `ruff check` (antes de instalar as dependências: falha rápido), `manage.py check`, `makemigrations --check --dry-run`, `coverage run manage.py test` com Postgres 16 como service (credenciais = padrão do `config/settings.py`, sem env). Cobertura no resumo da rodada + artefato `cobertura` (`coverage.xml`), 7 dias.
  - Dependências vulneráveis: instala `requirements.txt`, congela (`pip freeze`, antes de instalar o pip-audit) e roda `pip-audit` no resultado, transitivas incluídas. Motivo: `requirements.txt` em faixa, então audita o que o pip resolveu. Vulnerabilidade conhecida reprova o PR.
  - Docker: `docker compose up --build --wait` com `.env.example` e volume vazio (passa pelo initdb) + `GET /health` 200. Falhou: logs do compose na rodada.
- Python da esteira = `PYTHON_VERSION` no workflow = imagem do `Dockerfile`. Subiu um: subir o outro junto.
- Sem lockfile: `requirements.txt` em faixa, esteira instala a última versão dentro dela. Release nova de dependência pode quebrar a esteira sem mudança no código.
- Antes do push, rodar local: `ruff format .`, `ruff check .`, `manage.py test`, `makemigrations --check --dry-run`. Mexeu em Docker/compose: `docker compose up` + `/health` 200.
