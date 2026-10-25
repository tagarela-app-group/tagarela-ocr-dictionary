# CLAUDE.md — Tagarela API

Backend Django REST do Tagarela (app Flutter: repo `tagarela-app-group/tagarela`, pasta `../mob`). Guarda conta, capturas (só texto) e vocabulário. Não processa foto nem áudio.

## Produto

- Conta: e-mail único verificado por código + nome. Senha, Google ou Apple. Mesmo e-mail = mesma conta.
- Captura: rascunho com texto. Pessoa escolhe termos, corrige texto, confirma.
- Termo: palavra ou expressão confirmada, um por pessoa. Grupo: criado pela pessoa. IA nunca escolhe grupo.
- Falta (o app espera): ficha do termo via IA (tradução, fonética, exemplo), SRS, palavra do dia.

## Regras

1. Antes de alterar qualquer coisa (código, doc, config): propor (o que muda, onde, opções, recomendação) e esperar aprovação.
2. Pedido quebra regra ou boa prática: avisar antes, dizer qual e propor alternativa. Sem camada nova sem necessidade.
3. View fina: serializer valida, service faz, `Response`. Regra de negócio só em service.
4. Toda entrada (body e query): serializer que herda `StrictSerializer` (campo desconhecido = 400).
5. Lib externa só em `providers/`. allauth só em `apps/accounts/` e `config/`.
6. Limite, URL, TTL, idioma: setting (env → `config/settings.py` → `.env.example`). Segredo só no `.env`.
7. Contrato `/api/v1` é público. Não quebrar. Mudança incompatível: avisar + nova versão.
8. Model mudou: migration junto. Nunca editar migration mergeada.
9. Código novo ou alterado: teste junto. Bug corrigido: teste que reproduz. Sem teste: motivo no PR.
10. Sem comentário no código nem em config. Porquê vai neste arquivo ou no PR.
11. Mudou regra, decisão ou armadilha: atualizar este arquivo junto. Teto 8 KB: enxugar antes de somar. Só o que o código não mostra.
12. Task finalizada: branch própria da `develop` (`feat/`, `fix/`, `docs/`, `ci/`, `chore/`), commit, push e PR pra `develop`, na hora, sem perguntar.
13. Commit e PR: Conventional Commits em pt-BR, enxuto, só o necessário. Sem `Co-Authored-By` nem assinatura de IA.
14. PR pra `develop` com esteira verde: merge sozinho com `gh pr merge <n> --repo tagarela-app-group/tagarela-ocr-dictionary --squash --delete-branch` (comando isolado, sem `cd`/`&&`). Depois `git switch develop && git pull`.
15. Só o usuário: merge `develop` → `main` (prod). Nunca commitar direto na `develop` nem na `main`.
16. Fim de task ou troca de assunto: sugerir numa linha `/compact manter: ...` (mesmo assunto) ou `/clear` (assunto novo).

## Onde colocar

- Apps: `common` (StrictSerializer), `accounts`, `captures`, `vocabulary`. Dependência: `captures` → `vocabulary` → `common`.
- Endpoint: `views.py` + `urls.py` do app + `include` em `config/urls.py` sob `api/v1/`. `accounts` sem `urls.py`: allauth em `config/urls.py`.
- Usuário: `get_user_model()` / `settings.AUTH_USER_MODEL`, nunca import de `accounts.models`.
- Tabela: model + migration + `admin.py`.

## Decisões e armadilhas

### Base
- Monólito modular, um app por responsabilidade. Postgres é a verdade.
- allauth no monólito. Better Auth descartado (TypeScript, 2º runtime).
- Foto e áudio: texto extraído no celular. OCR, transcrição, fila e dicionário saíram em 2026-10-24 (imagem com GBs de modelo). Trabalho pesado novo (IA da ficha): decidir fila na hora.
- Contrato: sem barra final, só JSON. Validação: 400 `{"campo": ["msg pt-BR"]}`. Conflito: 409 `{"detail"}`. Formato exato: serializers.
- `/health`: banco fora = 503.

### Captura
- Offline first: `id` UUID do app. Mesmo `id` = 200 com existente. `id` de outro usuário = 409.
- Nasce `ready`. `original_text` = o que veio do celular. Edita só em `ready`.
- Termo = trecho do texto (`start`, `end` em code points). Palavra dentro de expressão vale.
- `PATCH terms` troca a lista. `PATCH text` mantém termos que batem no mesmo lugar.
- Confirmar (1+ termo): `analyzed` + termos no vocabulário, mesma transação.
- Descartar = `discarded_at`. Lista sem `updated_since` omite descartadas. Com: traz pro outro aparelho.

### Vocabulário
- Termo único: `key` = espaços juntados + `casefold`. Já existe: mantém grupo e texto da 1ª vez.
- Grupo: nome único por pessoa (ignora maiúscula). `icon` = slug do app (API não guarda lista). `accent` = 1 de 6 cores.
- Mover e apagar: tudo ou nada. Termo ou grupo de outra pessoa = 400. `group: null` = Sem grupo.
- Apagar grupo: termos vão pra Sem grupo (`SET_NULL`).
- Apagar termo: `deleted_at`. Novo apagar remove de vez os anteriores: só o último restaura. Confirmado de novo: entra como novo.

### Auth
- allauth headless, base `/api/auth/app/v1`, formato do allauth. Pendente (verificar e-mail, reset) = 401 + `X-Session-Token`. Logado = `Bearer`.
- JWT HS256 com `DJANGO_SECRET_KEY`: trocar a chave derruba todo login.
- Anti-enumeração: e-mail existente ou não responde igual. Sem link no e-mail (`HEADLESS_ONLY`).
- Social: sem client ID = desligado. `GOOGLE_CLIENT_ID` = client web (`aud`). `APPLE_CLIENT_ID` = bundle iOS.
- `data.user` ganha `name` e `picture` (`HeadlessAdapter.serialize_user`). E-mails pt-BR em `apps/accounts/templates/account/email/`. Dev: Mailpit http://localhost:8025.
- `/api/v1` exige Bearer. Aberta só com `AllowAny` explícito.

## Código e testes

- Código em inglês, texto pro usuário em pt-BR. Import `apps.<app>.<módulo>`. Ruff, linha 100.
- View: `@api_view` (um método) ou `APIView`. Nomes `<X>Service`, `<X>Provider`, `<X>Serializer`. Injeção: `self.provider = provider or XProvider()`.
- Testes: runner do Django no container, `apps/<app>/tests/test_<módulo>.py`. Nunca rede real.
- Auth: código de `mail.outbox`, `cache.clear()` no `setUp` (rate limit). Google/Apple: `patch` do id_token. Logado: `force_authenticate`.
- Migration de dados: `import_module` + função com `django.apps.apps`.

## Comandos

Subir: `README.md`. No container (`docker compose exec api ...`):

- `python manage.py test -v 0`
- `python manage.py makemigrations` (`migrate` roda na subida)
- Fora do container (venv `requirements-dev.txt`): `ruff format .`, `ruff check --fix .`
- Antes do push: ruff, testes, `makemigrations --check --dry-run`. Mexeu em Docker: `docker compose up` + `/health` 200.
- Healthcheck do `db`: `pg_isready -h 127.0.0.1` (sem `-h`, initdb dá falso pronto).

## Dependências e CI

- Pacote novo: checar PyPI e issues, contar ao usuário. Nativo ou pesado: perguntar.
- `requirements.txt` em faixa, sem lockfile: release nova pode quebrar esteira. `ruff` fixo: subiu = reformatar no mesmo PR. Lib de sistema nova: `Dockerfile` junto.
- Esteira: ruff, `check`, `makemigrations --check`, testes, `pip-audit`, `docker compose up --wait` + `/health`. `PYTHON_VERSION` do workflow = `Dockerfile`.
