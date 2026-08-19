# Arquitetura Inicial da Aplicação

## 1. Objetivo

Criar uma API backend para uma aplicação mobile capaz de:

1. receber uma imagem;
2. extrair o texto da imagem usando OCR;
3. identificar as palavras encontradas;
4. consultar significado e outras informações dessas palavras;
5. reutilizar resultados já conhecidos para reduzir tempo de resposta e chamadas externas.

Nesta primeira versão, o foco será apenas em imagens.

Áudio será adicionado em uma etapa futura.

---

## 2. Fluxo principal

```text
Aplicativo Mobile
       |
       v
Django REST Framework
       |
       v
Validação da imagem
       |
       v
PaddleOCR
       |
       v
Texto extraído
       |
       v
Normalização das palavras
       |
       v
Redis
       |
      MISS
       v
PostgreSQL
       |
      MISS
       v
API externa de dicionário
       |
       +------> PostgreSQL
       |
       +------> Redis
       |
       v
Resposta para o aplicativo
```

A ideia principal é evitar chamadas desnecessárias para a API externa.

Sempre que possível, a informação será recuperada localmente.

---

## 3. Arquitetura escolhida

Será utilizado um **Monólito Modular com Django**.

Isso significa que teremos apenas uma aplicação backend, mas com responsabilidades separadas em módulos.

```text
Django
 |
 +-- OCR
 |
 +-- Análise Lexical
 |
 +-- PostgreSQL
 |
 +-- Redis
 |
 +-- API externa
```

Não serão utilizados microserviços nesta etapa.

### Motivo

O projeto ainda está no início.

Microserviços adicionariam complexidade desnecessária para:

- deploy;
- comunicação entre serviços;
- logs;
- observabilidade;
- rede;
- manutenção;
- testes.

Se futuramente OCR ou áudio precisarem escalar separadamente, os módulos poderão ser extraídos.

---

## 4. Stack

### Backend

```text
Python
Django
Django REST Framework
```

### Banco

```text
PostgreSQL
psycopg
```

### Cache

```text
Redis
```

### OCR

```text
PaddleOCR
PaddlePaddle
Pillow
```

### API externa

```text
httpx
```

### Infraestrutura local

```text
Docker
Docker Compose
```

---

## 5. Dependências iniciais

```text
django
djangorestframework
psycopg[binary]

redis
httpx

paddleocr
paddlepaddle
pillow
```

Nesta primeira etapa não será utilizado pytest.

Os testes poderão utilizar inicialmente:

```text
django.test.TestCase
```

ou:

```text
rest_framework.test.APITestCase
```

---

## 6. Estrutura do projeto

Estrutura inicial:

```text
ocr-api/
|
├── AGENTS.md
├── README.md
├── manage.py
├── requirements.txt ou pyproject.toml
├── Dockerfile
├── docker-compose.yml
├── .env.example
├── .gitignore
|
├── docs/
│   └── ARQUITETURA_INICIAL.md
|
├── config/
│   ├── __init__.py
│   ├── settings.py
│   ├── urls.py
│   ├── asgi.py
│   └── wsgi.py
|
├── apps/
│   |
│   ├── ocr/
│   │   ├── migrations/
│   │   ├── providers/
│   │   │   └── paddle.py
│   │   ├── services.py
│   │   ├── serializers.py
│   │   ├── views.py
│   │   ├── urls.py
│   │   └── apps.py
│   |
│   └── lexical/
│       ├── migrations/
│       ├── providers/
│       │   └── dictionary.py
│       ├── models.py
│       ├── services.py
│       ├── cache.py
│       ├── serializers.py
│       ├── views.py
│       └── apps.py
```

A estrutura deve permanecer simples.

Não criar camadas adicionais sem necessidade.

---

## 7. Responsabilidade de cada módulo

### `ocr`

Responsável por:

```text
imagem
  |
  v
validação
  |
  v
OCR
  |
  v
texto
```

Arquivos principais:

```text
providers/paddle.py
services.py
serializers.py
views.py
```

O código que conhece PaddleOCR deve ficar dentro do provider.

Exemplo conceitual:

```python
class PaddleOCRProvider:
    def extract_text(self, image: bytes) -> str:
        ...
```

O restante da aplicação não deve depender diretamente da API do PaddleOCR.

---

### `lexical`

Responsável por:

```text
texto
 |
 v
normalização
 |
 v
palavras
 |
 v
Redis
 |
 v
PostgreSQL
 |
 v
API de dicionário
```

Ele deverá:

- normalizar palavras;
- remover palavras duplicadas;
- consultar Redis;
- consultar PostgreSQL;
- consultar a API externa;
- salvar resultados novos;
- devolver informações estruturadas.

---

## 8. Endpoint inicial

```http
POST /api/v1/images/analyze
```

Entrada:

```text
multipart/form-data
```

Campo:

```text
file
```

Exemplo:

```bash
curl -X POST   -F "file=@imagem.png"   http://localhost:8000/api/v1/images/analyze
```

---

## 9. Regras para imagens

Aceitar inicialmente:

```text
JPEG
PNG
WEBP
```

Limite:

```text
10 MB
```

A validação deve verificar:

1. tamanho;
2. Content-Type;
3. se o arquivo realmente pode ser aberto como imagem.

Apenas:

```text
imagem.jpg
```

Não garante que o arquivo seja realmente uma imagem.

---

## 10. OCR

Biblioteca inicial:

```text
PaddleOCR
```

O engine deve ser criado apenas uma vez e reutilizado.


Preferir algo equivalente a:

```text
Inicialização da aplicação
        |
        v
PaddleOCR carregado
        |
        v
Reutilizado pelas requisições
```

Isso evita carregar o modelo repetidamente.

---

## 11. Fluxo lexical

Exemplo:

OCR retorna:

```text
The quick brown fox
```

Após normalização:

```text
the
quick
brown
fox
```

Remover duplicações antes das consultas.

Depois:

```text
Redis
  |
  +-- HIT -> usar resultado
  |
  +-- MISS
        |
        v
   PostgreSQL
        |
        +-- HIT -> usar e colocar no Redis
        |
        +-- MISS
              |
              v
       API de dicionário
              |
              +--> salvar PostgreSQL
              |
              +--> salvar Redis
```

---

## 12. Redis

Redis será utilizado apenas como cache.

Exemplo de chave:

```text
lexical:en:architecture
```

Exemplo de valor:

```json
{
  "word": "architecture",
  "definitions": [
    "..."
  ]
}
```

O Redis pode perder todos os dados sem comprometer a aplicação.

O PostgreSQL continua sendo a persistência principal.

---

## 13. PostgreSQL

Tabela inicial sugerida:

```text
lexical_entry
```

Campos:

```text
id
word
normalized_word
language
data
source
created_at
updated_at
```

O campo `data` pode utilizar `JSONField` do Django.

Exemplo:

```python
class LexicalEntry(models.Model):
    word = models.CharField(max_length=255)
    normalized_word = models.CharField(max_length=255)
    language = models.CharField(max_length=10)
    data = models.JSONField()
    source = models.CharField(max_length=100)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        constraints = [
            models.UniqueConstraint(
                fields=["normalized_word", "language"],
                name="unique_lexical_entry"
            )
        ]
```

O JSON permite guardar diferentes estruturas retornadas por provedores sem a necesidade de criar várias tabelas no início.
