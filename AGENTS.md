# LuminaAI Repository Instructions

## 1. Visao geral

LuminaAI e um monorepo de Business Intelligence e Natural Language to SQL em
portugues. O backend FastAPI autentica usuarios, resolve tenant e perfil,
interpreta perguntas, executa consultas no clone analitico PostgreSQL e devolve
payloads para o frontend Next.js. Oracle e fonte de sincronizacao e
reconciliacao; nao e uma fonte permitida para consultas da IA.

Estado auditado em 2026-07-27:

- Backend: `backend/`, Python 3.12, FastAPI, Pydantic 2, SQLAlchemy async.
- Frontend: `frontend/`, Next.js 16, React 19, TypeScript 5.
- Banco corporativo e analitico: PostgreSQL.
- Origem ERP: Oracle, acessado por componentes tecnicos de sync/reconciliacao.
- Testes backend: pytest com PostgreSQL descartavel, guarda fail-closed e mocks.
- Testes frontend: Playwright com API simulada na porta isolada `3100`.
- Documentacao as-is: `docs/audit/`.

## 2. Fontes de verdade

Em caso de conflito, use esta ordem:

1. Codigo realmente executado.
2. Configuracao e entrypoints de runtime.
3. Scripts SQL, modelos e scripts de migracao.
4. Testes automatizados.
5. Scripts de instalacao e deploy.
6. Documentacao do repositorio.
7. Especificacoes externas.
8. Inferencias, sempre identificadas como inferencias.

Nao trate nomes de arquivos citados em documentacao como existentes sem
confirmar com `rg --files`.

## 3. Estrutura real

- `backend/main.py`: cria a aplicacao FastAPI, middlewares, lifespan e routers.
- `backend/routers/`: API de auth, consulta, tenant, usuarios, catalogos,
  dashboards, pacotes, conhecimento e SVR.
- `backend/services/`: pipelines, IA, semantica, seguranca, dados, sync e cache.
- `backend/services/metadata_catalog/`: catalogo corporativo, intent engine,
  canonicalizer, resolver, gerador SQL, validador, executor e grafo de conversa.
- `backend/services/data_platform/`: storage, blueprints, packages, dashboards,
  sync, linhagem, comparacao, cache e observabilidade.
- `backend/models/`: modelos SQLAlchemy.
- `backend/schemas/`: contratos Pydantic da API.
- `backend/database/`: `init.sql` e scripts de migracao ad hoc.
- `backend/tests/`: testes pytest e scripts de estresse.
- `frontend/app/`: App Router, login, dashboard e areas administrativas.
- `frontend/components/`: chat, graficos, runtime, interacoes e componentes UI.
- `frontend/hooks/useLuminaQuery.ts`: estado e transporte da conversa.
- `frontend/components/DynamicRenderer.tsx`: renderizacao visual principal.
- `frontend/lib/utils.ts`: resolucao da URL da API.
- `scripts/`: deploy, carga, backup e verificacoes auxiliares.
- `runtime-logs/`: logs e payloads de runtime; parte esta versionada.

## 4. Versoes e ferramentas confirmadas

- Python local: 3.12.10.
- Imagem backend: Python 3.12.
- Node local: 24.15.0.
- Imagem frontend: Node 20 Alpine.
- npm local: 11.12.1.
- FastAPI 0.115.5, Pydantic 2.10.3, SQLAlchemy 2.0.36, pytest 8.3.4.
- Next.js 16.2.10, React 19.2.4, TypeScript 5.
- Lockfile frontend: `frontend/package-lock.json`.
- Nao ha lockfile Python nem configuracao Alembic.

## 5. Setup confirmado

Os scripts abaixo existem, mas fazem alteracoes no ambiente. Leia-os antes de
executar:

```powershell
.\instalar_luminaai_servidor.bat
```

O instalador chama `scripts/deploy_helper.ps1`, pode instalar runtimes e
dependencias, criar arquivos de ambiente, gerar chaves, alterar firewall e
executar build. Nao o use em tarefas de auditoria ou validacao.

Setup manual refletido nos Dockerfiles e scripts:

```powershell
cd backend
python -m venv venv
.\venv\Scripts\python.exe -m pip install -r requirements.txt

cd ..\frontend
npm ci
```

Nao rode instalacao quando as dependencias ja estiverem presentes e nunca
altere lockfiles sem pedido explicito.

## 6. Execucao

Operacao Windows oficial:

```powershell
.\start-luminaai.ps1
.\stop-luminaai.ps1
```

Os scripts usam por padrao frontend `3002` e backend `8000`. Eles encerram
processos nas portas alvo e processos relacionados; nao os execute sem
necessidade operacional explicita.

Backend isolado:

```powershell
cd backend
.\.venv\Scripts\python.exe -m uvicorn main:app --host 0.0.0.0 --port 8000
```

Frontend:

```powershell
cd frontend
npm run dev -- --port 3002 --hostname 0.0.0.0
npm run start -- --port 3002 --hostname 0.0.0.0
```

`npm run dev` sem argumentos usa a porta padrao do Next.js, `3000`. O
Playwright usa `3100` e recusa portas operacionais. Nao confunda isso com a
alocacao operacional Windows do LuminaAI em `3002`.

## 7. Validacao

Frontend:

```powershell
cd frontend
npm run lint
npx tsc --noEmit
npm run build
npm run test:visual
npm run test:load
```

`test:visual` inicia um servidor dedicado na porta `3100` e nao reutiliza
servidor existente. `test:load` acessa `/health` em `127.0.0.1:8000` por
padrao e deve ser executado somente em ambiente de carga explicitamente
isolado.

Backend seguro no Windows:

```powershell
docker compose -f docker-compose.test.yml up -d --wait
.\scripts\run-backend-tests-safe.ps1 --selection all -q
docker compose -f docker-compose.test.yml down -v
```

O runner exige `TEST_DATABASE_URL`, `ENVIRONMENT=test` e
`LUMINA_TESTING=true`; nao usa `DATABASE_URL` como fallback. A guarda recusa
porta `5432`, destinos operacionais, Oracle, hosts externos e bancos sem nome
de teste antes de importar a aplicacao ou executar SQL. Bootstrap e reset
revalidam o destino conectado. Oracle, OpenAI e rede externa sao mockados.
Detalhes: `docs/testing/README.md`.

Nao existe comando configurado para lint ou type checking do backend. Para
auditoria sintatica, use parsing AST sem importar a aplicacao e sem escrever no
banco.

## 8. Convencoes de codigo

- Python: async para I/O, SQLAlchemy 2, Pydantic 2 e type hints.
- Frontend: TypeScript estrito, App Router, componentes funcionais e hooks.
- Preserve contratos legados enquanto os dois pipelines coexistirem.
- Use `rg`/`rg --files` para descoberta.
- Use `apply_patch` para edicoes manuais.
- Nao refatore codigo fora do escopo.
- Nao remova fallbacks ou compatibilidade sem testes de regressao.
- Nao masque excecoes novas com `except Exception` sem telemetria e contrato.
- Nao declare sucesso quando lint, testes, type checking ou build falharem.
- Nao remova/desabilite testes para obter resultado verde.

## 9. Regras de arquitetura

- `backend/routers/query.py` e a fronteira HTTP da consulta.
- O pipeline novo e selecionado por `NEW_PIPELINE_ACTIVE`,
  `ENABLE_DETERMINISTIC_PIPELINE` ou `use_new_pipeline`.
- Perguntas criticas podem usar o caminho deterministico em
  `NewQueryOrchestrator._execute_core_summary_query`.
- No estado auditado, esse caminho usa `get_db_context()` e `vw_vendas_lm` sem
  filtro `tenant_id`. Nao amplie esse padrao; valide e migre para uma fonte
  explicitamente isolada por tenant em tarefa funcional futura.
- O caminho generico usa intent engine, canonicalizer, metadata resolver,
  optimizer, SQL generator, security validator e database executor.
- Numeros devem vir de executores deterministas, nunca do modelo de IA.
- A IA pode interpretar intencao e redigir explicacoes; nao pode ser a fonte de
  valores, filtros finais ou SQL livre aceito sem validacao.
- Toda resposta numerica deve manter proveniencia e validacao matematica.
- Separar analise de dados de estrategia de visualizacao.
- Contratos analiticos canonicos vivem em
  `backend/contracts/analytical_v2/` e usam `lumina.analytics/2.0`.
- Preserve `time_windows` e `requested_visualizations` como listas; nunca
  reduza comparacao ou pedido visual multiplo a um campo singular.
- Use os adaptadores V1/V2 na fronteira de governanca. Nao espalhe conversoes
  condicionais pelos pipelines.
- Planos `READY` exigem tenant autenticado. Oracle nao e fonte valida para
  consultas de usuario e versao V2 desconhecida deve falhar.
- A autoridade de planejamento comparativo e
  `backend/services/comparison_planning/`, versao
  `lumina.comparison-planner/1.0`.
- O planner recebe `QueryIntentV2` e contexto confiavel; nao executa SQL, nao
  consulta banco/Oracle/OpenAI e nao calcula valores.
- Preserve N operandos, ordem, filtros especificos, baseline e alinhamento.
  Adaptador legado deve recusar estruturas que perderiam informacao.
- Metricas, dimensoes, entidades e metas do planner devem vir de providers
  governados e respeitar as allowlists do tenant autenticado.
- Mudanca no planner exige testes de idempotencia, filtros, alinhamento,
  complexidade, multitenancy, golden plans e rollback por feature flag.
- A autoridade de execucao comparativa e
  `backend/services/comparison_execution/`, versao
  `lumina.comparison-executor/1.0`.
- O executor aceita somente `QueryPlanV2` comparativo `READY`, fonte
  PostgreSQL analitica governada e isolamento de tenant comprovado.
- SQL comparativo e compilado de catalogo; valores usam binds. Oracle, OpenAI,
  SQL livre e numeros produzidos por IA sao proibidos.
- Matematica financeira permanece em `Decimal`; delta e
  `target - baseline`, percentual usa `abs(baseline)` e arredondamento final e
  `ROUND_HALF_UP`.
- Mudanca no executor exige testes de compilacao, SQL security, operandos,
  alinhamento, zero denominator, target, timeout, budgets, propriedades,
  multitenancy, golden results e rollback por feature flag.

## 10. Banco, multi-tenancy e seguranca

- Toda operacao corporativa deve derivar `tenant_id` do usuario autenticado.
- Nunca confiar apenas no `tenant_id` enviado pelo cliente.
- Toda query, cache, blueprint, package, dashboard e memoria deve ter escopo de
  tenant; quando aplicavel, tambem de usuario.
- O isolamento atual e principalmente de aplicacao e por banco clone do tenant.
  RLS nativo PostgreSQL nao foi confirmado.
- Nao introduzir SQL destrutivo em caminhos da aplicacao ou IA.
- Valores devem ser binds. Identificadores devem vir de allowlist/catalogo e
  passar por validacao.
- A IA e o endpoint de consulta nao podem abrir Oracle.
- Somente sync e reconciliacao tecnicos podem acessar Oracle.
- Credenciais Oracle/PostgreSQL devem permanecer criptografadas e nunca entrar
  em prompts, logs, respostas ou documentacao.
- Nunca ler ou imprimir conteudo de `.env` em relatorios. Documente apenas nomes.
- Nao versionar `.env`, credenciais, tokens, dumps ou logs com payload sensivel.

## 11. RBAC

- Perfis reais: `ADMIN`, `GESTOR`, `CONSULTA`.
- `ADMIN`: tenant, usuarios, configuracoes, inspector, seguranca e SVR.
- `ADMIN`/`GESTOR`: catalogo e Dashboard Studio.
- `CONSULTA`: consulta, historico, favoritos e preferencias de uso.
- Toda nova rota mutavel de governanca exige papel explicito; autenticacao
  simples nao e autorizacao administrativa.
- A protecao do frontend e ergonomica; o backend deve aplicar a regra final.

## 12. Migrations

- Nao crie nem execute migration sem pedido explicito e backup aprovado.
- O repositorio usa `backend/database/init.sql` e `migration_v*.py`, nao Alembic.
- O startup atual executa `Base.metadata.create_all`; considere esse efeito ao
  testar `backend/main.py`.
- Mudanca de modelo exige plano de migration idempotente, rollback, teste em
  banco descartavel e atualizacao da documentacao.

## 13. Metricas, formulas e blueprints

- Defina metrica uma unica vez no registro/camada de negocio.
- Registre unidade, formula, agregacao, filtros, categorias operacionais,
  tratamento de devolucao/RB/transferencia e fonte.
- Nao duplique formula em prompt, frontend e SQL.
- Blueprint nao pode armazenar SQL destrutivo ou contornar tenant/RBAC.
- Alteracoes em blueprints exigem versionamento, compatibilidade e teste.
- Rankings e totais devem validar soma por filial e total geral.

## 14. Contexto conversacional

- O frontend envia `session_id`, historico recente e `parent_id`.
- O contrato persistente e `lumina.conversation-state/1.0`, implementado em
  `backend/services/conversation_state/` e migration v12.
- O rollout usa `CONVERSATION_STATE_MODE`; producao permanece `LEGACY_ONLY`
  ate migration e rollout operacional aprovados.
- Em modo PostgreSQL, JSON local, RAM e historico do cliente nao sao
  autoridade. Toda operacao exige tenant, usuario e sessao.
- O grafo legado permanece somente para rollback nos modos de transicao.
- Contexto herdado deve registrar origem de periodo, filial, metrica, dimensao e
  visualizacao. Nova pergunta explicita sempre prevalece.
- Nao enviar historico ilimitado ao modelo; o intent engine atual usa seis
  mensagens recentes.
- Turnos usam `client_message_id`, transacoes curtas e compare-and-swap de
  `context_version`; nunca mantenha lock durante IA ou consulta analitica.
- Snapshot nao pode conter dataset, SQL, binds, credencial ou payload bruto.

### Autoridade de resolucao de contexto

- A autoridade semantica de heranca e
  `backend/services/context_resolution/`, versao
  `lumina.context-resolution/1.0`.
- O motor recebe `QueryIntentV2`, pergunta atual, snapshot PostgreSQL e
  contexto autenticado; nao persiste, consulta banco, Oracle ou OpenAI.
- Explicito prevalece sobre herdado; remocao e negacao nao podem reaparecer no
  mesmo turno; mudanca de assunto invalida heranca incompativel.
- `_question_with_inherited_context` e `SemanticPatch` permanecem somente como
  adapters legados governados.
- A persistencia do patch ocorre apenas depois da execucao bem-sucedida, por
  CAS no `ConversationStateService`.
- Branch continua do snapshot do `parent_id`; sibling, tenant e usuario nunca
  compartilham contexto.
- Producao permanece `LEGACY_ONLY`; flags do resolvedor iniciam desligadas.

### Autoridade temporal

- A autoridade temporal e `backend/services/temporal/`, versao
  `lumina.temporal.pt-BR/1.0`.
- Novos fluxos usam `TemporalNormalizer` com `TemporalContext`; nao crie helper
  paralelo nem chame `date.today()`/`datetime.now()` dentro de regras.
- Preserve listas e comparacoes. Adapter singular deve recusar pluralidade.
- Datas explicitas deterministicas prevalecem sobre inferencia da IA.
- Use a prioridade governada de timezone em `services/temporal/context.py`.
- `TimeWindow` publico possui fim inclusivo; timestamps usam o dia seguinte
  como limite exclusivo.
- Mudanca temporal exige corpus, relogio fixo, timezone, leap year, fiscal,
  range/lista/comparacao e compatibilidade legada.

### Autoridade de feedback supervisionado

- A autoridade e `backend/services/supervised_feedback/`, versao
  `lumina.supervised-feedback/1.0`.
- Feedback referencia resposta persistida por `response_node_id`, sessao,
  tenant, usuario e checksum; corpo reenviado pelo cliente nao e autoridade.
- Redacao e triagem sao deterministicas e nao podem chamar OpenAI ou Oracle.
- Autor nao revisa o proprio feedback; decisao humana final e separada da
  classificacao enviada pelo usuario.
- Feedback aprovado nao altera Knowledge Base, perfil, contexto, formula,
  SQL, prompt, embedding ou modelo.
- Candidate, exemplo, snapshot e exportacao sao passos humanos separados.
- Candidate deve passar por `VALIDATED` antes de `APPROVED`.
- Snapshot publicado e imutavel; mudanca exige nova versao explicita.
- Dataset real e tenant-scoped e exportado somente offline; nao existe
  treinamento ou publicacao automatica.
- Exportacao de dataset usa cursor e spool; importacao e somente dry-run,
  estrita, limitada e nao persistente.
- O rollout usa `SUPERVISED_FEEDBACK_MODE`; producao permanece `LEGACY_ONLY`
  e progride por `SHADOW`, `V2_COLLECT`, `V2_REVIEW` e `V2_CURATE`; todas as
  flags iniciam desligadas.

## 15. Uso de IA e tokens

- Use o `ai_credential_manager`/`ai_invocation_manager`; nao crie cliente
  paralelo sem governanca.
- Modelo autorizado atualmente: `gpt-4o-mini`.
- Nao enviar schema fisico, SQL, segredos ou dados desnecessarios.
- O caminho de explicabilidade atual envia ate 50 linhas do dataset ao modelo;
  qualquer evolucao deve reduzir, mascarar ou tornar isso opt-in por politica.
- Defina limite de tokens, timeout, retry e fallback observavel.
- Fallback nunca deve trocar silenciosamente a entidade solicitada.

## 16. Frontend

- Leia `frontend/AGENTS.md` e a documentacao da versao instalada do Next em
  `frontend/node_modules/next/dist/docs/` antes de alterar APIs do framework.
- Preserve cookies HttpOnly e `credentials: 'include'`.
- Use `getApiBase()` em vez de URLs dispersas.
- Respeite RBAC em `frontend/proxy.ts`, `Sidebar.tsx` e backend.
- Payloads visuais passam por `DynamicRenderer` e tipos em `types/lumina.ts`.
- V1 e sidecar V2 passam por
  `frontend/lib/analyticalContractAdapter.ts`; o frontend nao deve sintetizar
  numero, dataset ou formato ausente.
- Comparacoes especializadas passam por `frontend/components/comparison/`,
  versao `lumina.comparison-presentation/1.0`. Essa camada pode formatar e
  organizar, mas nunca recalcular diferenca, percentual, ranking, participacao,
  direcao, atingimento ou baseline.
- O rollout comparativo usa feature flags desligadas por padrao e mantem o
  runtime legado como fallback. Telemetria e shadow mode devem ser somente
  estruturais e nao podem registrar pergunta, valor, SQL ou dado empresarial.
- Mudancas visuais exigem type check, build e, quando seguro, Playwright nos
  viewports configurados.

## 17. Scripts Windows e portas

- Portas reservadas de outros sistemas: `3000`, `3001`, `3333`.
- LuminaAI operacional no Windows: frontend `3002`, backend `8000`.
- Playwright usa frontend `3100`; `3000`, `3001`, `3002`, `3333` e `8000`
  sao recusadas pela configuracao visual de teste.
- Nao abrir firewall, encerrar processos ou limpar cache sem pedido explicito.
- Revise `start-luminaai.ps1` antes de executar: ele encerra processos nas portas
  alvo e remove `.next/cache`.

## 18. Criterios de conclusao

Uma tarefa so esta concluida quando:

1. O fluxo afetado foi entendido no codigo real.
2. Alteracoes locais preexistentes foram preservadas.
3. Tenant, RBAC, dados sensiveis e compatibilidade foram avaliados.
4. Testes proporcionais foram executados em ambiente isolado.
5. Lint, type checking e build aplicaveis foram relatados sem mascaramento.
6. Falhas e validacoes nao executadas foram explicitadas.
7. Nenhum segredo apareceu no diff.
8. Documentacao afetada foi atualizada.

## 19. Relatorio final obrigatorio

Relate:

- objetivo e resultado;
- arquivos alterados;
- decisoes e riscos;
- comandos executados e resultados;
- testes nao executados e motivo;
- migrations/dependencias/lockfiles;
- estado final do Git;
- proxima etapa recomendada.

Nunca reverta, sobrescreva ou inclua em commit alteracoes locais que nao foram
criadas pela tarefa atual.

## 20. Base de conhecimento empresarial

- A autoridade semantica governada e `backend/services/enterprise_knowledge/`,
  versao `lumina.enterprise-knowledge/1.0`.
- Somente versoes `PUBLISHED` e vigentes podem entrar no runtime, busca,
  canonicalizer, intent ou contexto.
- `MetricRegistry` continua autoridade numerica; Knowledge Base nao calcula,
  gera SQL ou altera formulas.
- Asset e versao sao separados. Conteudo aprovado/publicado e imutavel;
  rollback sempre cria nova versao.
- Toda operacao exige tenant autenticado. `CONSULTA` le somente publicado e
  nunca escreve ou ve comentario de review.
- Autor nao aprova a propria versao. Aprovacao e vinculada ao checksum e
  publicacao exige CAS.
- Rollout usa `ENTERPRISE_KNOWLEDGE_MODE`; producao permanece `LEGACY_ONLY`.
- Migration v13 e explicita, aditiva e possui down somente para teste
  descartavel.

## 21. Perfil analitico governado

- A autoridade de preferencias pessoais e
  `backend/services/user_analytical_profile/`, versao
  `lumina.user-analytical-profile/1.0`.
- Perfil e sempre isolado por tenant e usuario autenticados. Rotas publicas
  usam `/api/v2/me`; o cliente nao escolhe o dono.
- O motor roda depois da resolucao de contexto e antes do planner. Pedido
  explicito, reset, remocao, correcao e contexto ativo vencem o perfil.
- Defaults analiticos exigem consentimento ativo e resumo publico na resposta.
  Apresentacao, localidade e acessibilidade nao podem alterar semantica.
- Perfil nao armazena pergunta, resposta, dataset, SQL, bind, credencial ou
  valor empresarial.
- Referencias pessoais usam IDs canonicos publicados. Perfil nao altera
  Knowledge Base nem `MetricRegistry`.
- Planner e executor nao consultam perfil; o executor permanece a unica
  autoridade numerica.
- Escritas usam checksum e compare-and-swap. Exclusao e soft delete ou pedido
  idempotente; auditoria minima e preservada.
- O rollout usa `USER_ANALYTICAL_PROFILE_MODE`; producao permanece
  `LEGACY_ONLY`, com todas as flags desligadas.
- Migration v14 e explicita, aditiva e possui down somente para PostgreSQL de
  teste descartavel.

## 22. Recuperacao semantica e resolucao de entidades

- A autoridade e `backend/services/semantic_retrieval/`, versao
  `lumina.semantic-retrieval/1.0`.
- O motor roda depois de Context Resolution e User Profile, e antes do
  planner. Somente `V2_AUTHORITATIVE` pode aplicar patch ao intent.
- Busca usa apenas a versao PostgreSQL `PUBLISHED` ativa do tenant. Draft,
  feedback bruto, dado proibido, Oracle, OpenAI e banco operacional nao sao
  fontes.
- Enterprise Knowledge publicada e `MetricRegistry` fornecem referencias;
  Knowledge continua autoridade semantica e MetricRegistry numerica.
- Normalizacao, feature hash, ranking, thresholds e ambiguity sao
  deterministas e versionados. Empate nunca escolhe o primeiro candidato.
- Tipo e dominio explicitos filtram candidatos antes do ranking. Perfil e
  somente desempate fraco consentido.
- Campo e valor de filtro sao resolvidos separadamente por `mention_id`.
- Clarification usa estado PostgreSQL tenant/user/session-scoped, token HMAC,
  expiracao e CAS; ID arbitrario do cliente nao e autoridade.
- Build cria nova versao e nao publica. Publication e rollback usam CAS,
  preservam historico, invalidam cache e nao mutam snapshot publicado.
- Cache inclui tenant, permission fingerprint, index/version, policies,
  locale, query fingerprint, tipo, dominio, contexto, perfil e top_k.
- Planner recebe IDs canonicos. Executor nao consulta indice semantico.
- Rollout usa `SEMANTIC_RETRIEVAL_MODE`; producao permanece `LEGACY_ONLY` e
  todas as flags funcionais iniciam desligadas.
- Migration v16 e explicita, aditiva, idempotente e possui down somente para
  PostgreSQL de teste descartavel.

## 23. Dashboard Blueprint V2

- A autoridade contratual declarativa e `backend/contracts/dashboard_blueprint_v2/`, versao `lumina.dashboard-blueprint/2.0`.
- No Prompt 19 o estado e somente `CONTRACT_ONLY`: nao existe API, model, migration, repository, runtime, pagina, renderer, editor ou side chat V2.
- Blueprint nao concede permission, nao escolhe tenant/usuario e nao contem SQL, formula, identificador fisico, dataset, credencial ou valor empresarial.
- Widgets, filtros, periodos e interacoes usam unions fechadas; registries sao estaticos e nao carregam plugins ou imports dinamicos.
- Patches visuais e semanticos sao separados; mudanca semantica exige nova revision e revalidacao.
- Canonicalizacao e checksums sao deterministas. Adapter legado somente propoe e nunca persiste ou modifica a origem.
- `backend/services/blueprints.json`, modelos e runtime legados permanecem autoridade operacional ate rollout futuro aprovado.
- Persistencia, renderer e proposta por IA dependem dos Prompts 20, 21 e 22; nenhuma dessas etapas e autorizada pelo contrato.

## 24. Backend governado de dashboards

- A autoridade backend V2 e `backend/services/dashboard_backend_v2/`, versao
  `lumina.dashboard-backend/1.0`; ela consome somente Blueprint V2 validado.
- Tenant, usuario, role, ownership e grants sao server-controlled. Roles de
  colaborador restringem RBAC global e nunca o elevam.
- Revisoes, reviews, approvals, publications e auditoria sao imutaveis;
  active publication, metadata, head e collaborators usam CAS.
- Rollback cria nova publication; nunca apaga ou reativa linha historica.
- Runtime aceita somente publication ativa, reutiliza Safe Analytical
  PostgreSQL, Validation & Provenance e Smart Cache, e preserva Decimal,
  classification, freshness, partial e provenance.
- Migration v22 e explicita, aditiva e excluida de `create_all`; down existe
  somente para PostgreSQL descartavel de teste.
- O rollout usa `DASHBOARD_BACKEND_MODE`; producao permanece `LEGACY_ONLY`,
  todas as flags ficam desligadas e a allowlist vazia.
- Prompt 20 nao cria pagina, renderer, editor, side chat ou geracao por IA.

## 25. Interface governada de dashboards e side chat

- A autoridade de apresentação V2 é `frontend/components/dashboard-v2/`, versão
  `lumina.dashboard-ui-sidechat/1.0`.
- `DASHBOARD_UI_MODE` é server-controlled e permanece `LEGACY_ONLY` por padrão;
  a flag pública apenas controla ergonomia e nunca concede acesso.
- Rotas `/dashboard/v2`, runtime, editor e histórico usam guard server-side e
  capabilities efetivas do backend. A Sidebar só aparece após capability real.
- O registry dos 16 widgets é estático. Widget ou result shape desconhecido
  falha fechado e os demais widgets permanecem disponíveis.
- O navegador não calcula métrica, delta, percentual, ranking ou null; apenas
  apresenta os valores tipados retornados pelo runtime certificado.
- Cross-filter e drilldown só usam interações declaradas no Blueprint ativo.
- Side chat reutiliza `/api/v1/query/` com contexto mínimo e action union fechada;
  não recebe SQL, dataset completo ou blueprint inteiro e não publica, aprova,
  executa rollback, gerencia colaboradores ou aplica semantic patch.
- Visual patch exige preview, confirmação humana, idempotency key, CAS e nova
  revisão do backend. `UI_MODIFIED` só ocorre após confirmação e preserva o
  checksum semântico.
- Requests são cancelados em unmount, logout, troca de usuário/tenant e nova
  geração; respostas antigas não sobrescrevem estado novo.
- Prompt 21 não autoriza Prompt 22, rollout produtivo, migration v23, nova
  dependência ou alteração de lockfile.

## 25. Assistência governada de dashboards por IA

- A autoridade é `backend/services/dashboard_ai_assistance_v2/`, versão
  `lumina.dashboard-ai-assistance/1.0`.
- O modelo interpreta somente intenção; resolução canônica, clarificação,
  design spec, Blueprint, patches, checksums e aplicação são determinísticos.
- Proposta, versão, evidência, decisão e auditoria são imutáveis. Aceite não
  aplica; aplicação é request separado e cria apenas DRAFT via Prompt 20.
- IA não publica, aprova, executa rollback, gerencia colaboradores, transfere
  ownership, executa SQL/analytics ou consulta Oracle.
- Toda operação é tenant/user-scoped e respeita RBAC e grants reais. Entrada
  não concede tenant, role, permission, provider, tool ou canonical ID.
- O rollout usa `DASHBOARD_AI_ASSISTANCE_MODE`; produção permanece
  `LEGACY_ONLY`, APIs/frontend desligados e allowlist vazia.
- Migration v23 é explícita, aditiva, excluída de `create_all` e possui down
  somente para PostgreSQL descartável de teste.
