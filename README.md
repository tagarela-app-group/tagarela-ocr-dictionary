# Tagarela API

Backend em Django REST Framework para receber imagens, extrair texto com OCR e enriquecer as palavras encontradas com informações lexicais.

O projeto usa um monolito modular. O modulo `ocr` cuida de upload, validação da imagem e extração de texto com PaddleOCR. O módulo `lexical` normaliza palavras e consulta informações na ordem:

```text
Redis -> PostgreSQL -> API externa de dicionário
```

Áudio ainda esta fora do escopo.

## Stack

- Python
- Django
- Django REST Framework
- PostgreSQL
- Redis
- PaddleOCR / PaddlePaddle
- Pillow
- httpx
- Docker / Docker Compose

## Configuracao

Crie o arquivo `.env` a partir do exemplo:

```bash
cp .env.example .env
```

As principais váriaveis são:

```env
POSTGRES_DB=example
POSTGRES_USER=example
POSTGRES_PASSWORD=example
POSTGRES_HOST=db
POSTGRES_PORT=5432

REDIS_URL=redis://redis:6379/0

LEXICAL_LANGUAGE=en
```

`LEXICAL_LANGUAGE` define o idioma usado para buscar as palavras na API externa e tambem compõe as chaves do Redis.
Provavelmente vai ser alterado para ser recebido via rota, mas está sendo analisado.

## Como Rodar

Suba a aplicação com Docker Compose:

```bash
docker compose up --build
```

Em outro terminal, rode as migrations:

```bash
docker compose exec api python manage.py migrate
```

A API ficara disponivel em:

```text
http://localhost:8000
```

## Health Check

Para testar se API, PostgreSQL e Redis estao respondendo:

```bash
curl http://localhost:8000/health
```

Resposta esperada:

```json
{
  "status": "ok",
  "checks": {
    "database": true,
    "redis": true
  }
}
```

## Enviar Imagem

Endpoint:

```http
POST /api/v1/images/analyze
```

O campo do arquivo deve se chamar `file`.

Formatos aceitos inicialmente:

- JPEG
- PNG
- WEBP

Tamanho maximo:

```text
10 MB
```

### Testando Pelo Postman

1. Crie uma request `POST`.
2. Use a URL:

```text
http://localhost:8000/api/v1/images/analyze
```

3. Va em `Body`.
4. Selecione `form-data`.
5. Adicione um campo:
   - `Key`: `file`
   - tipo da key: `File`
   - `Value`: selecione a imagem
6. Envie a request.

Não é necessario configurar manualmente o `Content-Type`; o Postman faz isso ao usar `form-data`.

### Testando Pelo Terminal

```bash
curl -X POST \
  -F "file=@/caminho/para/imagem.png" \
  http://localhost:8000/api/v1/images/analyze
```

Exemplo de resposta:

```json
{
  "ocr": {
    "text": "LEMBRE-SE BLEACH É SIMPLESMENTE ABSURDO"
  },
  "words": [
    {
      "word": "antes",
      "definitions": [],
      "source": "dictionary"
    }
  ]
}
```

Na primeira chamada, o OCR pode demorar mais porque o PaddleOCR carrega os modelos.

## Django Admin

Crie um superusuario:

```bash
docker compose exec api python manage.py createsuperuser
```

Acesse:

```text
http://localhost:8000/admin/
```

Os registros persistidos no PostgreSQL aparecem no model `LexicalEntry`.

## Inspecionar PostgreSQL

Entre no `psql`:

```bash
docker compose exec db psql -U example -d example
```

Liste as entradas lexicais:

```sql
SELECT id, word, normalized_word, language, source, data, created_at
FROM lexical_lexicalentry
ORDER BY id DESC;
```

## Inspecionar Redis

Liste as chaves:

```bash
docker compose exec redis redis-cli KEYS 'lexical:*'
```

Veja uma chave especifica:

```bash
docker compose exec redis redis-cli GET 'lexical:en:example'
```

## Documentacao

- `docs/ARQUITETURA_INICIAL.md`: arquitetura inicial, fluxo principal e responsabilidades dos modulos.
