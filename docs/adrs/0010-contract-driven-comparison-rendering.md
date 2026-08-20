# ADR 0010 - Renderizacao Comparativa Orientada Por Contratos

- Status: aceito
- Data: 2026-07-28

## Contexto

O executor `lumina.comparison-executor/1.0` produz operandos, alinhamento,
calculos, validacao e proveniencia deterministicos. O renderer legado nao
possuia uma fronteira especializada capaz de preservar multiplos operandos,
estados de valor e varias visualizacoes sem risco de recalculo no navegador.

## Decisao

Adotar a camada local `lumina.comparison-presentation/1.0`:

```text
AnalyticalResponseV2
  -> ComparisonPresentationAdapter
  -> ComparisonPresentationModel
  -> DynamicRenderer
  -> ComparisonRenderer
```

O modelo de apresentacao nao substitui o contrato publico. Ele organiza o
payload recebido para UI, preserva strings decimais e explicita estados.
Apache ECharts continua como engine grafica. O runtime legado permanece como
fallback governado por feature flags.

O frontend pode formatar valores e converter pontos exclusivamente para
coordenadas visuais. Ele nao pode recalcular diferenca, percentual, direcao,
participacao, ranking, atingimento ou baseline.

Validacao e proveniencia ficam no Trust Center e respeitam `ADMIN`, `GESTOR` e
`CONSULTA`. Telemetria e shadow mode sao exclusivamente estruturais.

## Consequencias

Beneficios:

- operandos e visualizacoes mantem ordem e cardinalidade;
- null, missing, zero e nao aplicavel permanecem distintos;
- resultados parciais, truncados, bloqueados e timeout ficam explicitos;
- V1 e V2 coexistem durante rollout;
- testes podem validar apresentacao sem banco, Oracle ou OpenAI.

Custos:

- existe um modelo local adicional, versionado e documentado;
- os dois renderers coexistem enquanto a flag estiver desligada;
- coordenadas ECharts exigem conversao numerica controlada.

## Alternativas Rejeitadas

- recalcular no frontend: quebra a autoridade numerica do executor;
- substituir o contrato V2: amplia acoplamento e quebra compatibilidade;
- adicionar outra biblioteca grafica: aumenta bundle e divergencia visual;
- ativar diretamente em producao: remove a possibilidade de shadow e rollback.

## Rollback

Desligar `NEXT_PUBLIC_COMPARISON_RENDERER_V2_ENABLED`. O runtime legado continua
inalterado. Shadow mode pode permanecer ativo para comparar apenas estrutura.
