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
