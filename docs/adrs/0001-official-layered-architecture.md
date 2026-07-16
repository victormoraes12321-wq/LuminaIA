# ADR 0001 - Arquitetura Em Camadas Oficial

Status: Aceita

## Contexto

O LuminaAI precisa separar IA, regras de negocio, execucao, dados, renderizacao e seguranca.

## Decisao

Adotar o fluxo oficial:

```text
IA -> Planner -> Validator -> Business Layer -> Enterprise Knowledge Layer -> Backend -> Data Engine -> Frontend -> Insight Layer -> Cache Layer -> Security Layer
```

## Consequencias

- Nenhuma camada deve assumir responsabilidade de outra.
- Mudancas que violem o fluxo exigem correcao ou ADR novo.
- Frontend nao calcula regra de negocio.
- IA nao consulta banco nem executa SQL.
