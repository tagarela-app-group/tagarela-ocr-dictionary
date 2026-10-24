# PRODUCT — Tagarela API

## Papel

Backend do app Tagarela (aprender inglês com termo do dia a dia; captura por foto, áudio, texto → vocabulário com revisão espaçada). Produto completo: `docs/PRODUCT.md` do repo do app.

## Proposta

Foto → texto (OCR) → palavras com significado. Reaproveita resultado já conhecido: resposta mais rápida, menos chamada externa.

## Conceitos

- **Palavra**: token do texto, normalizado (minúsculo, sem `-`/`'` nas bordas). Só palavra solta; expressão não.
- **Definição**: texto do dicionário externo, inglês → inglês. Sem tradução.
- **Fonte** (`source`): de onde veio a palavra na resposta. `cache`, `database` ou `dictionary`.
- **Idioma**: fixo por env (`LEXICAL_LANGUAGE`, padrão `en`).
- **Captura**: rascunho do que a pessoa guardou no dia (texto digitado, foto ou áudio). Foto e áudio ficam no celular; a API guarda só o texto extraído. O app extrai o texto no próprio celular e já manda pronto; extrair no servidor fica pra comparação. A pessoa escolhe os termos (palavra ou expressão) dentro do texto, pode corrigir o texto e confirma a análise.
- **Conta**: e-mail (único, verificado por código) + nome. Entra por senha, Google ou Apple. Google/Apple com mesmo e-mail = mesma conta.

## Escopo

- Feito (v1): imagem JPEG/PNG/WEBP até 10 MB → texto extraído + definições por palavra. Health check. Admin pra ver entradas salvas. Conta: cadastro com código no e-mail, login, esqueci a senha por código, Google e Apple (Apple só iOS), token JWT. Rotas `/api/v1` exigem login. Captura (rascunho): texto, foto e áudio (inglês, até 60 s), com o texto da foto e do áudio extraído em segundo plano, termos escolhidos, texto editado, confirmar e descartar.
- Próximo: IA monta a ficha de cada termo confirmado.
- Em análise: idioma vir na rota (hoje env).

## Lacunas vs app

App espera e API não tem: tradução pt-BR, fonética, exemplo, grupo sugerido (ficha do termo, via IA), vocabulário, grupos, SRS, palavra do dia. App hoje usa mock (json-server), não esta API.
