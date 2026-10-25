# CLAUDE.md — Tagarela API

Backend Django REST do Tagarela (app Flutter em `../mob`). Guarda conta, capturas (só texto) e vocabulário. Foto e áudio viram texto no celular.

## Produto

- Conta: um e-mail = uma pessoa, entra por senha, Google ou Apple.
- Captura: texto que a pessoa revisa, marca termos e confirma; termos confirmados vão pro vocabulário.
- Vocabulário: termo único por pessoa, organizado em grupos que só a pessoa cria. IA nunca organiza.
- App já espera e falta: ficha do termo via IA, revisão espaçada, palavra do dia.

## Regras

0. Início de sessão: ativar skill `caveman` nível `full`.
1. Antes de alterar algo (código, doc, config): propor (o quê, onde, opções, recomendação) e esperar ok. Pedido fere regra/boa prática: avisar e propor alternativa. Sem camada nova sem necessidade.
2. Contrato `/api/v1` é público: não quebrar. Incompatível: avisar + nova versão.
3. Configurável (limite, URL, TTL) vira setting via env, refletido no `.env.example`. Segredo só no `.env`.
4. Model mudou: migration junto. Nunca editar migration mergeada.
5. Código novo/alterado: com teste. Bug: teste que reproduz. Testes nunca usam rede real.
6. Sem comentário em código/config. Porquê vai aqui ou no PR.
7. Mudou regra ou decisão: atualizar aqui. Guia, não inventário: só o que o código não mostra.
8. Git, sem perguntar: branch da `develop` (`feat/ fix/ docs/ ci/ chore/`) → commit → push → PR pra `develop`. Conventional Commits pt-BR, enxuto, sem assinatura de IA. Esteira verde: `gh pr merge <n> --repo tagarela-app-group/tagarela-ocr-dictionary --squash --delete-branch` (isolado, sem `cd`/`&&`), depois `git switch develop && git pull`.
9. Nunca commitar direto em `develop`/`main`. `develop` → `main` só o usuário.
10. Dependência nova: checar manutenção e contar ao usuário; nativa ou pesada: perguntar.
11. Fim de task/troca de assunto: sugerir `/compact manter: ...` ou `/clear`.

## Arquitetura

- Monólito modular, um app por responsabilidade em `apps/`; Postgres é a verdade. Dependências só descem (`captures` → `vocabulary` → `common`).
- Camadas: view fina (serializer valida, service faz, `Response`), regra de negócio só em service, lib externa só em `providers/`.
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
