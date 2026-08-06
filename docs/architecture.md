# Arquitetura Do LuminaAI

## Smart Cache e materializações governadas

`lumina.smart-cache-materialization/1.0` fica depois do Safe Analytical
PostgreSQL e de Validation & Provenance. O cache só decide eligibility, constrói
keys server-controlled, lê/escreve resultados certificados e administra
invalidation, generations e leases; não calcula, certifica nem executa SQL.

Materializações usam definitions versionadas, builds governados e snapshots
imutáveis. Build produz `READY`, publicação explícita troca o ponteiro ativo por
CAS, refresh preserva o ativo e rollback mantém histórico. A migration V21 é
explícita e tenant-scoped. O bootstrap condicional garante zero models, services,
rotas, tabelas ou tasks Prompt 18 em `LEGACY_ONLY`.

## Estado Conversacional

O subsistema escalavel usa `lumina.conversation-state/1.0`: PostgreSQL armazena
sessoes por tenant/usuario, nos e eventos append-only e snapshots
materializados. Nenhum lock permanece aberto durante execucao analitica.
`LEGACY_ONLY` continua como default de producao ate migration v12 e rollout
controlado. Consulte ADR 0011 e `docs/contracts/CONVERSATION_STATE_V2.md`.

O motor `lumina.context-resolution/1.0` fica entre a intencao V2 do turno e o
planner. Ele recebe o snapshot PostgreSQL da branch, aplica precedencia e
policies por campo e devolve intent consolidado mais patch tipado. Nao acessa
dados, SQL, Oracle ou OpenAI. A persistencia ocorre apenas na conclusao
transacional do turno. Consulte ADR 0012.

## Visao Geral

O LuminaAI e uma plataforma de BI corporativo orientada por IA. A IA interpreta a intencao, estrutura estrategia analitica/visual e gera blueprints. O backend executa regras, consultas, calculos e persistencia. O frontend renderiza dashboards e interacoes sem calcular regra de negocio.

## Objetivos

- Transformar perguntas em analises estruturadas.
- Reutilizar blueprints e pacotes analiticos sem reutilizar dados de resposta.
- Preservar separacao entre inteligencia analitica, execucao e apresentacao.
- Oferecer dashboard runtime, studio visual e centros de confianca/performance/seguranca.

## Principios Arquiteturais

- Responsabilidade unica por camada.
- IA nao consulta banco e nao calcula metricas finais.
- Backend centraliza execucao, calculos e validacoes.
- Frontend renderiza e interage com payloads prontos.
- Blueprints sao reutilizaveis; dados devem ser consultados novamente conforme politicas de cache.
- Multi-tenant deve ser aplicado por usuario autenticado e `tenant_id`.

## Arquitetura Enterprise Oficial

```text
IA
-> Planner
-> Validator
-> Business Layer
-> Enterprise Knowledge Layer
-> Backend
-> Data Engine
-> Frontend
-> Insight Layer
-> Cache Layer
-> Security Layer
```

## Arquitetura Modular Implementada

```text
backend/
  main.py                    # FastAPI, routers, middlewares, lifespan
  routers/                   # Controllers HTTP
  schemas/                   # DTOs Pydantic
  models/                    # Modelos SQLAlchemy
  services/
    ai/                      # Corporate Intelligence Engine modular
    business/                # Business Knowledge Engine
    data_platform/           # Catalogos, blueprints, packages, runtime e sync
    performance/             # Performance Optimization Platform
    security/                # Enterprise Security Platform
frontend/
  app/                       # Rotas Next.js
  components/                # UI, charts, runtime e studio
  hooks/                     # Hooks de API/runtime/performance/SSE
  engines/                   # Grid, responsividade, layout e performance client-side
  types/                     # Contratos TS
scripts/                     # Backup, load smoke, import cycle check e seeds
docs/                        # Documentacao oficial e auditorias
```

## Fluxo Geral

```text
Usuario -> Frontend -> API Query -> Query Intelligence Engine -> IA/CIE
-> Planner -> Validator -> Business/Data Platform -> Data Engine
-> Transformacao/BI/Runtime Payload -> Frontend -> Dashboard -> Usuario
```

## Fluxo Deterministico Para Perguntas Criticas

O `NewQueryOrchestrator` possui um caminho deterministico para perguntas operacionais criticas quando ha periodo explicito ou periodo herdado da conversa. Esse caminho evita respostas ambiguas para os indicadores mais sensiveis de vendas:

- Faturamento do mes e do mes anterior.
- Ticket medio.
- Total de desconto e desconto medio.
- Venda por vendedor e maior vendedor.
- Ranking/top clientes com exclusao da loja interna quando aplicavel.

Regras relevantes:

- Vendedor tecnico `PADRAO` nao participa do ranking de vendedores.
- Cliente/loja interna `LAGES E LOPES LTDA` nao participa de top/ranking de clientes externos.
- Desconto e derivado de forma deterministica por item sobre a view de vendas.
- Continuidade de conversa pode herdar periodo por `session_id`, historico recente e `parent_id`.

## Fluxo De Dados

1. Usuario envia pergunta pelo chat.
2. Frontend chama `/api/v1/query/` com JWT/cookie, `session_id`, historico recente e `parent_id` quando ha grafo de conversa.
3. Backend valida sessao, tenant, escopo e senha obrigatoria.
4. Para perguntas criticas com periodo claro, o orquestrador pode executar o caminho deterministico.
5. Para perguntas abertas, IA identifica intencao e/ou CIE estrutura Business Intent, visual strategy e blueprint.
6. Planner e Validator normalizam plano, filtros, datas, metricas e view alvo.
7. Backend executa dados via clone PostgreSQL/mock/Oracle conforme configuracao.
8. Data Transformer humaniza labels e monta dados de grafico, KPIs e inteligencia BI.
9. Data Platform pode gerar blueprint, runtime payload, trust center e telemetria.
10. Frontend repara textos potencialmente corrompidos, adapta payloads legados e renderiza resposta/dashboard runtime.

## Fluxo Do Scheduler E Sync

O scheduler inicia no lifespan do FastAPI e chama tarefas de sincronizacao. O Sync Engine possui travas por tenant para evitar concorrencia indevida. A sincronizacao trabalha com catalogo, views e clone analitico conforme servicos `sync_service`, `sync_engine` e `sync_scheduler`.

## Fluxo Do Blueprint Repository

1. Query Intelligence Engine tenta localizar blueprint compativel.
2. Intent fingerprint e similaridade orientam reuso/evolucao.
3. Quando necessario, um novo blueprint e criado e persistido.
4. Data Platform pode registrar blueprint no repositorio e vincular analytical packages/dashboard runtime.

## Fluxo Do Metadata Catalog

1. View Manager/Catalog API registra ou atualiza metadados.
2. Metadata Catalog armazena entidades, colunas, qualidade, lineage e versoes.
3. Health Monitor calcula scores e alertas.
4. Endpoints `/api/v1/metadata-catalog/*` expoem resumo, busca, lineage, impacto e versoes.

## Limites E Observacoes

- Ha rotas duplicadas `/api/v1/api/v1/query` por compatibilidade, mantidas intencionalmente.
- Em ambiente local, o frontend preserva o mesmo host loopback usado no navegador (`localhost` ou `127.0.0.1`) ao montar a base da API, evitando perda de cookie de sessao.
- Docker compose nao foi validado localmente por ausencia do binario Docker.
- RLS nativo em banco nao foi identificado; isolamento ocorre na camada de aplicacao.

## Enterprise Knowledge V2

`enterprise_knowledge_assets` mantém identidade e ownership; versões,
aprovações, publicações, aliases, relações, eventos e imports vivem em tabelas
separadas pela migration v13. FKs compostas comprovam o tenant na camada de
banco.

O runtime lê apenas a versão publicada atual e vigente. O adaptador entrega
IDs canônicos, labels, domínio e provenance aos consumidores sem expor tabela,
coluna, SQL ou fórmula executável. `MetricRegistry` e executores
determinísticos continuam autoridades numérica e de consulta. ADR:
[`0013`](adrs/0013-published-versioned-enterprise-knowledge.md).

## Perfil Analitico Governado

```text
Pergunta + sessao autenticada
-> TemporalNormalizer
-> ContextResolution
-> UserPreferenceApplicationEngine
-> Planner
-> Executor deterministico
-> Presentation + resumo publico
```

O perfil e uma camada de defaults pessoais, nao uma autoridade semantica ou
numerica. O repository aplica escopo composto de tenant e usuario; o motor
puro recebe contratos ja carregados, nao consulta banco e nao persiste. O
planner e o executor nao conhecem o repository do perfil.

Knowledge Base e `MetricRegistry` validam identificadores de referencia sem
ceder ownership. `ConversationState` continua autoridade de continuidade;
`SemanticMemory` e `SearchHistory` nao promovem preferencias. ADR:
[`0014`](adrs/0014-explicit-governed-user-analytical-profile.md).

## Feedback Governado E Dataset Supervisionado

```text
Resposta persistida
-> ownership + checksum
-> redacao deterministica
-> triagem deterministica
-> revisao humana
-> decisao final
-> candidato explicito
-> curadoria
-> snapshot versionado
-> exportacao offline
```

`backend/services/supervised_feedback/` e a autoridade do fluxo
`lumina.supervised-feedback/1.0`. Ela referencia o Conversation State, mas nao
o altera. Knowledge Base, perfil, planner, executor e MetricRegistry nao sao
mutados por feedback. Snapshot publicado e imutavel e nao e consumido
automaticamente por IA. ADR:
[`0015`](adrs/0015-reviewed-human-feedback-before-training-datasets.md).

## Semantic Retrieval E Entity Resolution

```text
QueryIntentV2 + contexto resolvido + perfil consentido
-> mention extraction
-> indice PostgreSQL PUBLISHED do tenant
-> permission/type/domain filter
-> retrieval lexical + feature hash local opcional
-> ranking + threshold + ambiguity
-> canonical patch ou clarification
-> planner
-> executor deterministico
```

`backend/services/semantic_retrieval/` e a autoridade de recuperacao
`lumina.semantic-retrieval/1.0`. Enterprise Knowledge e `MetricRegistry`
fornecem referencias publicadas, mas nao sao alterados pelo indice. O planner
recebe IDs canonicos e o executor nao conhece o repository semantico.

Definitions, versions, documents, aliases, terms, representations,
publications, events, evaluations e clarifications vivem no PostgreSQL pela
migration v16. Publicacao e rollback usam CAS; o trigger protege snapshots
publicados. O provider inicial e feature hash deterministico sem rede.

Producao continua `LEGACY_ONLY`. ADR:
[`0016`](adrs/0016-governed-hybrid-semantic-retrieval.md).

## Dashboard Blueprint V2

```text
referências analíticas canônicas
-> blueprint declarativo estrito
-> validação fail-closed
-> canonicalização UTF-8/NFC
-> checksums semântico e visual independentes
-> artefato CONTRACT_ONLY
```

`backend/contracts/dashboard_blueprint_v2/` define
`lumina.dashboard-blueprint/2.0`; `backend/services/dashboard_blueprint_v2/`
contém somente validação, canonicalização, registries, fixtures e adapter puro.
O contrato não é integrado ao runtime, banco ou frontend nesta fase. O legado,
incluindo `services/blueprints.json`, continua operacional. Persistência,
renderer e geração assistida pertencem aos Prompts 20, 21 e 22 e continuam não
autorizados. ADR:
[`0022`](adrs/0022-dashboard-blueprints-as-versioned-declarative-contracts.md).

## Backend Governado de Dashboards V2

```text
autenticação (tenant/user/RBAC)
-> dashboard draft + revision imutável
-> validação Blueprint V2
-> review e approval humanos
-> publication imutável + active pointer CAS
-> runtime plan canônico
-> Safe Analytical PostgreSQL
-> Validation & Provenance
-> Smart Cache/materialização publicada
-> resultado tipado + auditoria estrutural
```

`backend/services/dashboard_backend_v2/` implementa a autoridade de lifecycle,
revisions, publication, rollback, colaboração e runtime do contrato
`lumina.dashboard-backend/1.0`. A migration V22 mantém dados em 13 tabelas
tenant-scoped e não é executada por `create_all`. O router `/api/v2/dashboards`
é condicional e fica ausente em `LEGACY_ONLY`; esse continua sendo o default.

O runtime não compila SQL, não consulta Oracle e não calcula fórmulas. Ele
delega a autoridades existentes e mantém checksums, classification, permission
scope, freshness, partial e provenance. Não há frontend V2 no Prompt 20. ADR:
[`0023`](adrs/0023-governed-dashboard-revisions-publication-and-runtime.md).

## Interface Governada de Dashboards e Side Chat

```text
guard server-side + sessão HttpOnly + capability backend
-> biblioteca e publication ativa
-> runtime tipado do Prompt 20
-> registry estático de 16 widgets
-> filtros / cross-filter / drilldown declarados
-> proveniência pública
-> editor manual com preview, CAS e idempotência
-> side chat com contexto mínimo e action union fechada
-> envelope incremental completo antes de qualquer action
-> visual patch confirmado
-> nova revisão + UI_MODIFIED
```

`frontend/components/dashboard-v2/` e `frontend/lib/dashboard-v2/` implementam
`lumina.dashboard-ui-sidechat/1.0`. O frontend não recalcula fatos e não eleva
RBAC. `LEGACY_ONLY` continua default e torna rotas, link e requests V2 ausentes.
O endpoint conversacional existente recebeu apenas envelopes opcionais estritos;
nenhum path OpenAPI foi criado. ADR: [`0024`](adrs/0024-governed-dashboard-ui-and-contextual-side-chat.md).

## Assistência governada de dashboards

O Prompt 22 acrescenta `dashboard_ai_assistance_v2` entre a intenção humana e
as autoridades dos Prompts 19–21. O modelo produz intenção estrita; resolução,
clarificação, design, síntese, patches, validação e checksums são
determinísticos. Propostas versionadas exigem revisão e aceite humano; uma
segunda operação aplica somente DRAFT pelo backend Prompt 20. Migration v23
persiste o workflow com isolamento composto e histórico imutável. Produção
permanece `LEGACY_ONLY`. ADR: [`0025`](adrs/0025-ai-dashboard-proposals-with-deterministic-synthesis-and-human-approval.md).
