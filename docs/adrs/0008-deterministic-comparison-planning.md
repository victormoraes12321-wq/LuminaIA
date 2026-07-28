# ADR 0008 - Planejamento Comparativo Deterministico Separado Da Execucao

- Status: aceito
- Data: 2026-07-27

## Contexto

Os Contratos Analiticos V2 representam comparacoes e o Normalizador Temporal
V2 produz janelas canonicas. Faltava uma autoridade unica para transformar
essa intencao em operandos, filtros, alinhamento, baseline, calculos
declarativos e estrategia, sem depender da frase original ou executar dados.

Manter essa logica distribuida em parsers, planners legados e executores
permitiria perda de operandos, contaminacao de filtros, fallback semantico
incorreto e divergencia entre pipelines V1/V2.

## Decisao

Adotar `ComparisonPlanner`, versao
`lumina.comparison-planner/1.0`, como autoridade deterministica de planejamento
comparativo.

O planner recebe `QueryIntentV2`, `TimeWindow` ja normalizada e um
`ComparisonPlanningContext` confiavel. Catalogos de metrica, dimensao,
entidade e meta sao injetados por uma interface sem conexao de banco. A saida
e um `ComparisonPlanningResult` validado contendo `QueryPlanV2` e definicao
estrutural complementar.

O planner nao acessa banco, Oracle ou OpenAI, nao executa SQL e nao calcula
valores. O tenant e suas permissoes sao derivados do backend. Filtros usam
identificadores logicos, operandos preservam ordem e N itens, e limites
explicitos bloqueiam complexidade excessiva sem truncamento.

O rollout e reversivel por flags. Shadow mode compara somente estrutura
sanitizada. O builder legado permanece disponivel para rollback, e o adaptador
recusa representacoes que perderiam informacao.

## Consequencias

Beneficios:

- uma unica fonte de verdade entre normalizacao e execucao;
- planos idempotentes, serializaveis, auditaveis e seguros para concorrencia;
- separacao clara entre planejamento, execucao e calculo;
- suporte estrutural a periodo, entidade, metrica, meta e N operandos;
- cache e observabilidade baseados em identidade semantica sanitizada;
- caminho preparado para um executor universal.

Custos:

- o executor atual nao consome todos os planos novos;
- metas dependem de provider oficial;
- catalogos governados precisam evoluir junto das metricas e dimensoes;
- divergencias do shadow mode precisam ser acompanhadas durante o rollout.

## Alternativas Rejeitadas

- gerar SQL diretamente pela IA;
- adicionar regras por frase completa;
- calcular comparacoes dentro do planner;
- reutilizar somente o comparison engine de valores;
- reduzir estruturas multiplas para dois operandos no adaptador legado;
- usar faturamento, Cliente ou zero como fallback universal.

## Proxima Decisao

O Prompt 06 definira o executor universal que consumira `QueryPlanV2`, obterá
datasets autorizados e aplicara os calculos declarados. Esta ADR nao antecipa
essa responsabilidade.
