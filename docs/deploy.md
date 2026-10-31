# Deploy (prd)

A esteira já prova que a imagem de prd compila, passa no `check --deploy`, roda as migrations e responde no `/health`. Falta só o que depende da hospedagem e das contas.

## 1. Configuração

Copie `.env.prd.example` para `.env.prd` (fora do git) ou cadastre as mesmas chaves como secrets da hospedagem. A API não sobe em prd enquanto estas chaves estiverem vazias ou com valor de exemplo:

- `DJANGO_SECRET_KEY`: gerar uma nova, ela assina os tokens de login.
- `DJANGO_ALLOWED_HOSTS`: o domínio da API.
- `POSTGRES_PASSWORD`, junto com `POSTGRES_HOST` e os outros `POSTGRES_*`.
- `GEMINI_API_KEY`: chave própria de prd, com limite de gasto.
- `EMAIL_HOST`, `EMAIL_HOST_USER`, `EMAIL_HOST_PASSWORD` e `DEFAULT_FROM_EMAIL`: SMTP de verdade.

Gerar a chave:

```sh
python -c "import secrets; print(secrets.token_urlsafe(50))"
```

## 2. Imagem

O alvo padrão do `Dockerfile` é o de prd: gunicorn, sem root, com os estáticos do admin servidos pelo whitenoise.

```sh
docker build --tag tagarela-api .
```

Para conferir na sua máquina:

```sh
docker run --env-file .env.prd --publish 8000:8000 tagarela-api
```

A hospedagem pode ajustar `PORT`, `WEB_CONCURRENCY` e `GUNICORN_CMD_ARGS` por variável de ambiente.

## 3. Banco

Antes de cada versão nova subir, rode como passo separado:

```sh
python manage.py migrate
```

Em prd a API não migra ao subir. Do primeiro deploy em diante, valem as regras de migration e de contrato do `CLAUDE.md`.

## 4. HTTPS

A API espera um proxy na frente, que termina o HTTPS e define `X-Forwarded-Proto`. O proxy precisa sobrescrever esse cabeçalho quando vier do cliente; as hospedagens gerenciadas costumam fazer isso sozinhas, mas confira na que escolher.

`/health` responde em HTTP puro, sem redirect, para o health check da hospedagem. O `Host` que ela manda precisa estar em `DJANGO_ALLOWED_HOSTS`.

O HSTS começa em 1 ano. Se quiser testar o domínio antes, comece com `SECURE_HSTS_SECONDS=3600`: o navegador guarda esse valor e não dá para desfazer antes do prazo.

## 5. Login social

- `GOOGLE_CLIENT_ID`: client Web do Google, o mesmo projeto do client Android.
- Client Android do Google: pacote `com.tagarela.app` com o SHA-1 da chave de release.
- `APPLE_CLIENT_ID`: `com.tagarela.app`.

## 6. App

Troque o `API_URL` em `../mob/env/prd.json` pelo domínio real. O roteiro do build está no README do app.
