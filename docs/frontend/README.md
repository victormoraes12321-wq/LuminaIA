# Frontend

## Semantic Retrieval V2

Clarifications semanticas usam `ClarificationPanel` e enviam o token assinado
antes de continuar a conversa. A area
`/dashboard/admin/semantic` oferece versions, build, publication, rollback,
inspector e audit apenas para `ADMIN` e sob feature flag.

`CONSULTA` recebe labels e provenance publica, sem vetor ou score interno. A
flag `NEXT_PUBLIC_SEMANTIC_RETRIEVAL_ENABLED` inicia `false`.

## Sessao Conversacional

`useLuminaQuery` persiste somente public session ID, context version e parent
da resposta numa chave local escopada a tenant e usuario. Cada submissao gera
UUID idempotente, retries reutilizam o mesmo request body e logout remove os
vinculos. O backend permanece autoridade.

`AssistantResponseBlock` mostra um resumo compacto do contexto herdado,
periodo alterado, dimensoes e filtros mantidos. Metadados tecnicos do
resolvedor ficam restritos ao diagnostico `ADMIN`; `CONSULTA` nao recebe IDs
internos nem um editor de memoria.

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

## Glossário E Governança

`/dashboard/knowledge` fornece glossário published-only para `CONSULTA`.
ADMIN/GESTOR também acessam assets e histórico; ações são renderizadas por
papel e sempre revalidadas pelo backend. ADMIN recebe publicação, depreciação,
rollback e audit timeline.

A entrada de navegação só aparece com
`NEXT_PUBLIC_ENTERPRISE_KNOWLEDGE_ENABLED=true`. O default é desligado.
Playwright cobre CONSULTA/ADMIN em desktop, tablet, mobile e ultrawide com API
simulada.

## Meu Perfil Analitico

`/dashboard/settings/profile` permite ao usuario autenticado gerir somente o
proprio perfil: localidade, apresentacao, acessibilidade, consentimento,
disable/reactivate, exportacao e pedido de exclusao. A navegacao depende de
`NEXT_PUBLIC_USER_ANALYTICAL_PROFILE_ENABLED=true`; o backend continua sendo a
autoridade de rollout e autorizacao.

`AssistantResponseBlock` mostra `applied_preference_summary` sem IDs internos,
SQL ou dados empresariais. O usuario pode pedir a remocao das preferencias no
turno seguinte ou abrir a pagina de configuracao. O frontend nao calcula nem
aplica defaults por conta propria.

## Feedback De Respostas

`FeedbackControls` aparece somente quando a flag publica esta ativa e a
resposta possui `response_node_id`, sessao e checksum persistidos. O navegador
envia referencias, categoria, correcao e explicacao; nao reenvia dataset nem
resposta inteira.

`/dashboard/feedback` lista feedback proprio. A fila
`/dashboard/admin/feedback` e visivel apenas para ADMIN/GESTOR e volta a ser
validada pelo backend. Flags:

- `NEXT_PUBLIC_SUPERVISED_FEEDBACK_ENABLED`;
- `NEXT_PUBLIC_SUPERVISED_FEEDBACK_ADMIN_ENABLED`.
