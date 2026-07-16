# Frontend

## Responsabilidade

Renderizar respostas, dashboards, filtros, tabelas, graficos, Trust Center e Dashboard Studio. O frontend nao deve calcular KPIs de negocio nem consultar banco diretamente.

## Fluxo Principal

```text
Usuario -> ChatInterface -> useLuminaQuery -> /api/v1/query/
-> AssistantResponseBlock -> InlineDashboardRuntime/DynamicRenderer
-> DashboardRuntimeEngine -> GridEngine/RuntimeRenderer -> Usuario
```

## Componentes Principais

- `ChatInterface`: entrada da pergunta e modo operacional/analitico/executivo.
- `AssistantResponseBlock`: apresentacao da resposta da IA e visualizacoes.
- `InlineDashboardRuntime`: adapta `QueryResponse` para runtime quando necessario.
- `DashboardRuntimeEngine`: orquestrador do runtime visual.
- `GridEngine`: grid responsivo.
- `RuntimeRenderer`: decide qual componente renderizar por widget.
- `TrustCenterPanel`: confianca, lineage, versoes, sync, performance, cache, health, audit e diagnosticos.
- `Sidebar`: navegacao e consultas sugeridas.
- `Dashboard Studio`: pagina `/dashboard/studio` para templates/instances visuais.

## Charts E Componentes

Implementados componentes de KPI, barras, linhas, area, pizza, heatmap, scatter, treemap, funil, tabelas e ranking.

## Responsividade

A responsividade e coberta por CSS/Tailwind, engines de grid e testes Playwright para desktop, tablet e ultrawide.

## Limitacoes

- Testes visuais cobrem integridade de layout, nao validam todos os cenarios reais de dados.
- SSE pode ser desabilitado no modo inline de chat.
