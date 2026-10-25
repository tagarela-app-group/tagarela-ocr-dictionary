# ARCHITECTURE — Tagarela API

Mapa técnico. Detalhe fica no código. Aqui só decisão, regra e armadilha.

## Stack

- Python 3.12, Django 5.2, DRF 3.15+, PostgreSQL 16 (psycopg 3).
- Auth: django-allauth 65 headless (cliente `app`), JWT HS256. Login social: Google e Apple.
- Local: Docker Compose (`api`, `db`, `mailpit`).

## Decisões

- Monólito modular: um Django, um app por responsabilidade. Sem microserviço no início.
- allauth dentro do monólito. Better Auth descartado: TypeScript, exigiria 2º runtime e deploy.
- Foto e áudio: texto extraído no celular. API recebe só texto, nunca arquivo. OCR, transcrição, fila e dicionário saíram em 2026-10-24 (imagem com GBs de modelo). Trabalho pesado novo (IA da ficha): decidir fila na hora.
- Postgres é a verdade. Sem camada extra sem necessidade.

## Pastas

```
config/        settings, urls raiz, health.py, tests.py
apps/
  common/      StrictSerializer (campo desconhecido = 400)
  accounts/    User (login por e-mail, `name`), adapters, forms, e-mails pt-BR
  captures/    Capture, CaptureTerm: rascunho até confirmar a análise
  vocabulary/  Group, Term: vocabulário da pessoa
  <app>/       models, serializers, services, views, urls, admin, tests/ (helpers.py)
```

- Dependência: `captures` → `vocabulary` → `common`. `accounts` e `common` não dependem de ninguém.
- Usuário: `get_user_model()` / `settings.AUTH_USER_MODEL`. Nunca import de `accounts.models`.
- `accounts` sem `urls.py`: rotas do allauth em `config/urls.py`.

## Onde colocar

- Endpoint: `views.py` + `urls.py` do app + `include` em `config/urls.py` sob `api/v1/`.
- Entrada (body e query): serializer que herda `StrictSerializer`.
- Regra de negócio: `services.py`. Lib externa: `providers/<nome>.py`.
- Auth: config em `config/settings.py`, código só em `apps/accounts/`.
- Tabela: model + migration + `admin.py`.
- Setting: env → `config/settings.py` → `.env.example`.

## Captura

- Offline first: nasce no celular com `id` UUID do app. Mesmo `id` de novo = 200 com o existente. `id` de outro usuário = 409.
- Nasce `ready` com `text`. `original_text` = o que veio do celular.
- Termo = trecho do texto (`text`, `start`, `end` em code points). Palavra dentro de expressão vale.
- `PATCH terms` troca a lista toda. `PATCH text` mantém os termos que ainda batem no mesmo lugar. Edita só em `ready`.
- Confirmar (1+ termo): `analyzed` e termos entram no vocabulário, na mesma transação.
- Descartar = `discarded_at`. Some da lista. `updated_since` traz o descarte pro outro aparelho.

## Vocabulário

- Termo único por pessoa: `key` = espaços juntados + `casefold`. Já existe: não entra (ficam grupo e texto da 1ª vez).
- Termo nasce sem grupo. Grupo é escolha da pessoa, nunca da IA.
- Grupo: nome único por pessoa, ignora maiúscula. `icon` = slug do catálogo do app (API não guarda a lista). `accent` = uma das 6 cores.
- Mover: tudo ou nada. Termo ou grupo de outra pessoa = 400. `group: null` = Sem grupo.
- Apagar grupo: sem rota ainda. FK `SET_NULL` já solta os termos.

## Auth

- Base `/api/auth/app/v1`. Resposta e erros no formato do allauth.
- Fluxo pendente (verificar e-mail, reset) = 401 + `X-Session-Token`. Logado = `Authorization: Bearer`.
- Rotas: `auth/signup` → código no e-mail → `auth/email/verify`. `auth/login`. `auth/password/request` → `auth/password/reset` (código). `auth/provider/token` (id_token Google/Apple). `tokens/refresh` (rotaciona). `GET`/`DELETE auth/session`.
- JWT assinado com `DJANGO_SECRET_KEY`: trocar a chave derruba todo login.
- Anti-enumeração: e-mail existente ou desconhecido responde igual. E-mail sem link (não há web, `HEADLESS_ONLY`).
- Social: sem client ID na env = desligado. `GOOGLE_CLIENT_ID` = client web (`aud` do id_token). `APPLE_CLIENT_ID` = bundle iOS. Apple só no iOS. Mesmo e-mail verificado = mesma conta.
- `data.user` ganha `name` e `picture` (`HeadlessAdapter.serialize_user`).
- E-mail: templates pt-BR `.txt` + `.html` em `apps/accounts/templates/account/email/`. Dev: Mailpit em http://localhost:8025.
- `/api/v1` exige Bearer por padrão. Rota aberta só com `AllowAny` explícito. Abertas: `/health`, `/admin/`, `/api/auth/*`.

## Endpoints

Contrato público: o app consome. Sem barra final, só JSON. Formato exato: serializers. Validação: 400 `{"campo": ["msg pt-BR"]}`. Conflito: 409 `{"detail"}`.

| Rota | Nota |
| --- | --- |
| `GET /health` | 200. Banco fora: 503 |
| `POST /api/v1/captures` | `{id, source, captured_at, text}`. 201 nova, 200 já existia |
| `GET /api/v1/captures` | `updated_since?`, `cursor?`. Sem `updated_since`: sem as descartadas |
| `GET`/`PATCH`/`DELETE /api/v1/captures/{id}` | `PATCH {text?, terms?}`. `DELETE` 204 |
| `POST /api/v1/captures/{id}/confirm` | 200 `analyzed`. 400 sem termo |
| `GET /api/v1/vocabulary` | `{groups, ungrouped}` |
| `POST /api/v1/groups` | `{name, icon, accent}`. 201. 400 nome repetido |
| `POST /api/v1/terms/move` | `{terms, group}`. 200 com o vocabulário atualizado |

## Comandos

Subir: `README.md`. No container (`docker compose exec api ...`), sempre com saída curta:

- Testes: `python manage.py test -v 0`
- Migration: `python manage.py makemigrations`. `migrate` roda sozinho na subida.
- Formato, fora do container (venv com `requirements-dev.txt`): `ruff format .`, `ruff check --fix .`
- Antes do push: ruff, testes, `makemigrations --check --dry-run`. Mexeu em Docker: `docker compose up` + `/health` 200.
- Healthcheck do `db` usa `pg_isready -h 127.0.0.1`: sem `-h`, o initdb dá falso pronto.

## Convenções

- Código em inglês. Texto pro usuário e docs em pt-BR.
- Import absoluto `apps.<app>.<módulo>`. Aspas duplas, type hints. Ruff, linha 100.
- View: `@api_view` (um método) ou `APIView` (vários). Nomes: `<X>Service`, `<X>Provider`, `<X>Serializer`.
- Dependência injetável: `self.provider = provider or XProvider()`.

## Testes

- Runner do Django, no container (precisa do Postgres). Arquivo: `apps/<app>/tests/test_<módulo>.py`.
- Nunca rede real: fake via construtor ou `patch`.
- Auth: fluxo pelo client, código de `mail.outbox`, `cache.clear()` no `setUp` (rate limit do allauth). Google/Apple: `patch` da validação do id_token.
- Endpoint logado: `force_authenticate` no `setUp`.
- Migration de dados: `import_module` + chamar a função com `django.apps.apps`.

## Dependências

- Antes de pacote novo: checar PyPI e issues, contar ao usuário. Nativo ou pesado: perguntar.
- `requirements.txt` em faixa, sem lockfile: release nova pode quebrar a esteira.
- `requirements-dev.txt` fora da imagem. `ruff` fixo: subiu = reformatar no mesmo PR.
- Lib de sistema nova: `Dockerfile` junto.

## Git e CI

- Repo `tagarela-app-group/tagarela-ocr-dictionary`. Branch da `develop` (`feat/`, `fix/`, `docs/`, `ci/`, `chore/`). PR pra `develop`, squash. Commit: Conventional Commits em pt-BR.
- Esteira: ruff, `check`, `makemigrations --check`, testes com cobertura (Postgres service), `pip-audit` sobre o `pip freeze`, `docker compose up --wait` + `/health`.
- `PYTHON_VERSION` do workflow = imagem do `Dockerfile`. Subiu um, subir o outro.
