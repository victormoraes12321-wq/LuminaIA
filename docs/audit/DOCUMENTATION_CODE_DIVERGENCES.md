# Divergencias Entre Documentacao E Codigo

Data: 2026-07-27.

Status permitidos: Confirmado, Confirmado com divergencia, Parcial, Ausente,
Substituido por outra implementacao, Obsoleto, Nao utilizado, Nao foi possivel
confirmar.

## Matriz principal

| Componente esperado | Caminho esperado | Caminho real/evidencia | Status | Impacto e recomendacao futura |
| --- | --- | --- | --- | --- |
| Orquestrador | `services/new_query_orchestrator.py` | mesmo caminho; `run_pipeline` | Confirmado com divergencia | bloco debug duplicado; reduzir apos baseline |
| Context Guard | `services/context_guard.py` | mesmo caminho | Confirmado | usado no legado; confirmar cobertura do novo |
| Planner Engine | `services/planner_engine.py` | `metadata_catalog/resolver.py`, `executor.py:QueryPlanner`, `query_planner.py` | Substituido por outra implementacao | tres conceitos de planner; consolidar contrato |
| Plan Validator | `services/plan_validator.py` | mesmo caminho + `metadata_catalog/executor.py:SecurityValidator` | Confirmado com divergencia | validacao legada e nova separadas |
| Breakdown Service | `sales_value_breakdown_service.py` | `sales_value_breakdown.py` | Substituido por outra implementacao | corrigir referencias documentais |
| Query Optimizer | `query_optimizer_engine.py` | wrapper + `metadata_catalog/executor.py:QueryOptimizer` | Confirmado com divergencia | wrapper de compatibilidade |
| Semantic Layer | `semantic_layer.py` | mesmo caminho + catalogo corporativo | Confirmado com divergencia | duas fontes semanticas |
| Canonicalizer | `services/canonicalizer.py` | `services/metadata_catalog/canonicalizer.py` | Substituido por outra implementacao | atualizar caminhos |
| SQL Sanitizer | `security_and_normalization_engine.py` | wrapper + `metadata_catalog/executor.py:SecurityValidator` | Confirmado com divergencia | bloqueio lexical, nao parser SQL |
| Analytical Storage | `data_platform/analytical_storage.py` | mesmo caminho | Confirmado | possui mock/fallback local |
| AQD | `aqd_service.py` | mesmo caminho | Confirmado | decompose/ARP; uso principal e legado/parcial |
| Cache | `cache_service.py` | mesmo + caches especializados | Confirmado com divergencia | RAM local, nao distribuido |
| Scheduler | `scheduler.py` | mesmo + `data_platform/sync_scheduler.py` | Confirmado | dois niveis de agendamento |
| Sync | `sync_service.py` | mesmo + `data_platform/sync_engine.py` | Confirmado com divergencia | duas implementacoes/coordenacoes |
| Reconciliation | `erp_reconciliation.py` | mesmo + `daily_reconciliation.py` | Confirmado | Oracle tecnico e clone |
| Blueprint | `models/blueprint.py` | mesmo caminho | Confirmado | repository enterprise adicional |
| Metadata Catalog | `models/metadata_catalog.py` | mesmo + dois catalogos de servico | Confirmado com divergencia | ORM, data platform e catalogo em memoria |
| View Catalog | `models/view_catalog.py` | mesmo caminho | Confirmado | tenant scoped |
| Business KPI | `models/business_kpi.py` | mesmo caminho | Confirmado | endpoint de escrita sem role forte |
| Business Formula | `models/business_formula.py` | mesmo caminho | Confirmado | engine e governanca presentes |
| Pipeline Contracts | `models/new_pipeline_contracts.py` | mesmo caminho | Confirmado | coexistem contratos legados |
| Dashboard | `frontend/app/dashboard/page.tsx` | mesmo caminho | Confirmado | chat e resposta inline |
| Dynamic Renderer | `components/DynamicRenderer.tsx` | mesmo caminho | Confirmado | ECharts, tabela e multi-vis |
| API Base Resolver | nao especificado | `frontend/lib/utils.ts:getApiBase` | Confirmado | fallback 127.0.0.1:8000 |
| Contexto conversacional | persistencia esperada | JSON/RAM + history/memory PostgreSQL | Parcial | grafo nao distribuido |
| Multi-tenant | isolamento estrito | JWT, filtros e banco clone por tenant | Parcial | RLS nativo nao confirmado |
| RBAC | perfis | ADMIN/GESTOR/CONSULTA | Confirmado com divergencia | rotas BKE/packages mutaveis fracas |
| RLS | esperado em arquitetura enterprise | helper/validator de aplicacao; sem policy SQL confirmada | Nao foi possivel confirmar | criar/verificar policies reais |
| PostgreSQL | banco analitico/local | corporativo + clone; core summary usa conexao principal | Confirmado com divergencia | validar isolamento de `vw_vendas_lm` |
| SQLite | banco local opcional | nenhuma referencia propria de runtime | Ausente | remover afirmacao de suporte atual |
| Oracle | origem possivel | sync, reconciliacao e scripts tecnicos | Confirmado | nao usar na query/IA |
| Portas | frontend 3002/backend 8000 | Windows 3002/8000; Docker 3000/8000; Playwright 3100 | Confirmado por contexto | manter teste e operacao separados |
| Scripts Windows | esperados | BAT/PowerShell presentes, varios nao rastreados | Confirmado com divergencia | revisar e versionar apos seguranca |
| Health | `/health`, `/health/deep` | `backend/main.py`; `/healthz` frontend | Confirmado | deep nao testa clone/Oracle por design |
| Comercial/precos SaaS | possivel mistura | nao encontrado no runtime | Ausente | manter fora do codigo tecnico |

## Divergencias documentais relevantes

### 1. Porta do frontend

- `README.md` afirma que `start-luminaai.ps1` sobe frontend em 3000.
- O script atual usa 3002 por padrao.
- Dockerfile/Compose operacional usam 3000; Playwright usa 3100.
- Especificacoes recentes reservam 3000 para outro sistema e usam 3002.

Conclusao: nao existe uma unica porta global; ha contextos distintos. O
Playwright recusa as portas operacionais e nao reutiliza servidor existente.

### 2. Isolamento Oracle

Documentacao recente diz que Oracle fica isolado em sync/reconciliacao. Isso e
verdade para o caminho novo de consulta, mas o repositorio contem:

- `oracle_service.py` publico para servicos;
- scripts de health/discovery/reconciliation;
- caminhos legados com nomes/comentarios Oracle;
- mocks Oracle sobre PostgreSQL.

Recomendacao: impor dependencia arquitetural por modulo e teste de imports, nao
apenas convencao textual.

O isolamento PostgreSQL tambem diverge da descricao simplificada: o executor
generico abre o clone configurado do tenant, enquanto core summaries usam
`get_db_context()` e `vw_vendas_lm` sem filtro de tenant. A seguranca depende de
essa base/view ser fisicamente exclusiva, o que nao foi confirmado.

### 3. Certificacao de testes

Documentos historicos registram suites verdes. O baseline reproduzivel atual:

- lint frontend passa sem erros ou avisos;
- pytest exige `TEST_DATABASE_URL` e PostgreSQL descartavel;
- suite backend atual: 667 passed e 4 xfailed estritos;
- Playwright mockado: 16 passed na porta 3100;
- build e type checking passam.

Relatorios historicos nao devem ser apagados, mas nao representam certificacao
atual em 2026-07-27.

### 4. Migrations

Guias sugerem inicializacao/migrations controladas, mas:

- nao ha Alembic;
- scripts `migration_v*.py` sao ad hoc;
- `init.sql` centraliza parte do schema;
- `main.py` executa `create_all` no startup.

Recomendacao: baseline e ferramenta de migration antes de evoluir modelos.

### 5. Pipeline "oficial"

O repositorio possui pipeline novo e legado, selecionados por flags. Diagramas
lineares que mostram um unico fluxo sao incompletos.

Recomendacao: documentar ambos ate concluir strangler/rollout.

### 6. Persistencia de conversa

Documentacao sugere contexto persistente, mas o grafo principal e JSON/RAM.
SearchHistory e SemanticMemory estao no PostgreSQL, porem nao substituem o
estado completo do grafo.

### 7. Seguranca e RLS

Ha classes e comentarios que usam o termo RLS, mas nenhuma migration/policy
PostgreSQL de `CREATE POLICY` foi encontrada. O isolamento comprovado e de
aplicacao e por clone.

### 8. Dados enviados a IA

Arquitetura afirma desacoplamento NLU-SQL, confirmado para intent. Entretanto,
explainability envia amostra do dataset ao modelo. A documentacao de seguranca
deve registrar essa saida de dados explicitamente.

## Codigo aparentemente obsoleto ou de compatibilidade

- `query_optimizer_engine.py`: wrappers.
- `security_and_normalization_engine.py`: wrappers/excecoes.
- `services/ai/legacy_contracts.py`.
- `InlineDashboardRuntime` e `dashboardRuntimeAdapter`.
- componentes Recharts antigos ao lado de ECharts.
- rota `/api/v1/api/v1/query`.
- dois pipelines e varios engines com funcoes sobrepostas.

Nao e seguro remover esses itens sem instrumentacao de uso e testes.

## Caminhos documentados que nao existem

- `backend/services/planner_engine.py`
- `backend/services/sales_value_breakdown_service.py`
- `backend/services/canonicalizer.py`

Substitutos reais estao na matriz. Todos os demais caminhos obrigatorios
citados na solicitacao foram encontrados, salvo esses nomes.

## Evidencia de qualidade atual

- Python AST: aprovado nos arquivos alterados pelo Prompt 04.
- TypeScript: aprovado.
- Build Next: aprovado.
- ESLint: aprovado sem erros ou avisos.
- pytest: 667 passed e 4 xfailed estritos em banco descartavel.
- Playwright: 16 passed na porta isolada 3100.
- Nenhuma CI/CD foi encontrada.

## Recomendacao

Tratar `docs/audit/` como fotografia as-is. Documentos de produto/arquitetura
alvo podem continuar descrevendo futuro, mas devem declarar explicitamente
"target" e nunca substituir evidencia do codigo atual.
