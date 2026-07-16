# ADR 0003 - Reutilizar Blueprints, Nao Dados

Status: Aceita

## Contexto

Respostas de dados podem ficar obsoletas rapidamente, mas estrategias analiticas podem ser reutilizadas.

## Decisao

Reutilizar blueprints, fingerprints e analytical packages quando compativeis. Consultar dados novamente conforme backend/cache/politica.

## Consequencias

- Cache de inteligencia e permitido.
- Cache de dados precisa respeitar politica de atualizacao.
- Blueprints nao devem armazenar dados finais.
