# PRODUCT — Tagarela API

Backend do app Tagarela. Produto completo: `docs/PRODUCT.md` do repo do app.

## Papel

Guarda a conta, as capturas (só texto: foto e áudio ficam no celular) e o vocabulário. Não processa foto nem áudio.

## Conceitos

- **Conta**: e-mail único verificado por código + nome. Senha, Google ou Apple. Mesmo e-mail = mesma conta.
- **Captura**: rascunho com texto. Pessoa escolhe os termos, pode corrigir o texto e confirma a análise.
- **Termo**: palavra ou expressão confirmada. Um por pessoa (maiúscula e espaço não contam).
- **Grupo**: nome, ícone e cor, criado pela pessoa. Termo novo fica sem grupo até ela mover. IA nunca escolhe grupo.

## Escopo

- Feito: conta (cadastro, login, esqueci a senha, Google, Apple), captura (criar, editar, confirmar, descartar, sincronizar), vocabulário (termo entra ao confirmar, criar, editar e apagar grupo, mover e apagar termo).
- Falta (o app espera): ficha do termo via IA (tradução, fonética, exemplo), SRS, palavra do dia.
