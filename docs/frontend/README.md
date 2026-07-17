# Frontend

## Responsabilidade

Renderizar respostas, dashboards, filtros, tabelas, graficos, Trust Center e Dashboard Studio. O frontend nao deve calcular KPIs de negocio nem consultar banco diretamente.

## Fluxo Principal

```text
Usuario -> ChatInterface -> useLuminaQuery -> /api/v1/query/
-> AssistantResponseBlock -> InlineDashboardRuntime/DynamicRenderer
-> DashboardRuntimeEngine -> GridEngine/RuntimeRenderer -> Usuario
```

`useLuminaQuery` envia `session_id`, historico recente e `parent_id` para preservar continuidade da conversa. O hook tambem expoe `resetConversation`, usado pela logo do sistema para limpar a tela de perguntas.

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
- `textEncoding`: reparo defensivo de textos com acentos/caracteres especiais antes da renderizacao.
- `getApiBase`: preserva `localhost` ou `127.0.0.1` conforme o host aberto no navegador, evitando perda de cookie de sessao local.

## Charts E Componentes

Implementados componentes de KPI, barras, linhas, area, pizza, heatmap, scatter, treemap, funil, tabelas e ranking.

## Responsividade

A responsividade e coberta por CSS/Tailwind, engines de grid e testes Playwright para desktop, tablet e ultrawide.

## Limitacoes

- Testes visuais cobrem integridade de layout, nao validam todos os cenarios reais de dados.
- SSE pode ser desabilitado no modo inline de chat.
- O frontend nao corrige regra de negocio; reparos de texto/encoding sao apenas apresentacionais.
