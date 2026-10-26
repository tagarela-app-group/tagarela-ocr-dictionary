# CLAUDE.md — Tagarela API

Backend Django REST do Tagarela (app Flutter em `../mob`). Guarda conta, capturas (só texto) e vocabulário. Foto e áudio viram texto no celular.

## Produto

- Conta: um e-mail = uma pessoa, entra por senha, Google ou Apple.
- País de origem fica na conta (ISO alpha-2 + `XK`, opcional) e vira bandeira no avatar. Não é idioma: idioma da interface é escolha do aparelho, a API não guarda.
- Curso: "aprende X por meio de Y" (en, es, pt; X ≠ Y). Conta tem vários, um ativo; mesmo X com outro Y é outro curso. Capturas, termos e grupos vivem no curso. Rotas de estudo usam o curso ativo; conta sem curso ganha inglês por meio do português.
- Captura: texto que a pessoa revisa, marca termos e confirma; termos confirmados vão pro vocabulário do curso da captura. O app manda o curso em que ela nasceu (offline first).
- Vocabulário: termo único por curso, organizado em grupos que só a pessoa cria. IA nunca organiza.
- App já espera e falta: revisão espaçada, palavra do dia, exercícios da ficha.
- Análise linguística: recebe texto e termo opcional, consulta Gemini sem persistir resultados e devolve uma ficha estruturada.
- Ficha do termo (`cards`): gerada pela análise na 1ª abertura, com a captura mais recente do termo como contexto e os idiomas do curso; fica salva e não regenera. Frente, palavras, formalidade, situações, armadilha (texto e formas errada e certa), imagem pra lembrar e falas do diálogo no idioma que a pessoa aprende; verso (tradução, explicação), ao pé da letra e tradução dos exemplos e do diálogo no idioma base. Armadilha e imagem também seguem no idioma base (`base.pitfall`, `base.imagine`) pra não quebrar o contrato. Enche `Term.translation`. O que a pessoa revelou fica salvo (`revealed`).

## Regras

0. Início de sessão: ativar skill `caveman` nível `full`.
1. Antes de alterar algo (código, doc, config): propor (o quê, onde, opções, recomendação) e esperar ok. Pedido fere regra/boa prática: avisar e propor alternativa. Sem camada nova sem necessidade.
2. Contrato `/api/v1` é público: não quebrar. Incompatível: avisar + nova versão.
3. Configurável (limite, URL, TTL) vira setting via env, refletido no `.env.example`. Segredo só no `.env`.
4. Model mudou: migration junto. Nunca editar migration mergeada. Preencher dado e mudar a tabela: migrations separadas (Postgres recusa no mesmo passo). Migration de dados testa com `MigrationTestCase`.
5. Código novo/alterado: com teste. Bug: teste que reproduz. Testes nunca usam rede real.
6. Sem comentário em código/config. Porquê vai aqui ou no PR.
7. Mudou regra ou decisão: atualizar aqui. Guia, não inventário: só o que o código não mostra.
8. Git, sem perguntar: branch da `develop` (`feat/ fix/ docs/ ci/ chore/`) → commit → push → PR pra `develop`. Conventional Commits pt-BR, enxuto, sem assinatura de IA. Esteira verde: `gh pr merge <n> --repo tagarela-app-group/tagarela-ocr-dictionary --squash --delete-branch` (isolado, sem `cd`/`&&`), depois `git switch develop && git pull`.
9. Nunca commitar direto em `develop`/`main`. `develop` → `main` só o usuário.
10. Dependência nova: checar manutenção e contar ao usuário; nativa ou pesada: perguntar.
11. Fim de task/troca de assunto: sugerir `/compact manter: ...` ou `/clear`.

## Arquitetura

- Monólito modular, um app por responsabilidade em `apps/`; Postgres é a verdade. Dependências só descem (`cards` → `captures` → `vocabulary` → `courses` → `common`; `cards` → `language_analysis`).
- Camadas: view fina (serializer valida, service faz, `Response`), regra de negócio só em service, lib externa só em `providers/`.
- `language_analysis` usa `GeminiProvider`; o endpoint exige a autenticação padrão e não mantém histórico de interações.
- Toda entrada passa por serializer estrito (campo desconhecido = 400).
- Auth: allauth headless isolado em `accounts` e `config`; resto do app usa `get_user_model()`. Rotas exigem login por padrão.
- Captura é offline first: o app gera o id, a API sincroniza de forma idempotente e soft delete propaga entre aparelhos.
- Trabalho pesado (IA, processamento): decidir fila quando surgir.

## Estilo

- Código em inglês, texto pro usuário em pt-BR. Ruff, linha 100.
- Nomes `<X>Service`, `<X>Provider`, `<X>Serializer`; dependências injetáveis pelo construtor.
- Contrato só JSON, sem barra final; erros com mensagem pt-BR por campo.
- Testes no runner do Django, em `apps/<app>/tests/`.

## Comandos

Subir: `README.md`. No container (`docker compose exec api ...`): `python manage.py test -v 0`, `python manage.py makemigrations`. Fora: `ruff format .`, `ruff check --fix .`. Antes do push: ruff, testes, `makemigrations --check --dry-run`.
