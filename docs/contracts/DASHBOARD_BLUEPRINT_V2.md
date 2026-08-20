# Dashboard Blueprint V2

## Estado e autoridade

`lumina.dashboard-blueprint/2.0` é o contrato declarativo canônico para uma
futura geração, revisão, publicação e apresentação governada de dashboards.
Nesta etapa ele é exclusivamente `CONTRACT_ONLY`: não possui API, persistência,
migration, renderer, editor, rota frontend ou integração com IA.

O contrato descreve a intenção de apresentação. Ele não concede permissões,
não escolhe tenant ou usuário, não executa consultas e não é fonte de valores.
Métricas, dimensões e entidades são referências canônicas; fórmulas, SQL,
identificadores físicos, datasets e credenciais são proibidos.

## Raiz canônica

`DashboardBlueprintV2` contém versão, revisões visual e semântica, identidade,
propósito, lifecycle, origem, audiência, classificação, requisitos de
capacidade, layout, widgets, bindings, filtros, interações, acessibilidade,
intenção de refresh e compatibilidade. O estado é fixo em `CONTRACT_ONLY` e o
`checksum` recebido deve ser nulo.

Todos os modelos públicos usam Pydantic 2 com `strict=True`, `extra=forbid`,
imutabilidade e validação de defaults. Payloads JSON são lidos pela fronteira
JSON estrita, sem coerção implícita de tipos Python. Unions de widgets, filtros,
períodos e interações são fechadas e discriminadas.

## Lifecycle, origem e governança

Lifecycle fechado: `DRAFT`, `IN_REVIEW`, `APPROVED`, `PUBLISHED`,
`SUPERSEDED`, `DEPRECATED`, `ARCHIVED` e `REJECTED`.

Origem fechada: humana, template, legado migrado, proposta por IA, assistida
por IA ou gerada pelo sistema. Origem de IA nunca transforma a IA em autoridade
numérica nem autoriza publicação automática.

Classificações `SECRET` e `FORBIDDEN` são recusadas. Uma classificação do
dashboard nunca reduz a de um binding. `permissions` representa somente
requisitos; autorização futura continuará no backend autenticado. O execution
context server-controlled é separado e não pode ser embutido no blueprint.

## Layout responsivo

| Breakpoint | Largura mínima | Colunas |
|---|---:|---:|
| `MOBILE` | 0 | 4 |
| `TABLET` | 768 | 8 |
| `DESKTOP` | 1280 | 12 |
| `ULTRAWIDE` | 1920 | 16 |

Posições e tamanhos são inteiros limitados. Overlap, IDs duplicados, widgets
ausentes e divergência entre ordem visual e acessível falham de forma fechada.
Todo widget visível deve estar posicionado em todos os breakpoints.

## Widgets e registry

O registry estático contém 16 tipos: KPI, KPI comparativo, line, bar, stacked
bar, area, pie e donut charts, table, ranking, status summary, progress, filter
panel, text block, divider e provenance summary. Não existem plugins dinâmicos,
imports por nome, componentes arbitrários, HTML, JavaScript ou CSS livre.

Widgets analíticos exigem `binding_id`, shape compatível e provenance pública.
Tabela exige indicador de truncamento. Charts limitam séries e cardinalidade.
Texto é simples e limitado; não é markup executável.

## Bindings, filtros e interações

Bindings referenciam IDs canônicos de métricas, dimensões e entidades. Períodos
são uma union discriminada entre `FIXED`, `RELATIVE`, `INHERITED` e `FILTER`.
Comparações preservam current e baseline. Shapes fechados incluem scalar,
comparison, time series, grouped series, table, fact set, ranking e status
summary. O blueprint não redefine fórmula ou agregação da métrica.

Há nove filtros tipados, com scope, default e grupos explícitos. Defaults são
preferências declarativas, nunca autoridade sobre contexto autenticado.
Interações incluem cross-filter, drilldown, reset, provenance, navegação
interna, expansão, sort e paginação. Referências inexistentes, self-target e
ciclos são proibidos. Navegação externa não existe no contrato.

## Apresentação, estados e proveniência

Formatação de número, moeda, percentual e data é descritiva e não recalcula
valores. Temas são tokens fechados. Estados de loading, empty e error têm
mensagens e ações tipadas. Acessibilidade mínima exige descrição e fallback
textuais, status independente de cor e reading order determinística.

Cada binding analítico exige resumo público de proveniência. Dados sensíveis,
SQL, binds e payload bruto não entram nesse resumo. Refresh, cache e
materialização são preferências; a policy efetiva cabe ao backend futuro.

## Patches e versionamento

`DashboardVisualPatchV2` altera somente título/descrição visual, layout e campos
visuais allowlisted. Não altera binding, métrica, dimensão, filtro,
classificação, permissão ou provenance.

`DashboardSemanticPatchV2` usa allowlist separada, exige avanço de
`semantic_revision` e `requires_revalidation=true`. Patches são propostas
imutáveis; nenhum aplicador ou persistence layer foi criado nesta etapa.

## Canonicalização e checksums

O canonicalizer puro aplica NFC, normaliza whitespace, ordena chaves de mapas e
preserva ordem de listas. O JSON canônico usa UTF-8 e separadores estáveis.
SHA-256 é calculado para blueprint, semantic, visual, layout, widgets, bindings,
filtros, interações e acessibilidade. O processo é determinístico e idempotente;
ele nunca repara payload inválido.

## Pipeline de validação e limites

O pipeline fail-closed percorre contrato, identidade, versão, lifecycle,
segurança, classificação, permissões, layout, widgets, bindings, filtros,
interações, formatação, acessibilidade, provenance, compatibilidade e, somente
quando válido, canonicalização. Status: `VALID`, `VALID_WITH_WARNINGS`,
`INVALID`, `BLOCKED` e `UNSUPPORTED_VERSION`.

Antes do parse são bloqueados conteúdo executável, HTML/JS/CSS, SQL, DSNs,
paths, templates, Python/shell, URLs externas, caracteres de controle, excesso
de 1 MB e profundidade superior a 20. O contrato limita 64 widgets/bindings,
32 filtros, 16 grupos, 128 interações e 64 operações por patch.

## Compatibilidade, legado e artefatos

Compatibilidade é `[2.0, 3.0)`, com feature registry estático. Versão
desconhecida não recebe fallback. O adapter legado é puro, limitado e gera
somente proposta sintética com warnings; não modifica nem persiste a origem.
`backend/services/blueprints.json`, modelos e schemas legados permanecem ativos
e inalterados até rollout aprovado.

Schemas oficiais estão em `docs/contracts/dashboard_blueprint_v2/schemas/` e
20 goldens em `docs/contracts/dashboard_blueprint_v2/goldens/`. O exportador
gera ambos duas vezes, compara hashes e certifica que a OpenAPI padrão não
possui paths do Prompt 19.

