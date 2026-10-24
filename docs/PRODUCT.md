# PRODUCT — Tagarela API

## Papel

Backend do app Tagarela (aprender inglês com termo do dia a dia; captura por foto, áudio, texto → vocabulário com revisão espaçada). Produto completo: `docs/PRODUCT.md` do repo do app.

## Proposta

Guarda a conta e o que a pessoa capturou: o texto (digitado, ou extraído da foto e do áudio no próprio celular), os termos escolhidos e a confirmação da análise. Não processa foto nem áudio: isso é do app.

## Conceitos

- **Captura**: rascunho do que a pessoa guardou no dia (texto digitado, foto ou áudio). Foto e áudio ficam no celular; a API guarda só o texto extraído. O app extrai o texto no próprio celular e já manda pronto; a API não recebe arquivo. A pessoa escolhe os termos (palavra ou expressão) dentro do texto, pode corrigir o texto e confirma a análise.
- **Conta**: e-mail (único, verificado por código) + nome. Entra por senha, Google ou Apple. Google/Apple com mesmo e-mail = mesma conta.

## Escopo

- Feito (v1): health check. Admin pra ver contas e capturas. Conta: cadastro com código no e-mail, login, esqueci a senha por código, Google e Apple (Apple só iOS), token JWT. Rotas `/api/v1` exigem login. Captura (rascunho): texto, foto e áudio, sempre com o texto já extraído no celular, termos escolhidos, texto editado, confirmar e descartar.
- Próximo: IA monta a ficha de cada termo confirmado.

## Lacunas vs app

App espera e API não tem: tradução pt-BR, fonética, exemplo, grupo sugerido (ficha do termo, via IA), vocabulário, grupos, SRS, palavra do dia. App hoje usa mock (json-server), não esta API.
