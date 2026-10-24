# ARCHITECTURE — Tagarela API

## Stack

- Python 3.12, Django 5.2, Django REST Framework 3.15+.
- PostgreSQL 16 (psycopg 3). Redis 7 (cache do lexical + fila do Celery).
- Fila: Celery 5.6, broker Redis. Processo `worker` separado (mesma imagem).
- OCR: PaddleOCR 3 + PaddlePaddle 3.2.0 CPU (índice extra `paddlepaddle.org.cn` no `requirements.txt`). Pillow valida imagem.
- Transcrição: faster-whisper 1.2 (CTranslate2 na CPU, `int8`, modelo só inglês `.en`). PyAV lê formato, codec e duração do áudio.
- HTTP externo: httpx.
- Auth: django-allauth 65 headless (cliente `app`), token JWT HS256. Login social: Google e Apple.
- Local: Docker Compose (`api`, `worker`, `db`, `redis`, `mailpit`). Imagem `python:3.12-slim` + libs de sistema `libglib2.0-0 libgl1 libgomp1` (Paddle/OpenCV) e `libpq5` (Postgres).

## Decisão: monólito modular

Um backend Django, responsabilidade separada por app. Sem microserviço: projeto no início, microserviço = complexidade em deploy, comunicação, logs, observabilidade, rede, manutenção, testes. OCR ou áudio precisar escalar separado: extrair o módulo.

Auth: allauth dentro do monólito (app `accounts`). Better Auth descartado: lib TypeScript, exigiria serviço Node separado (2º runtime e deploy). Port Python dele ainda imaturo (1ª versão em 09/2026, 1 mantenedor).

Fila: Celery + Redis. Extrair texto (OCR da foto, transcrição do áudio) pesa CPU e leva segundos: roda no `worker`, fora da requisição. Worker prefork mantém os modelos carregados entre tarefas. RQ descartado: processo novo por tarefa recarregaria os modelos. Síncrono descartado: requisição longa em rede móvel e servidor preso.

Princípios: local antes de externo (cache → banco → API). Redis descartável, Postgres é a verdade. Estrutura simples, sem camada extra sem necessidade.

## Pastas

```
config/                    settings, urls raiz, celery.py (app do Celery), health.py (GET /health), tests.py (health), wsgi/asgi
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
  ocr/                     imagem → validação → texto. Orquestra a análise
    providers/paddle.py    único lugar que conhece PaddleOCR
    validators.py          validação do upload
    serializers.py         ImageAnalyzeSerializer
    services.py            ImageAnalysisService (OCR + lexical), TextExtractionService (só o texto, pra captura)
    views.py, urls.py      analyze_image
    tests/                 testes do app (images.py: helper de upload)
  lexical/                 texto → palavras → definição
    providers/dictionary.py  único lugar que conhece a API de dicionário
    cache.py               LexicalCache (Redis)
    models.py              LexicalEntry
    services.py            LexicalPreparationService, LexicalLookupService
    admin.py               LexicalEntry no admin
    tests/                 testes do app
  captures/                rascunho do que a pessoa capturou (texto, foto, áudio) até confirmar a análise
    models.py              Capture, CaptureTerm
    serializers.py         entrada (estrita) e saída
    services.py            CaptureService (criar, receber arquivo, editar, confirmar, descartar), CaptureConflict (409)
    processing.py          CaptureProcessingService (extrai o texto do arquivo, roda no worker)
    tasks.py               process_capture (task do Celery), enqueue_processing
    uploads.py             arquivo temporário em CAPTURE_UPLOAD_DIR (salvar, achar, apagar)
    views.py, urls.py      rotas /api/v1/captures
    admin.py               Capture (termos inline) no admin
    tests/                 testes do app (helpers.py: usuário, captura, pasta de upload temporária)
  transcription/           áudio → validação → texto (pra captura)
    providers/whisper.py   único lugar que conhece faster-whisper
    audio.py               único lugar que conhece PyAV: formato, codec e duração
    validators.py          validação do upload de áudio
    services.py            TranscriptionService
    management/commands/benchmark_transcription.py  mede tempo, CPU e memória por modelo
    tests/                 testes do app (audio.py: gera M4A/WAV de verdade com PyAV, sem arquivo no repo)
docs/                      PRODUCT, ARCHITECTURE
.github/workflows/ci.yml   esteira
pyproject.toml             config do ruff e coverage (sem dependência)
requirements.txt           dependências da app (imagem)
requirements-dev.txt       ruff, coverage, pip-audit (fora da imagem)
```

- Dependência entre apps: `captures` → `ocr` → `lexical`; `captures` → `transcription`. Nunca o contrário. `common` não depende de ninguém. `accounts` não depende de ninguém. App que precisar de usuário: `get_user_model()` / `settings.AUTH_USER_MODEL`, nunca import direto de `accounts.models`.
- `lexical` e `accounts` sem rota própria (sem `urls.py`). Rotas do allauth: `include` em `config/urls.py`.
- Stubs vazios do Django: `ocr/models.py`, `ocr/admin.py`, `lexical/views.py`, `lexical/serializers.py`.

## Onde colocar

- Endpoint: view em `apps/<app>/views.py` + `apps/<app>/urls.py` + `include` em `config/urls.py` sob `api/v1/<recurso>/`.
- Validação de entrada: serializer herdando `StrictSerializer` (`apps.common.serializers`): campo desconhecido = 400, junto com os outros erros. Vale pra body e query. Regra reutilizável: `validators.py`. Limite: setting.
- Regra de negócio, orquestração: `services.py`.
- Lib/serviço externo: `providers/<nome>.py`. Trocar provedor = mexer só no provider.
- Cache: `cache.py` do app.
- Tarefa em segundo plano: `apps/<app>/tasks.py`. Task fina: chama service. Service enfileira via função do `tasks.py` dentro de `transaction.on_commit` (só depois de gravar). Celery não aparece fora de `config/celery.py` e `tasks.py`.
- Auth (cadastro, login, e-mail, social): config `ACCOUNT_*` / `SOCIALACCOUNT_*` / `HEADLESS_*` em `config/settings.py`. Código só em `apps/accounts/` (adapter, form, template). allauth não aparece fora daí.
- Tabela: `models.py` + migration + registro em `admin.py`.
- Setting: env → `config/settings.py` → `.env.example` + tabela Config abaixo.
- Transversal (health, settings, urls raiz): `config/`.
- Módulo novo (ex.: `transcription`): app novo `apps/<nome>/` em `INSTALLED_APPS`, mesma estrutura dos atuais.

## Fluxo

`analyze_image` (view) → `ImageAnalyzeSerializer` (valida) → `ImageAnalysisService.analyze` → `PaddleOCRProvider.extract_text` → `LexicalLookupService.analyze_text` → resposta.

Captura de foto ou áudio, texto extraído no celular (padrão do app): app cria com o texto (`POST captures` com `text`) → `ready`. Arquivo não sobe.

Captura de foto ou áudio, texto extraído no servidor (app em `EXTRACTION=server`, pra comparar): app cria sem texto (`POST captures`, `waiting_file`) → manda o arquivo (`PUT captures/{id}/file`, 202) → `save_upload` grava em `CAPTURE_UPLOAD_DIR` → `processing` → `enqueue_processing` (após commit) → worker `process_capture` → `CaptureProcessingService.process` → `TextExtractionService.extract` (foto) ou `TranscriptionService.transcribe` (áudio) → `ready` com o texto, arquivo apagado. Texto digitado já nasce `ready`. Depois: app salva texto editado e termos (`PATCH`) → confirma (`POST confirm`, `analyzed`).

Lookup, em lote:

1. Redis `MGET`. HIT → `source: cache`.
2. MISS → Postgres (`normalized_word__in`). HIT → `source: database`, regrava no Redis.
3. MISS → dicionário, 1 chamada por palavra, sequencial. Upsert no Postgres + Redis, `source: dictionary`.

## OCR (`ocr`)

- Validação em ordem: tamanho ≤ `OCR_MAX_IMAGE_SIZE_BYTES` → `content_type` JPEG/PNG/WEBP → Pillow abre + `verify()` → formato real JPEG/PNG/WEBP. Extensão do nome não garante nada. Erro = 400, mensagem pt-BR.
- Engine PaddleOCR: um por processo, criado na 1ª requisição (lazy, com lock), reutilizado. 1ª chamada lenta (carrega modelos). Ideal: carregar no startup.
- Paddle lê de caminho: grava arquivo temporário, apaga no fim. Desligado: orientação de documento, unwarping, orientação de linha.
- Texto = `rec_texts` unidos por espaço.

## Transcrição (`transcription`)

- Validação em ordem: tamanho ≤ `TRANSCRIPTION_MAX_AUDIO_SIZE_BYTES` → `content_type` `audio/mp4`, `audio/m4a` ou `audio/x-m4a` → PyAV abre → container MP4/M4A com uma faixa só, AAC (sem vídeo) → duração ≤ `TRANSCRIPTION_MAX_AUDIO_SECONDS` + 1 s de folga (app para em 60 s; o encoder passa uns milissegundos). Erro = 400, mensagem pt-BR.
- Modelo: um por processo e por configuração (modelo, precisão, threads), criado na 1ª tarefa (lazy, com lock), reutilizado. 1ª vez baixa do Hugging Face pra `TRANSCRIPTION_MODEL_DIR` (volume `whisper_models`: recriar o container não baixa de novo).
- Transcrição: idioma fixo `en`, `beam_size` = `TRANSCRIPTION_BEAM_SIZE`, `vad_filter` ligado (corta silêncio, evita texto inventado em áudio mudo). Texto = segmentos unidos por espaço.
- PyAV `<19`: faster-whisper 1.2.1 passa `metadata_errors` pro `av.open`, removido no PyAV 19. Subir o teto quando sair faster-whisper que não passe.

Medição (`benchmark_transcription`, 2026-10-23): Docker Desktop no PC de dev (6 vCPU), `int8`, beam 5, threads padrão do CTranslate2 (4), 1 tarefa por vez. Áudio: LibriSpeech dev-clean (CC BY 4.0, leitura limpa, fora do repo), convertido pra M4A AAC 44,1 kHz 128 kbps (padrão do `record` no app). Erro = WER contra o texto oficial, 248 palavras.

| Modelo | 60 s de áudio: tempo / CPU | 30 s | 5 s | Memória pico | Erro (WER) |
| --- | --- | --- | --- | --- | --- |
| `tiny.en` | 5,5 s / 10,6 s | 3,1 s | 0,9 s | 348 MB | 6,9% |
| `base.en` | 7,8 s / 16,3 s | 5,1 s | 1,3 s | 447 MB | 5,6% |
| `small.en` | 19,9 s / 45,4 s | 12,5 s | 3,8 s | 781 MB | 2,8% |

- Threads: 2 ganha de 4 nesta máquina, repetido 3×. 60 s em `base.en`: 5,2 s / 9,4 s de CPU (2 threads) × 7,6 s / 15,7 s (4). `small.en` com 2: 15,1 s / 27,9 s. Padrão = 2.
- Escolha: `base.en` com 2 threads. 60 s viram texto em ~5 s. Erro de `base` é quase todo nome próprio e homófono ("needing" × "kneading"); a pessoa corrige no texto antes de escolher os termos. `small.en` erra metade, mas custa ~3× CPU e +330 MB por processo. `tiny.en` economiza pouco e erra mais.
- Leitura limpa favorece todos. Microfone de celular com ruído deve aumentar o erro e a distância entre os modelos: medir de novo com áudio real do app antes de produção, e no servidor de produção (CPU diferente).
- Ponta a ponta (`PUT file` → fila → worker → `ready`), 60 s, `base.en`, 2 threads: 1ª tarefa depois de subir o worker ~22 s (carrega modelo), 2ª ~13 s, depois ~5,5 s. Ideal: carregar no startup do worker.
- Memória pico é só do Whisper. Worker carrega Paddle também: somar os dois pra dimensionar.

## Lexical (`lexical`)

- Normalização: regex `\b[\w'-]+\b` → NFKC → `casefold` → tira `-` e `'` das bordas → dedup → ordem alfabética. Ex.: "The quick brown fox" → brown, fox, quick, the. Número também vira palavra (`\w` pega dígito).
- Dicionário: `GET {DICTIONARY_API_BASE_URL}/{lang}/{palavra}` (dictionaryapi.dev), timeout `DICTIONARY_API_TIMEOUT_SECONDS`. Usa só `meanings[].definitions[].definition`.
- Sem definição (404, erro de rede, timeout, resposta vazia): `definitions: []`, salvo igual no Postgres e Redis. Erro transitório fica gravado.
- Idioma: `LEXICAL_LANGUAGE`. `analyze_text(text, language)` já aceita idioma; view ainda não passa.

## Captura (`captures`)

- Rascunho do que a pessoa capturou. Offline first: nasce no celular, o app sincroniza quando tiver internet. `id` = UUID gerado no app: mesmo `id` de novo = 200 com o que já existe (envio repetido não duplica). `id` de outro usuário = 409.
- Status: `waiting_file` (foto/áudio sem arquivo) → `processing` → `ready` | `failed` → `analyzed` (confirmou a análise). Texto digitado ou extraído no celular (`text` no `POST`) nasce `ready`.
- Arquivo: só temporário. Foto e áudio ficam no celular; a API guarda só o texto. Apagado depois de extrair, depois da última tentativa e ao descartar. Reenviar (`PUT file`) vale em `waiting_file`, `processing` e `failed` (é o "Processar agora" do app). Já processada: 409.
- Processamento: task `process_capture`. Erro na extração: nova tentativa com espera `CAPTURE_PROCESS_RETRY_SECONDS × 2^tentativa`, até `CAPTURE_PROCESS_MAX_RETRIES`. Última falhou: `failed` + `error`. Códigos: `no_text` (extraiu nada), `file_missing` (arquivo sumiu da pasta), `processing_failed` (extração quebrou em todas as tentativas).
- Texto e termos: `text` = atual (editável), `original_text` = o que veio do OCR/transcrição/digitação. Termo = trecho do texto (`text`, `start`, `end` em caracteres). Palavra e expressão que a contém coexistem ("mind" e "mind the gap"). `PATCH` com `terms` troca a lista toda; só `text` mantém os termos que ainda batem no mesmo lugar. Edita só em `ready`.
- Confirmar: exige 1+ termo e `ready` → `analyzed` (`analyzed_at`). De novo em `analyzed`: 200. A IA que monta a ficha de cada termo entra depois.
- Descartar: só marca `discarded_at`. Registro fica no banco; some da lista e do detalhe. Sincronização (`updated_since`) traz o descarte, pro outro aparelho apagar.
- Redis caiu com captura na fila: fica `processing`. App reenvia o arquivo e resolve.

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

`Capture` (tabela `captures_capture`): `id` (UUID do app), `user`, `source` (`text`, `audio`, `photo`), `status`, `original_text`, `text`, `error`, `captured_at` (hora no celular), `processed_at`, `analyzed_at`, `discarded_at`, `created_at`, `updated_at`. Índice (`user`, `updated_at`).

`CaptureTerm` (tabela `captures_captureterm`): `capture`, `text` (char 255), `start`, `end`. Único (`capture`, `start`, `end`). Ordem: `start`, depois o maior primeiro.

Redis:

- Chave `lexical:{lang}:{palavra}` (ex.: `lexical:en:architecture`). Valor JSON `{word, definitions, source}`. TTL `LEXICAL_CACHE_TTL_SECONDS`.
- Redis fora: leitura vira MISS, escrita ignorada. API segue funcionando.
- Fila do Celery: `CELERY_BROKER_URL` (padrão = `REDIS_URL`; `.env.example` usa o banco 1 do Redis, separado do cache).

## Endpoints

Sem barra final. Sem throttle. Resposta só JSON. `/api/v1` exige login (Bearer, seção Auth). Rotas de auth: seção Auth.

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
- 401: sem token válido.

Captura (`/api/v1/captures`). Erro de validação: 400 `{"campo": ["<mensagem pt-BR>"]}`. Conflito de estado: 409 `{"detail": "..."}`. De outro usuário ou descartada: 404.

| Rota | Corpo | Resposta |
| --- | --- | --- |
| `POST /api/v1/captures` | JSON `{id, source, captured_at, text?}`. `text` até `CAPTURE_MAX_TEXT_LENGTH`: obrigatório em `source: text`; em foto/áudio = texto extraído no celular (nasce `ready`), sem ele espera o arquivo (`waiting_file`) | 201 nova, 200 já existia, 409 `id` de outro usuário |
| `GET /api/v1/captures` | query `updated_since?` (ISO 8601), `cursor?` | 200 `{next, previous, results}`. Mais recente (`updated_at`) primeiro, `CAPTURE_PAGE_SIZE` por página. Sem `updated_since`: sem as descartadas. Com: tudo que mudou desde então, descartadas incluídas |
| `GET /api/v1/captures/{id}` | | 200 |
| `PATCH /api/v1/captures/{id}` | JSON `{text?, terms?: [{text, start, end}]}`, ao menos um. Até `CAPTURE_MAX_TERMS` termos de até `CAPTURE_MAX_TERM_LENGTH` | 200. 400 termo que não bate com o texto ou repetido. 409 fora de `ready` |
| `PUT /api/v1/captures/{id}/file` | multipart, campo `file`. Foto: mesmas regras do OCR. Áudio: regras da Transcrição | 202 `processing`. 400 captura de texto ou arquivo inválido. 409 já processada |
| `POST /api/v1/captures/{id}/confirm` | | 200 `analyzed`. 400 sem termo. 409 fora de `ready` |
| `DELETE /api/v1/captures/{id}` | | 204, mesmo se já descartada |

Captura na resposta:

```json
{
  "id": "0b8f…", "source": "photo", "status": "ready",
  "text": "MIND THE GAP", "original_text": "MIND THE GAP",
  "terms": [{ "text": "MIND THE GAP", "start": 0, "end": 12 }],
  "error": "", "captured_at": "…", "processed_at": "…", "analyzed_at": null,
  "discarded_at": null, "created_at": "…", "updated_at": "…"
}
```

`/admin/`: Django admin. `LexicalEntry` com busca por palavra, filtro por idioma e fonte. `Capture` com busca por texto e e-mail, filtro por tipo e status, termos na própria tela.

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
| `CELERY_BROKER_URL` | = `REDIS_URL` | `.env.example`: `redis://redis:6379/1` |
| `CELERY_WORKER_CONCURRENCY` | 1 | tarefas em paralelo no worker (cada uma com seus modelos na memória) |
| `CAPTURE_UPLOAD_DIR` | `/tmp/tagarela/captures` | pasta do arquivo temporário. Precisa ser a mesma no `api` e no `worker`: compose fixa `/var/lib/tagarela/captures` no volume `capture_uploads` |
| `CAPTURE_MAX_TEXT_LENGTH` | 2000 | texto digitado ou editado |
| `CAPTURE_MAX_TERMS` | 50 | termos por captura |
| `CAPTURE_MAX_TERM_LENGTH` | 100 | caracteres por termo |
| `CAPTURE_PAGE_SIZE` | 50 | |
| `CAPTURE_PROCESS_MAX_RETRIES` | 3 | novas tentativas antes de `failed` |
| `CAPTURE_PROCESS_RETRY_SECONDS` | 30 | espera base, dobra a cada tentativa |
| `OCR_MAX_IMAGE_SIZE_BYTES` | 10 MB | |
| `TRANSCRIPTION_MODEL` | `base.en` | modelo do Whisper (`tiny.en`, `base.en`, `small.en`...). Escolha em Transcrição |
| `TRANSCRIPTION_MODEL_DIR` | `/tmp/tagarela/whisper` | onde o modelo é baixado. Compose fixa `/var/lib/tagarela/whisper` no volume `whisper_models` (worker) |
| `TRANSCRIPTION_COMPUTE_TYPE` | `int8` | precisão na CPU |
| `TRANSCRIPTION_CPU_THREADS` | 2 | 0 = padrão do CTranslate2 (4). Medição em Transcrição |
| `TRANSCRIPTION_BEAM_SIZE` | 5 | 1 = mais rápido, pode errar mais |
| `TRANSCRIPTION_MAX_AUDIO_SIZE_BYTES` | 5 MB | 60 s em AAC 128 kbps ≈ 1 MB |
| `TRANSCRIPTION_MAX_AUDIO_SECONDS` | 60 | + 1 s de folga |
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

Fixo em settings (sem env): Celery com `acks_late`, `reject_on_worker_lost`, prefetch 1 (tarefa longa: uma por vez, volta pra fila se o worker morrer) e sem guardar resultado; content types e formatos aceitos, `LANGUAGE_CODE` pt-br, `TIME_ZONE` America/Sao_Paulo.

## Rodar e inspecionar

Subir: `README.md`. Comandos via `docker compose exec`:

- Testes: `api python manage.py test`. Cobertura: `api sh -c "pip install -r requirements-dev.txt && coverage run manage.py test && coverage report"`.
- Migration: `api python manage.py makemigrations`. `migrate` roda sozinho na subida do `api`.
- Admin: `api python manage.py createsuperuser` (pede e-mail) → http://localhost:8000/admin/.
- Código de verificação/reset no dev: Mailpit em http://localhost:8025 (e-mail renderizado, texto, cabeçalhos e checagem de compatibilidade do HTML).
- Postgres: `db psql -U <POSTGRES_USER> -d <POSTGRES_DB>` → `SELECT id, word, normalized_word, language, source, data, created_at FROM lexical_lexicalentry ORDER BY id DESC;`
- Redis: `redis redis-cli KEYS 'lexical:*'`, `redis redis-cli GET 'lexical:en:<palavra>'`. Fila: `redis redis-cli -n 1 LLEN celery`.
- Medir transcrição: `worker python manage.py benchmark_transcription <arquivos .m4a> --model base.en` (opcionais `--threads`, `--beam-size`, `--compute-type`). Um modelo por execução: memória pico é do processo.
- Worker: `docker compose logs -f worker`. Mudou código de task ou service: `docker compose restart worker` (worker não tem hot reload).
- Capturas: `db psql ...` → `SELECT id, source, status, error, text, updated_at FROM captures_capture ORDER BY updated_at DESC;`
- Postman: POST, Body → form-data, key `file` tipo File. Content-Type automático.

Formato e análise: fora do container (ruff não está na imagem). Venv local: `python -m venv .venv` → `pip install -r requirements-dev.txt` → `ruff format .`, `ruff check --fix .`.

Compose: `api` só sobe com `db` healthy. Healthcheck `pg_isready -h 127.0.0.1`: `-h` força TCP, porque no initdb o servidor temporário só aceita socket local e daria falso pronto.

Servidor = `runserver` (dev, hot reload pelo volume `.:/app`). Subida do `api`: `migrate` e depois `runserver`. Migration falhou: container para, erro em `docker compose logs api`. Sem setup de produção (lá, `migrate` vai num passo de deploy, fora do servidor).

## Convenções

- Código (nomes, classes) em inglês. Texto pro usuário (erro) e docs em pt-BR.
- Import absoluto: `apps.<app>.<módulo>`, `config.<módulo>`.
- Formato e análise: ruff (`pyproject.toml`). Regras padrão do ruff, linha 100, migrations fora (geradas pelo Django). RUF012 desligada: Django declara `Meta` (constraints, indexes) com lista.
- Aspas duplas. Type hints nas assinaturas.
- View: função com `@api_view` (um método) ou `APIView` (vários métodos na mesma rota).
- Nomes: `<X>Provider` (externo), `<X>Service` (regra), `<X>Serializer`, `<X>Cache`, task = verbo (`process_capture`).
- Dependência injetável: construtor recebe opcional, padrão real (`self.cache = cache or LexicalCache()`).
- Falha de dependência opcional (Redis, dicionário): provider/cache trata e segue. Não derruba a requisição.

## Testes

- Runner do Django (`manage.py test`). Sem pytest por enquanto. Base: `django.test.TestCase` (banco), `SimpleTestCase` (sem banco), `rest_framework.test.APISimpleTestCase` (endpoint sem banco), `APITestCase` (endpoint com banco).
- Roda no container `api` (precisa do Postgres).
- Arquivo: pacote `apps/<app>/tests/` (`__init__.py` + `test_<módulo>.py`). Transversal (`config/`): `config/tests.py`. Helper compartilhado no pacote do app (ex.: `apps/ocr/tests/images.py`).
- Auth: fluxo inteiro pelo client do Django em `/api/auth/app/v1`. Código lido de `mail.outbox`. `cache.clear()` no `setUp` (rate limit do allauth fica no cache). Google/Apple: `patch` da validação do id_token (`allauth.socialaccount.providers.google.views._verify_and_decode`, `AppleOAuth2Adapter.get_verified_identity_data`).
- Nunca Paddle, Whisper, rede ou Redis reais: fake via construtor. View: `unittest.mock.patch("apps.ocr.views.ImageAnalysisService")`. Dicionário: `httpx.get` mockado + payload fixo. Paddle: `patch.object(PaddleOCRProvider, "_engine", fake)`. Whisper: `patch.object(WhisperProvider, "_models", {chave: fake})`; carga via `patch("faster_whisper.WhisperModel")`. Redis: client `MagicMock`. Health: `patch` de `config.health.connections` e `config.health.Redis`.
- Unit: normalização, validator, parse do provider, lookup (ordem cache → banco → dicionário, `source`).
- Captura: `UploadDirMixin` (pasta de upload temporária por teste), `make_user`, `make_capture` em `apps/captures/tests/helpers.py`. Fila: `patch("apps.captures.services.enqueue_processing")` + `captureOnCommitCallbacks(execute=True)`. Extração: `CaptureProcessingService({source: fake})`. Task: `process_capture.apply(args=..., retries=N)` com o service mockado; nova tentativa via `patch.object(process_capture, "retry")`. Nunca broker real.
- API: status + corpo (200, 400, 401). Endpoint com login: `self.client.force_authenticate(get_user_model()(email=...))` no `setUp`; Bearer de verdade só no teste de auth.
- Código novo ou alterado: teste junto. Bug corrigido: teste que reproduz o bug.
- Cobertos: normalização, lookup (ordem, `source`, idioma, gravação), cache, provider do dicionário, provider do Paddle (sem engine real), validator, service de imagem, `POST /api/v1/images/analyze`, `GET /health`, auth (cadastro + código, login, e-mail não verificado, reset, refresh, logout, Google, Apple, token inválido, anti-enumeração, Bearer nas rotas `/api/v1` (401 sem token ou token inválido, 200/400 com o access do login), e-mails em texto e HTML com o código e a validade), `User` (manager, display, admin), `StrictSerializer`, captura (criar, id repetido e de outro usuário, campos e valores inválidos, lista com cursor e `updated_since`, detalhe, termos com palavra dentro de expressão, editar texto mantendo termos, termo que não bate, confirmar, descartar, arquivo de foto e de áudio na fila, arquivo trocado (foto em áudio e vice-versa), reenvio, 409, processamento com texto, sem texto, erro com e sem nova tentativa, arquivo sumido, task e fila), `TextExtractionService`, validator de áudio (tipo, formato, codec, tamanho, duração com folga), provider do Whisper (sem modelo real), `TranscriptionService`, comando de benchmark. Fora: criação do engine Paddle e do modelo Whisper (carregam modelo real).

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
  - Docker: `docker compose up --build --wait` com `.env.example` e volume vazio (passa pelo initdb; sobe `worker` junto) + `GET /health` 200. Falhou: logs do compose na rodada.
- Python da esteira = `PYTHON_VERSION` no workflow = imagem do `Dockerfile`. Subiu um: subir o outro junto.
- Sem lockfile: `requirements.txt` em faixa, esteira instala a última versão dentro dela. Release nova de dependência pode quebrar a esteira sem mudança no código.
- Antes do push, rodar local: `ruff format .`, `ruff check .`, `manage.py test`, `makemigrations --check --dry-run`. Mexeu em Docker/compose: `docker compose up` + `/health` 200.
