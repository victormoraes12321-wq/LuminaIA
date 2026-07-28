# Apresentacao Comparativa V2

## Objetivo E Versao

A camada `lumina.comparison-presentation/1.0` transforma resultados
deterministicos do executor comparativo em uma representacao visual local,
auditavel e estritamente apresentacional.

Fluxo:

```text
AnalyticalResponseV2
  -> ComparisonPresentationAdapter
  -> ComparisonPresentationModel
  -> DynamicRenderer
  -> ComparisonRenderer
  -> tabela, indicadores e Apache ECharts
```

O frontend nao calcula diferenca, percentual, direcao, participacao, ranking,
atingimento ou baseline. Esses valores pertencem ao backend. A camada apenas
preserva, classifica, formata e exibe o que foi recebido.

## Implementacao

Os arquivos vivem em `frontend/components/comparison/`:

- `comparisonPresentationTypes.ts`: tipos estritos e versao;
- `comparisonPresentationAdapter.ts`: fronteira V2/V1;
- `comparisonFormatters.ts`: formatacao central de unidades e estados;
- `ComparisonRenderer.tsx`: superficie visual, tabela, estados e controles;
- `ComparisonChart.tsx`: opcoes ECharts;
- `comparisonExport.ts`: exportacao CSV com valores brutos;
- `comparisonFeatureFlags.ts`: rollout e shadow mode;
- `comparisonTelemetry.ts`: telemetria exclusivamente estrutural;
- `index.ts`: API local da camada.

`InlineDashboardRuntime` detecta a comparacao, cria o modelo uma vez e entrega
o resultado ao `DynamicRenderer`. Com a flag desligada, o runtime legado
continua sendo a superficie ativa.

## Presentation Model

`ComparisonPresentationModel` preserva:

- identificador, tipo, titulo, status, parcialidade e truncamento;
- baseline e targets;
- operandos, calculos, datasets e visualizacoes em ordem;
- alinhamento, validacao, proveniencia, warnings e erros;
- politicas de exibicao, acesso e exportacao;
- metadados tecnicos sanitizados quando o perfil permite.

Cada operando mantem valor bruto e formatado separados. Cada calculo mantem o
resultado bruto recebido, direcao, status, denominador zero e motivo de nao
aplicabilidade. Datasets preservam linhas brutas, colunas, chaves de
alinhamento, buckets ausentes/nulos e sinal de truncamento.

O adapter nao modifica o payload de entrada e e idempotente. Contratos
inconsistentes geram `ComparisonPresentationContractError`.

## Estados

Estados suportados:

- `SUCCESS`;
- `PARTIAL`;
- `EMPTY`;
- `NOT_APPLICABLE`;
- `CLARIFICATION_REQUIRED`;
- `OUT_OF_SCOPE`;
- `UNSUPPORTED`;
- `TIMEOUT`;
- `BLOCKED`;
- `ERROR`.

Timeout e bloqueio nunca sao apresentados como "sem dados". Resultado parcial
e truncado recebem aviso antes das visualizacoes. Falhas permanecem visiveis.

`NULL`, `MISSING`, `ZERO` e `NOT_APPLICABLE` sao estados de valor diferentes:

- `NULL`: "Sem valor";
- `MISSING`: "Sem registro";
- `ZERO`: zero formatado na unidade;
- `NOT_APPLICABLE`: "Nao aplicavel".

Percentual com denominador zero permanece nulo e exibe o motivo informado pelo
executor. Meta ausente nunca se torna meta zero.

## Defaults E Visualizacoes

Visualizacoes explicitamente solicitadas pelo contrato sao preservadas na
ordem recebida. Sem pedido explicito, defaults deterministicos usam o tipo da
comparacao e a compatibilidade das unidades.

Componentes suportados:

- KPI/cards para operandos e calculos;
- tabela comparativa com busca visual, paginacao e scroll horizontal;
- barras para categorias e entidades;
- linha e area para series temporais;
- pizza apenas para participacao explicita e unidade compativel;
- pequenos multiplos quando unidades nao podem compartilhar eixo;
- realizado versus meta sem gauge ou atingimento calculado no navegador.

Comparacoes compostas e unidades incompativeis usam fallback seguro para tabela
ou pequenos multiplos. O frontend nao reduz silenciosamente linhas, operandos
ou visualizacoes. Volume grande usa paginacao, data zoom e limite visual
explicito, mantendo o dataset bruto exportavel.

## Formatos

`comparisonFormatters.ts` centraliza:

- moeda pt-BR;
- percentual;
- inteiros e decimais;
- datas e timestamps;
- valores `Decimal` serializados como string;
- labels de calculo e direcao.

Strings decimais sao preservadas. Conversao numerica ocorre somente para
coordenadas do ECharts, nunca para refazer calculos financeiros.

## Acessibilidade E Responsividade

- controles possuem nomes acessiveis e suporte de teclado;
- graficos incluem descricao textual e `role="img"`;
- tabelas possuem caption e cabecalhos semanticos;
- direcao usa texto e icone, nao apenas cor;
- fullscreen fecha com `Escape` e devolve foco;
- labels longos quebram ou usam barras horizontais;
- layouts cobrem desktop, tablet, mobile e ultrawide;
- tema claro e escuro preservam o mesmo resultado.

## Validacao, Proveniencia E RBAC

Validacao e proveniencia sao reunidas no Trust Center da comparacao:

- `CONSULTA`: resultado de negocio, sem proveniencia ou diagnostico tecnico;
- `GESTOR`: proveniencia resumida permitida;
- `ADMIN`: checks e metadados tecnicos sanitizados.

SQL, binds, credenciais, connection strings, pergunta integral e linhas
restritas nao sao exibidos nem exportados.

## Exportacao

CSV inclui IDs, labels, periodos, status e valores brutos recebidos. Valores
formatados nunca substituem os valores de auditoria. Datasets classificados
como `RESTRICTED` nao sao exportaveis.

## Feature Flags E Telemetria

Flags:

- `NEXT_PUBLIC_COMPARISON_RENDERER_V2_ENABLED`;
- `NEXT_PUBLIC_COMPARISON_RENDERER_V2_SHADOW_MODE`.

Ambas ficam desligadas por padrao. Em ambiente nao produtivo, os testes podem
usar overrides locais. Shadow mode adapta o contrato e emite somente estrutura,
sem substituir o renderer legado.

A telemetria registra versao, tipo, status, contagens, parcialidade,
truncamento, duracao, renderer, fallback, role, erro tipado e fingerprint
estrutural. Nao registra perguntas, valores, SQL ou dados empresariais.

## Compatibilidade

- V2 com sidecar: usa o contrato `lumina.analytics/2.0`;
- V1 com sidecar: prefere o sidecar governado;
- V1 sem sidecar: cria apresentacao minima apenas com campos recebidos;
- flag desligada: mantem o runtime legado.

## Limites E Proxima Etapa

Esta camada nao implementa Dashboard Blueprint V2, memoria conversacional,
consulta de banco, Oracle, OpenAI ou regras financeiras. A proxima etapa e
`Prompt 08 - Estado conversacional escalavel no PostgreSQL`.
