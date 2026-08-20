# ADR 0009 - Execucao Comparativa Deterministica

## Status

Aceito em 2026-07-28.

## Contexto

O contrato V2 e o normalizador temporal preservam a intencao. O planner
comparativo preserva operandos, filtros, periodos, baseline e alinhamento, mas
nao executa dados. O executor legado converte `Decimal` para `float`, aceita
apenas estruturas reduzidas e nao e autoridade adequada para comparacoes
financeiras universais.

## Decisao

Adotar `lumina.comparison-executor/1.0` como autoridade de execucao de planos
comparativos `READY`.

O executor:

- usa somente PostgreSQL analitico tenant-scoped;
- exige catalogo governado para identificadores e formulas;
- usa binds para todos os valores;
- preserva `Decimal`;
- alinha por IDs canonicos;
- calcula delta como target menos baseline;
- calcula percentual contra o modulo do baseline;
- explicita zero, nulo, missing bucket, truncamento e partial;
- produz validacao matematica e proveniencia;
- converte para V2 e V1 sem reexecutar dados;
- permanece atras de flags desligadas por padrao.

Oracle continua limitado a sync e reconciliacao tecnica. OpenAI nao participa
da execucao ou da matematica.

## Consequencias

Comparacoes passam a ser reproduziveis e auditaveis. Fonte sem coluna de
tenant comprovada e bloqueada. Metricas sem fonte oficial, como lucro ou
vendas pendentes, continuam indisponiveis. A exigencia de isolamento pode
impedir rollout em clones antigos ate que a fonte analitica seja corrigida.

O resultado canonico suporta N operandos; consumidores V1 recebem fallback de
tabela e sidecar quando nao conseguem representar toda a estrutura.

## Alternativas Rejeitadas

- reutilizar numeros redigidos pela IA;
- adaptar todas as comparacoes ao executor legado de dois operandos;
- gerar SQL a partir de texto;
- usar Oracle durante a consulta;
- converter valores financeiros para `float`;
- preencher meta, nulo ou bucket ausente com numero inferido;
- afirmar isolamento apenas porque existe um tenant no request.

## Rollback

Desligar `COMPARISON_EXECUTOR_V2_ENABLED` e
`COMPARISON_EXECUTOR_V2_SHADOW_MODE`. O planner, consultas simples e payload
legado continuam disponiveis.
