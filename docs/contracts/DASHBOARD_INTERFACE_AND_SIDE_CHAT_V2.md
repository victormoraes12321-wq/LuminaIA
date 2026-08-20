# Interface Governada de Dashboards e Side Chat V2

- Versão: `lumina.dashboard-ui-sidechat/1.0`
- Estado: implementado, desativado por padrão
- Dependências: `lumina.dashboard-blueprint/2.0` e `lumina.dashboard-backend/1.0`
- Autoridade operacional padrão: runtime legado

## Fronteiras

O frontend apresenta contratos, mantém estado efêmero, captura intenção e envia
ações tipadas. Ele não calcula métrica, comparação, percentual, ranking ou
“Outros”; não converte null em zero; não decide tenant, role, permission,
ownership, lifecycle ou publicação. Blueprint V2 define estrutura. Dashboard
Backend V2 decide acesso, CAS, revisão, publicação e runtime. Safe Analytical
PostgreSQL e Validation & Provenance continuam autoridades dos fatos.

## Modos e rotas

`DASHBOARD_UI_MODE` é server-side e tem default `LEGACY_ONLY`.
`NEXT_PUBLIC_DASHBOARD_UI_MODE` controla apenas ergonomia da Sidebar e nunca
concede acesso. Os modos são `LEGACY_ONLY`, `V2_PREVIEW`, `V2_READ`,
`V2_AUTHORING` e `V2_SIDE_CHAT`.

As páginas são `/dashboard/v2`, `/dashboard/v2/[dashboardId]`,
`/dashboard/v2/[dashboardId]/edit` e
`/dashboard/v2/[dashboardId]/history`. O layout server component responde 404
em `LEGACY_ONLY`; edit/history também falham fechado fora de authoring. Proxy,
sessão HttpOnly e capabilities retornadas pelo backend completam a defesa. Um
403 e um recurso cross-tenant são apresentados como “não encontrado ou não
disponível”, sem enumeração.

## Biblioteca, shell e runtime

A biblioteca busca metadados permitidos do Prompt 20, pesquisa localmente esses
metadados e filtra lifecycle. Nada autoritativo vai para localStorage. Criação
manual usa clone de fonte governada, cria DRAFT e não chama IA.

O shell suporta loading, ready, partial, stale, blocked, unavailable, archived,
unpublished e permission denied. Filtros separam default, draft, submitted,
effective e runtime-confirmed. Cada request é cancelável; gerações antigas não
sobrescrevem estado atual. Logout desmonta a árvore; mudança de tenant remonta o
side chat e aborta requests.

O grid usa placements do Blueprint para MOBILE, TABLET, DESKTOP e ULTRAWIDE,
preserva reading order e usa fallback explícito para widget sem placement.
Resize de viewport não muta o blueprint.

## Registry e renderer

O registry estático contém KPI, COMPARISON_KPI, LINE_CHART, BAR_CHART,
STACKED_BAR_CHART, AREA_CHART, PIE_CHART, DONUT_CHART, TABLE, RANKING,
STATUS_SUMMARY, PROGRESS, FILTER_PANEL, TEXT_BLOCK, DIVIDER e
PROVENANCE_SUMMARY. Não há `eval`, import dinâmico, component path vindo do
payload ou registry mutável.

O renderer valida widget, result shape e status. Tipo desconhecido ou shape
incompatível falha fechado no próprio card. Charts reutilizam Recharts,
respeitam ordering e limites do contrato e sempre oferecem tabela textual.
Valores, delta, percentual, rank, ties, status, freshness, partial e truncation
são exibidos exatamente como recebidos.

## Editor, CAS e lifecycle

O editor separa VISUAL e SEMANTIC. Preview é cópia efêmera, dirty, descartável,
com undo local. Patches visuais aceitam somente a allowlist do Prompt 19;
patches semânticos exigem revalidação e voltam a DRAFT. Controles numéricos
permitem mover/redimensionar com teclado sem dependência nova.

Toda mutação usa idempotency key opaca, lock versions/checksums e Prompt 20.
409 nunca executa last-write-wins: exibe base, exige reload/compare/reaplicação.
Review, approval, publication e rollback têm confirmação humana; rollback cria
nova publication. Collaborator role não eleva RBAC global.

## Side chat

O side chat usa `POST /api/v1/query/`, não uma segunda plataforma. O request
opcional `dashboard_context` é um schema fechado contendo apenas IDs canônicos,
checksums, filtros permitidos, referências públicas e versão conversacional.
Não aceita blueprint completo, rows, SQL, binds, DSN, credentials, permission
grants, prompt interno ou chain of thought.

Modos: ASK, EXPLAIN_WIDGET, EXPLAIN_VARIANCE, FILTER, NAVIGATE e VISUAL_EDIT.
Ações fechadas: NO_ACTION, FOCUS_WIDGET, OPEN_PROVENANCE, APPLY_FILTER,
RESET_FILTERS, DRILLDOWN, VISUAL_PATCH_PROPOSAL, VISUAL_PATCH_APPLY e BLOCKED.
Texto livre nunca é executado. HTML, JavaScript, URL arbitrária, semantic edit,
approve, publish, rollback e collaborator management são bloqueados.

O interceptor puro retorna UI_MODIFIED somente depois de dashboard/revision,
capability, paths visuais, confirmação backend, nova revisão e checksum
semântico preservado. Mudança semântica/publication/major contract pode retornar
FULL_RENDERING_REQUIRED; isso não é fallback genérico. Cancelamento retorna
nenhuma ação e resposta obsoleta é descartada.

O transporte reaproveita o corpo incremental da request de query e mantém a
máquina de estados `CONNECTING`, `RECEIVING`, `COMPLETE`, `CANCELLED`,
`FAILED`, `RETRYABLE`, `ACTION_PENDING` e `ACTION_CONFIRMED`. Chunks apenas
marcam recebimento: texto e ação só entram no estado React depois que o envelope
JSON completo foi recebido e validado. Cancelamento, resposta stale, troca de
tenant, logout e reset de sessão invalidam a generation atual; reset também
gera novo session ID e limpa mensagens, contexto visual e proposta pendente.

Troca persistente de chart type permanece semântica em Blueprint V2 porque
`widget_type` participa do checksum semântico e não está na visual allowlist.
Assim, o side chat a bloqueia/encaminha ao editor semântico; alterar essa regra
exigiria nova versão do contrato do Prompt 19, não um bypass no Prompt 21.

## Segurança, acessibilidade e telemetria

Proveniência mostra somente publication, revision, widget/binding, definições
públicas, período, filtros, freshness, completeness, truncation, validação,
certificação, cache/materialization e warnings. Drawers são dialogs; widgets têm
foco, nomes e fallbacks; reduced motion e light/dark seguem o sistema existente.

Telemetria é estrutural por CustomEvent: abertura/fechamento, widget status,
UI_MODIFIED, bloqueio, cancelamento e conflito. Não registra pergunta, resposta,
valor, dataset, filtro sensível, SQL ou tenant literal.

## Rollout

Produção continua `LEGACY_ONLY`, sem link, página acessível ou request V2. A
progressão exige flags backend compatíveis, allowlist por tenant, migration v22,
backup/restore, SLO, leakage zero e aprovação operacional. Não existe migration
v23, dependência nova, lockfile alterado ou implementação do Prompt 22.
