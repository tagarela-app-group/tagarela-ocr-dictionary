# PRODUCT — Tagarela API

## Papel

Backend do app Tagarela (aprender inglês com termo do dia a dia; captura por foto, áudio, texto → vocabulário com revisão espaçada). Produto completo: `docs/PRODUCT.md` do repo do app.

## Proposta

Guarda a conta, o que a pessoa capturou (texto digitado ou extraído da foto e do áudio no próprio celular, termos escolhidos, confirmação da análise) e o vocabulário: termos confirmados e grupos que a pessoa cria. Não processa foto nem áudio: isso é do app.

## Conceitos

- **Captura**: rascunho do que a pessoa guardou no dia (texto digitado, foto ou áudio). Foto e áudio ficam no celular; a API guarda só o texto extraído. O app extrai o texto no próprio celular e já manda pronto; a API não recebe arquivo. A pessoa escolhe os termos (palavra ou expressão) dentro do texto, pode corrigir o texto e confirma a análise.
- **Termo** (vocabulário): palavra ou expressão confirmada numa captura. Um por pessoa: o mesmo termo de novo (maiúscula e espaço não contam) não entra.
- **Grupo**: coleção de termos com nome, ícone e cor, criada pela pessoa. Termo novo fica sem grupo até a pessoa mover. A pessoa escolhe o grupo, nunca a IA.
- **Conta**: e-mail (único, verificado por código) + nome. Entra por senha, Google ou Apple. Google/Apple com mesmo e-mail = mesma conta.

## Escopo

- Feito (v1): health check. Admin pra ver contas e capturas. Conta: cadastro com código no e-mail, login, esqueci a senha por código, Google e Apple (Apple só iOS), token JWT. Rotas `/api/v1` exigem login. Captura (rascunho): texto, foto e áudio, sempre com o texto já extraído no celular, termos escolhidos, texto editado, confirmar e descartar. Vocabulário: termo entra ao confirmar (sem repetir), criar grupo, mover termos entre grupos e de volta pra Sem grupo.
- Próximo: IA monta a ficha de cada termo confirmado. Editar e apagar grupo.

## Lacunas vs app

App espera e API não tem: tradução pt-BR, fonética, exemplo (ficha do termo, via IA), SRS (nível muda com a revisão), editar e apagar grupo, palavra do dia.
