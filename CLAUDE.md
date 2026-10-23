# CLAUDE.md — Tagarela API

Backend Django REST do Tagarela: foto → OCR → palavras com definição. Este arquivo: regras gerais + mapa dos docs.

## Docs

Ler só o doc do assunto do pedido. Não ler todos por padrão.

| Doc | Assunto |
| --- | --- |
| `docs/PRODUCT.md` | Produto: papel da API, conceitos, escopo, lacunas vs app. |
| `docs/ARCHITECTURE.md` | Técnico: stack, pastas, fluxo, endpoints, dados, config, convenções, testes, git e CI. |

App cliente (Flutter): repo `tagarela-app-group/tagarela`.

## Regras

1. Início de chat novo: ativar skill `caveman` (nível `full`).
2. Cada coisa no seu lugar. Conteúdo novo vai no doc do assunto. Doc não repete outro doc.
3. Docs: só o necessário. Objetivo, estilo caveman, sem perder informação.
4. View fina: serializer valida → service faz → `Response`. Regra de negócio só em service.
5. Lib ou serviço externo (PaddleOCR, dicionário, Redis) só dentro de `providers/` ou `cache.py`. Resto do código não importa direto.
6. Limite, URL, TTL, idioma: sempre setting (env → `config/settings.py` → `.env.example`). Nunca valor solto no código. Segredo só no `.env` (fora do git).
7. Contrato `/api/v1` é público (app consome). Não quebrar. Mudança incompatível: avisar usuário + nova versão.
8. Model mudou: migration junto (`makemigrations`). Nunca editar migration já mergeada.
9. Mudou endpoint, contrato, model, fluxo ou env: atualizar doc do assunto junto.
10. Seguir sempre boas práticas de código, estrutura e arquitetura. Sem camada nova sem necessidade.
11. Pedido quebra regra ou boa prática: avisar usuário antes de fazer. Dizer qual regra e propor alternativa.
12. Toda task que cria ou altera código (service, provider, cache, validator, view, model): teste junto, sempre que fizer sentido. Bug corrigido: teste que reproduz. Sem teste: dizer o motivo no PR. Regras em `docs/ARCHITECTURE.md` (Testes).
13. Task finalizada: branch própria + commit + push + PR pra `develop`, na hora, sem perguntar. Fluxo em `docs/ARCHITECTURE.md` (Git). Commit e PR sem `Co-Authored-By` nem outra assinatura de IA.
14. Merge: PR pra `develop` com esteira verde = eu faço. PR `develop` → `main` (prod) = só o usuário aprova. Nunca commitar direto na `develop` nem na `main`.
15. Sem comentário no código. Vale pra config também (workflow, compose, Dockerfile, toml, requirements). Nome claro explica o quê. Porquê vai no doc do assunto ou no PR.
