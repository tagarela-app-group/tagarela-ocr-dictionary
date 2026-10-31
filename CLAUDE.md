# CLAUDE.md — Tagarela API

Backend Django REST do Tagarela (app Flutter em `../mob`). Guarda conta, capturas (só texto) e vocabulário. Foto e áudio viram texto no celular.

## Produto

- Conta: um e-mail = uma pessoa, entra por senha, Google ou Apple.
- País de origem fica na conta (ISO alpha-2 + `XK`, opcional) e vira bandeira no avatar. Não é idioma.
- Curso: "aprende X por meio de Y" (en, es, pt; X ≠ Y). O app fica no Y do curso ativo, então Y só pode ser idioma em que o app está traduzido. Conta tem vários, um ativo; mesmo X com outro Y é outro curso. Capturas, termos e grupos vivem no curso. Rotas de estudo usam o curso ativo. Leitura sem curso volta vazia e não cria nada; `POST` que precisa de curso (grupo, captura sem `course`) começa inglês por meio do português.
- Captura: texto que a pessoa revisa, marca termos e confirma; termos confirmados vão pro vocabulário do curso da captura. O app manda o curso em que ela nasceu (offline first).
- Vocabulário: termo único por curso, organizado em grupos que só a pessoa cria. IA nunca organiza.
- Falta: revisão espaçada de verdade (a de hoje é provisória).
- Exercícios (minigames, `exercises`): a IA gera por termo e tipo (`kind`) de 1 a `EXERCISE_VARIATIONS` variações numa chamada só, na 1ª vez que alguém pede; ficam salvas e não regeneram. Usa o significado da ficha, quando existe. Só o que é exemplo vai no idioma aprendido (frase, resposta, o que ouvir); tradução e explicação vão no idioma base, com o idioma aprendido entre `*asteriscos*`. Todo exercício ensina algo além do termo (`extra`). Contrato e como criar tipo novo: `docs/exercises.md`.
- Revisão (`reviews`), provisória pra teste: termo abaixo do nível 5 está pendente; cada revisão sobe 1 nível, ver a resposta não sobe; nível 5 = dominado. Sessão: até `REVIEW_SESSION_SIZE` termos do curso ativo, menos revisados primeiro, embaralhados, tipo sorteado entre os que o app manda em `kinds` (sem `kinds`: todos). A revisão serve primeiro a variação menos usada. A regra mora em `reviews/policy.py`: a repetição espaçada troca só ela; `ReviewAttempt` já guarda o histórico.
- Análise linguística (`language_analysis`): sem rota própria e sem salvar nada; só a ficha chama.
- Ficha do termo (`cards`): gerada pela análise na 1ª abertura, com a captura mais recente do termo como contexto e os idiomas do curso; fica salva e não regenera. Frente, palavras, formas errada e certa da armadilha (`source_pitfall_wrong`, `source_pitfall_right`) e falas do diálogo no idioma que a pessoa aprende; verso (tradução, explicação), ao pé da letra, armadilha, imagem, nota de formalidade, situações (`base.*`) e tradução dos exemplos e do diálogo no idioma base. Campo que o app não lê não é pedido ao Gemini. Em `pitfall`, `imagine` e `formality_note` (idioma base), o que está no idioma aprendido vem entre asteriscos (`*on the fence*`) pro app destacar; ficha antiga vem sem. Enche `Term.translation`. O que a pessoa revelou fica salvo: `revealed` (pra lembrar), `pitfall_revealed` (armadilha) e `formality_revealed` (nota de formalidade), cada um no seu campo pra um não entregar o outro.

## Regras

0. Início de sessão: ativar skill `caveman` nível `full`.
1. Antes de alterar algo (código, doc, config): propor (o quê, onde, opções, recomendação) e esperar ok. Pedido fere regra/boa prática: avisar e propor alternativa. Sem camada nova sem necessidade.
2. Contrato `/api/v1`: até o primeiro deploy, o app é o único consumidor e o contrato pode mudar sem versão nova. Campo sai da resposta: o app muda antes. Campo novo na requisição ou rota nova: a API muda antes, porque o serializer estrito devolve 400. Do primeiro deploy em diante é público: não quebrar. Incompatível: avisar + nova versão.
3. Configurável (limite, URL, TTL) vira setting via env, refletido em `.env.dsv.example` e `.env.prd.example`. Segredo só no `.env.dsv`, no `.env.prd` ou no secret da hospedagem.
4. Model mudou: migration junto. Do primeiro deploy em diante, nunca editar migration mergeada. Preencher dado e mudar a tabela: migrations separadas (Postgres recusa no mesmo passo). Migration de dados testa com `MigrationTestCase`.
5. Código novo/alterado: com teste. Bug: teste que reproduz. Testes nunca usam rede real. Teste existe pra pegar bug: cobra regra, contrato, validação e borda. Não testa cópia do código (texto de prompt, constante, valor de setting), o Django, o DRF ou lib, nem o que outro teste já cobre (login obrigatório é o padrão, coberto no `test_api_auth.py`). Antes de escrever, dizer que bug ele pegaria; nenhum, não escreve.
6. Sem comentário em código/config. Porquê vai aqui ou no PR.
7. Mudou regra ou decisão: atualizar aqui. Guia, não inventário: só o que o código não mostra.
8. Git, sem perguntar: branch da `develop` (`feat/ fix/ docs/ ci/ chore/`) → commit → push → PR pra `develop`. Conventional Commits pt-BR, enxuto, sem assinatura de IA. Esteira verde: `gh pr merge <n> --repo tagarela-app-group/tagarela-ocr-dictionary --squash --delete-branch` (isolado, sem `cd`/`&&`), depois `git switch develop && git pull && git branch -D <branch>`.
9. Nunca commitar direto em `develop`/`main`. `develop` → `main` só o usuário.
10. Dependência nova: checar manutenção e contar ao usuário; nativa ou pesada: perguntar.
11. Fim de task/troca de assunto: sugerir `/compact manter: ...` ou `/clear`.
12. Tipagem estrita em código novo/alterado: sem `Any`; parâmetros e retornos anotados. Dado de fora (JSON, IA) entra como `object`/`Mapping[str, object]` e vira tipo de verdade (serializer, `TypedDict`, dataclass) antes de circular.
13. Sem repetição: antes de escrever, procurar o que já existe em `apps/` e nos testes. Código igual em 2 lugares vira uma peça só, no lugar certo (service, `common/`, helper de teste). Igual por acaso, com regra diferente, fica separado. Repetição antiga no arquivo mexido: avisar e propor extrair. A esteira roda o `jscpd` e falha com qualquer trecho repetido.

## Arquitetura

- Monólito modular, um app por responsabilidade em `apps/`; Postgres é a verdade. Dependências só descem (`reviews` → `exercises` → `cards` → `captures` → `vocabulary` → `courses` → `common`; `cards` e `exercises` → `language_analysis`; `accounts` e `language_analysis` só usam `common`). Testes podem subir. `apps/common/tests/test_architecture.py` cobra; app novo entra no `LAYERS`.
- Camadas: view fina (serializer valida, service faz, `Response`), regra de negócio só em service, lib externa só em `providers/`.
- IA: `GeminiProvider.generate(prompt, system_instruction=, schema=)` (em `language_analysis`) é o único ponto com o Gemini; cada uso traz o próprio prompt e serializer; o schema sai do serializer (`common/schema.py`), e a resposta passa por ele antes de salvar. Campo no idioma aprendido leva prefixo `source_`, no idioma base `target_`: sem prefixo o Gemini ignora o pedido de idioma. Toda chamada vai com `store=False`, sem histórico.
- Toda entrada passa por serializer estrito (campo desconhecido = 400).
- Auth: allauth headless isolado em `accounts` e `config`; resto do app usa `get_user_model()`. Rotas exigem login por padrão.
- Captura é offline first: o app gera o id, a API sincroniza de forma idempotente e soft delete propaga entre aparelhos.
- Trabalho pesado (IA, processamento): decidir fila quando surgir.

## Ambientes

- Só dois: `dsv` (local, no compose) e `prd`. `DJANGO_ENV` é obrigatório: sem ele a API não sobe.
- Um `settings.py` só; o que muda em prd fica no bloco final.
- `config/environment.py` recusa subir prd com valor inseguro ou de exemplo. Segredo novo obrigatório entra lá. Domínio `.invalid` nos exemplos marca o que falta trocar.
- Dockerfile: alvo padrão `prd`, pra hospedagem que builda sem `--target` nunca subir `runserver`; o compose usa `dsv`. `--timeout` do gunicorn acima da espera do app pela IA (45 s). Migrate em prd é passo separado. Roteiro: `docs/deploy.md`.

## Estilo

- Código em inglês, texto pro usuário em pt-BR. Ruff, linha 100.
- Nomes `<X>Service`, `<X>Provider`, `<X>Serializer`; dependências injetáveis pelo construtor.
- Contrato só JSON, sem barra final; erros com mensagem pt-BR por campo.
- Testes no runner do Django, em `apps/<app>/tests/`.
- Contrato com o app: `apps/common/tests/test_app_contract.py` compara a resposta real com `test/contract/*.json` do app, na `develop`. Só roda com `APP_CONTRACT_DIR`, que a esteira define. Rota nova que o app lê entra lá.

## Comandos

Subir: `README.md`. No container (`docker compose exec api ...`): `python manage.py test -v 0`, `python manage.py makemigrations`. Fora: `ruff format .`, `ruff check --fix .`, `npx jscpd@5.4.1 apps config --format python --ignore "**/migrations/**" --threshold 0`. Antes do push: só o que gera arquivo (`ruff format .`, `makemigrations`). Testes, análise e checagem de migration ficam pra esteira.
