# Frontend

## Sessao Conversacional

`useLuminaQuery` persiste somente public session ID, context version e parent
da resposta numa chave local escopada a tenant e usuario. Cada submissao gera
UUID idempotente, retries reutilizam o mesmo request body e logout remove os
vinculos. O backend permanece autoridade.

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
- `analyticalContractAdapter`: aceita o payload V1 e valida o sidecar opcional
  `lumina.analytics/2.0` sem inventar dados ou alterar o renderer.
- `components/comparison`: adapta resultados do executor para
  `lumina.comparison-presentation/1.0`, sem recalcular numeros, e integra tabela,
  cards, ECharts, Trust Center, CSV, RBAC, feature flag e shadow mode.
- `getApiBase`: preserva `localhost` ou `127.0.0.1` conforme o host aberto no navegador, evitando perda de cookie de sessao local.

## Charts E Componentes

Implementados componentes de KPI, barras, linhas, area, pizza, heatmap, scatter, treemap, funil, tabelas e ranking.

## Responsividade

A responsividade e coberta por CSS/Tailwind, engines de grid e testes Playwright
para desktop, tablet, mobile e ultrawide. O renderer comparativo tambem valida
fullscreen, teclado, labels longos e ausencia de overflow horizontal.

## Limitacoes

- Testes visuais cobrem integridade de layout, nao validam todos os cenarios reais de dados.
- SSE pode ser desabilitado no modo inline de chat.
- O frontend nao corrige regra de negocio; reparos de texto/encoding sao apenas apresentacionais.
- A apresentacao comparativa V2 existe, mas permanece desligada por padrao ate
  rollout controlado. A superficie V1 continua como fallback.
- O Dashboard Blueprint V2 permanece fora desta camada. O estado
  conversacional PostgreSQL integra o hook por metadados de sessao, parent e
  versao; o frontend nao armazena historico como autoridade.
