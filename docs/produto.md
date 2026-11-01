# Produto e detalhes da API

## Produto

- Conta: um e-mail = uma pessoa, entra por senha, Google ou Apple.
- País de origem fica na conta (ISO alpha-2 + `XK`, opcional) e vira bandeira no avatar. Não é idioma.
- Curso: "aprende X por meio de Y" (en, es, pt; X ≠ Y). O app fica no Y do curso ativo, então Y só pode ser idioma em que o app está traduzido. Conta tem vários, um ativo; mesmo X com outro Y é outro curso. Capturas, termos e grupos vivem no curso. Rotas de estudo usam o curso ativo. Leitura sem curso volta vazia e não cria nada; `POST` que precisa de curso (grupo, captura sem `course`) começa inglês por meio do português.
- Captura: texto que a pessoa revisa, marca termos e confirma; termos confirmados vão pro vocabulário do curso da captura. O app manda o curso em que ela nasceu (offline first).
- Vocabulário: termo único por curso, organizado em grupos que só a pessoa cria. IA nunca organiza.
- Falta: revisão espaçada de verdade (a de hoje é provisória).
- Exercícios (minigames, `exercises`): a IA gera por termo e tipo (`kind`) de 1 a `EXERCISE_VARIATIONS` variações numa chamada só, na 1ª vez que alguém pede; ficam salvas e não regeneram. Usa o significado da ficha, quando existe. Só o que é exemplo vai no idioma aprendido (frase, resposta, o que ouvir); tradução e explicação vão no idioma base, com o idioma aprendido entre `*asteriscos*`. Todo exercício ensina algo além do termo (`extra`). Contrato e como criar tipo novo: `docs/exercises.md`.
- Revisão (`reviews`), provisória pra teste: termo abaixo do nível 5 está pendente; cada revisão sobe 1 nível, ver a resposta não sobe; nível 5 = dominado. Sessão: até `REVIEW_SESSION_SIZE` termos do curso ativo, menos revisados primeiro, embaralhados, tipo sorteado entre os que o app manda em `kinds` (sem `kinds`: todos). A revisão serve primeiro a variação menos usada. A regra mora em `reviews/policy.py`: a repetição espaçada troca só ela; `ReviewAttempt` já guarda o histórico.
- Palavra do dia (`daily_words`): a IA escolhe uma por curso e dia (data do servidor) no primeiro `GET /daily-word`; fica salva e não regenera. Evita até `DAILY_WORD_AVOID_LIMIT` palavras passadas e até o mesmo tanto de termos do curso. `POST /daily-word/save` manda pro vocabulário sem grupo; `term` vem preenchido quando a palavra está no vocabulário. Sem curso: 404.
- Análise linguística (`language_analysis`): sem rota própria e sem salvar nada; só a ficha chama.
- Ficha do termo (`cards`): gerada pela análise na 1ª abertura, com a captura mais recente do termo como contexto e os idiomas do curso; fica salva e não regenera. Frente, palavras, formas errada e certa da armadilha (`source_pitfall_wrong`, `source_pitfall_right`) e falas do diálogo no idioma que a pessoa aprende; verso (tradução, explicação), ao pé da letra, armadilha, imagem, nota de formalidade, situações (`base.*`) e tradução dos exemplos e do diálogo no idioma base. Campo que o app não lê não é pedido ao Gemini. Em `pitfall`, `imagine` e `formality_note` (idioma base), o que está no idioma aprendido vem entre asteriscos (`*on the fence*`) pro app destacar; ficha antiga vem sem. Enche `Term.translation`. O que a pessoa revelou fica salvo: `revealed` (pra lembrar), `pitfall_revealed` (armadilha) e `formality_revealed` (nota de formalidade), cada um no seu campo pra um não entregar o outro.

## Ambientes

- Só dois: `dsv` (local, no compose) e `prd`. `DJANGO_ENV` é obrigatório: sem ele a API não sobe.
- Um `settings.py` só; o que muda em prd fica no bloco final.
- `config/environment.py` recusa subir prd com valor inseguro ou de exemplo. Segredo novo obrigatório entra lá. Domínio `.invalid` nos exemplos marca o que falta trocar.
- Dockerfile: alvo padrão `prd`, pra hospedagem que builda sem `--target` nunca subir `runserver`; o compose usa `dsv`. `--timeout` do gunicorn acima da espera do app pela IA (45 s). Migrate em prd é passo separado. Roteiro: `docs/deploy.md`.

## Regras e código em detalhe

2. Contrato `/api/v1`: até o primeiro deploy, o app é o único consumidor e o contrato pode mudar sem versão nova. Campo sai da resposta: o app muda antes. Campo novo na requisição ou rota nova: a API muda antes, porque o serializer estrito devolve 400. Do primeiro deploy em diante é público: não quebrar. Incompatível: avisar + nova versão.
4. Model mudou: migration junto. Do primeiro deploy em diante, nunca editar migration mergeada. Preencher dado e mudar a tabela: migrations separadas (Postgres recusa no mesmo passo). Migration de dados testa com `MigrationTestCase`.
- Monólito modular, um app por responsabilidade em `apps/`; Postgres é a verdade. Dependências só descem (`reviews` → `exercises` → `cards` → `captures` → `vocabulary` → `courses` → `common`; `daily_words` → `cards`; `cards`, `exercises` e `daily_words` → `language_analysis`; `accounts` e `language_analysis` só usam `common`). Testes podem subir. `apps/common/tests/test_architecture.py` cobra; app novo entra no `LAYERS`.
- IA: `GeminiProvider.generate(prompt, system_instruction=, schema=)` (em `language_analysis`) é o único ponto com o Gemini; cada uso traz o próprio prompt e serializer; o schema sai do serializer (`common/schema.py`), e a resposta passa por ele antes de salvar. Campo no idioma aprendido leva prefixo `source_`, no idioma base `target_`: sem prefixo o Gemini ignora o pedido de idioma. Toda chamada vai com `store=False`, sem histórico.
- Contrato com o app: `apps/common/tests/test_app_contract.py` compara a resposta real com `test/contract/*.json` do app, na `develop`. Só roda com `APP_CONTRACT_DIR`, que a esteira define. Rota nova que o app lê entra lá.
