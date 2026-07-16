# ADR 0004 - Dashboard Studio Como Camada Visual

Status: Aceita

## Contexto

Usuarios precisam personalizar dashboards sem quebrar inteligencia analitica.

## Decisao

Dashboard Studio altera Dashboard Template e Dashboard Instance, mas nao altera Blueprint, Business Layer, formulas, KPIs ou Data Platform.

## Consequencias

- Personalizacao visual fica isolada.
- Rollback/versionamento visual pode ocorrer sem recalcular regra analitica.
- Frontend/backend devem rejeitar mudancas que tentem alterar calculos via Studio.
