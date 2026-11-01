# CLAUDE.md — Tagarela API

Backend Django REST do Tagarela (app Flutter em `../mob`). Guarda conta, capturas (só texto) e vocabulário. Foto e áudio viram texto no celular.

Detalhe de cada feature e ambientes: `docs/produto.md`. Exercícios: `docs/exercises.md`. Deploy: `docs/deploy.md`. Antes de mexer numa feature, ler a parte dela.

## Produto

- Conta: um e-mail = uma pessoa, entra por senha, Google ou Apple.
- Curso: "aprende X por meio de Y" (en, es, pt; X ≠ Y). Conta tem vários, um ativo. Capturas, termos e grupos vivem no curso; rotas de estudo usam o ativo.
- Captura: texto que a pessoa revisa, marca termos e confirma; termos confirmados vão pro vocabulário.
- Vocabulário: termo único por curso, em grupos que só a pessoa cria. IA nunca organiza.
- Ficha e exercícios: a IA gera na 1ª vez, fica salvo, não regenera.

## Regras

1. Antes de alterar algo (código, doc, config): propor (o quê, onde, opções, recomendação) e esperar ok. Pedido fere regra/boa prática: avisar e propor alternativa. Sem camada nova sem necessidade.
2. Contrato `/api/v1`: até o primeiro deploy, o app é o único consumidor e pode mudar sem versão nova. Campo sai da resposta: o app muda antes. Campo novo na requisição ou rota nova: a API muda antes. Depois do primeiro deploy: não quebrar; incompatível vira nova versão.
3. Configurável (limite, URL, TTL) vira setting via env, refletido em `.env.dsv.example` e `.env.prd.example`. Segredo só no `.env.dsv`, no `.env.prd` ou no secret da hospedagem.
4. Model mudou: migration junto. Depois do primeiro deploy, nunca editar migration mergeada. Preencher dado e mudar a tabela: migrations separadas. Migration de dados testa com `MigrationTestCase`.
5. Código novo/alterado: com teste, sem rede real. Bug: teste que reproduz. Teste cobra regra, contrato, validação e borda. Não testa cópia do código (prompt, constante, setting), Django, DRF, lib, nem o que outro teste já cobre (login obrigatório: `test_api_auth.py`). Antes de escrever, dizer que bug ele pegaria; nenhum, não escreve.
6. Sem comentário em código/config.
7. Mudou regra: atualizar aqui. Mudou feature: `docs/produto.md`. Só o que o código não mostra.
8. Git é do usuário: no máximo um commit local, em branch da `develop` (`feat/ fix/ docs/ ci/ chore/`), nunca direto em `develop`/`main`. Conventional Commits pt-BR, enxuto, sem assinatura de IA. Push, PR, merge e erro da esteira: ele cuida.
9. Validar é do usuário: não rodar teste, lint, análise nem build. A entrega é o código e os testes escritos; ao terminar, dizer o que mudou, sem afirmar que funciona.
10. Dependência nova: checar manutenção e contar ao usuário; nativa ou pesada: perguntar.
11. Fim de task ou troca de assunto: sugerir `/compact manter: ...` ou `/clear`.
12. Tipagem estrita: sem `Any`; parâmetros e retornos anotados. Dado de fora (JSON, IA) entra como `object`/`Mapping[str, object]` e vira tipo de verdade antes de circular.
13. Sem repetição: antes de escrever, procurar em `apps/` e nos testes. Igual em 2 lugares vira uma peça só (service, `common/`, helper de teste). Igual por acaso, com regra diferente, fica separado. A esteira falha com qualquer trecho repetido (`jscpd`).

## Arquitetura

- Monólito modular, um app por responsabilidade em `apps/`; Postgres é a verdade. Dependências só descem (`reviews` → `exercises` → `cards` → `captures` → `vocabulary` → `courses` → `common`; `cards` e `exercises` → `language_analysis`; `accounts` e `language_analysis` só usam `common`). `test_architecture.py` cobra; app novo entra no `LAYERS`.
- View fina (serializer valida, service faz, `Response`), regra de negócio só em service, lib externa só em `providers/`.
- IA: `GeminiProvider.generate(prompt, system_instruction=, schema=)` é o único ponto com o Gemini; o schema sai do serializer e a resposta passa por ele antes de salvar. Campo no idioma aprendido leva prefixo `source_`, no idioma base `target_`: sem prefixo o Gemini ignora o idioma. Toda chamada com `store=False`.
- Toda entrada passa por serializer estrito (campo desconhecido = 400).
- Auth: allauth headless isolado em `accounts` e `config`; resto usa `get_user_model()`. Rotas exigem login por padrão.
- Captura é offline first: o app gera o id, a API sincroniza de forma idempotente e soft delete propaga.
- Ambientes: só `dsv` e `prd`; `DJANGO_ENV` obrigatório. Segredo novo obrigatório entra em `config/environment.py`.

## Estilo

- Código em inglês, texto pro usuário em pt-BR. Ruff, linha 100.
- Nomes `<X>Service`, `<X>Provider`, `<X>Serializer`; dependências injetáveis pelo construtor.
- Contrato só JSON, sem barra final; erros com mensagem pt-BR por campo.
- Testes no runner do Django, em `apps/<app>/tests/`. Rota nova que o app lê entra em `test_app_contract.py`, que compara com `test/contract/*.json` do app.

## Comandos

Subir: `README.md`. Só rodar o que gera arquivo: `ruff format .` e, no container (`docker compose exec api ...`), `python manage.py makemigrations`.
