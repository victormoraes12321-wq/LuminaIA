# Baseline Seguro De Testes

## Prompt 26 — 2026-08-10

- Versão: `lumina.security-migration-rollout/1.0`.
- Security readiness determinístico: `32/32 PASS`, `0 FAIL`, `0 CRITICAL FAIL`.
- Testes dirigidos Prompt 26: `36 passed`, `0 failed`, `0 skipped`.
- Backend final seguro: `1906 passed`, `0 failed`, `0 errors`, `0 skipped`,
  `0 xfailed`, `0 XPASS`, 2 warnings Pydantic preexistentes, em `1752.99s`.
- Frontend: ESLint `0 errors/13 warnings`; TypeScript PASS; Next build PASS,
  28 páginas/rotas; Playwright completo duas vezes, `412 passed`, `0 failed`,
  `0 skipped` em `19.9m` e `14.0m`.
- AST: `826` arquivos Python próprios analisados, `0` erros; Docker config PASS.
- OpenAPI DEFAULT duas vezes: `190 paths`, `216 operations`, `0` Prompt 26,
  SHA-256 `ab2ed7a6f3f67828ab3837f9b9f12e6746c1198449beb74fd66a0ef1cf718f0b`.
- OpenAPI COMBINED duas vezes: `256 paths`, `289 operations`, 66 experimental-only,
  SHA-256 `c4f7c6731be6a074d9f589d6def0dcedcbaf0ab1269581854524ac538c26b52c`.
- A mudança de hash preserva counts/paths e decorre do auth server-derived de
  Validation V2 e das sete novas suites fechadas no enum Prompt 24.
- Reconciliação canônica Prompt 26.1:
  - PRE-PROMPT26 CANONICAL DEFAULT:
    `87f5f4835a4555e44f8a2640ffb9facead89763f9ba1d1a7b570cad9976792e3`.
  - POST-PROMPT26 CANONICAL DEFAULT:
    `ab2ed7a6f3f67828ab3837f9b9f12e6746c1198449beb74fd66a0ef1cf718f0b`.
  - PRE-PROMPT26 CANONICAL COMBINED:
    `bfae6ce1c42932c69312638db31fc81181d3a7def7efdfde39246a51af9124bb`.
  - POST-PROMPT26 CANONICAL COMBINED:
    `c4f7c6731be6a074d9f589d6def0dcedcbaf0ab1269581854524ac538c26b52c`.
  - Algoritmo oficial inalterado: SHA-256 de
    `json.dumps(app.openapi(), sort_keys=True).encode()`.
  - Diff: 0 paths/operations adicionados ou removidos; dois endpoints Validation V2
    passaram de headers client-controlled para OAuth2 server-derived; o GET perdeu
    apenas o 422 associado aos headers; COMBINED ampliou somente
    `EvaluationSuiteKindV2` de 19 para 26 valores.
  - Causa: `INTENTIONAL_SECURITY_SCHEMA_HARDENING`; zero breaking change default
    indevida e hashes pós-Prompt 26 reproduzidos em dois processos limpos.
  - Regressão proporcional: `36 passed`, `0 failed`, `0 skipped`, `0 xfailed`;
    backend `1906`, Playwright `412 + 412` e AST `826/0` retidos.
- Exports duas vezes: 26 schemas SHA-256
  `fff4376d81318e8735176ef1e83bee4675c9551347420ff498ba46939101730b`;
  4 goldens SHA-256 `7473486463db4934a54746ae88d7f5113a1bd6d5a6a3d6bdf79e0c58718389c9`;
  aggregate manifest `1a41a8a17d32c0d2a5fcb982dc94abb284f0d0b9bd7e216aa375c5fdc2736d46`.
- Blueprint Git blob preservado:
  `2F2C79E87D0B1564B3BA04F40B0ABA0B05430B411EDAFDD6064028A7E2403744`;
  Git diff `0 bytes`.
- Migration v27: `NOT_REQUIRED`; v1–v23 tracked inalteradas e v24–v26
  preexistentes/untracked não foram editadas pelo Prompt 26. Advisory lock real PASS.
- Produção: `LEGACY_ONLY`; worker, performance, rollout e canary desligados;
  migration/rollout/canary reais não executados.
- Status: **PROMPT 26 — FULL_SUITE_CERTIFIED. PHASE 23–26 CHECKPOINT — AUTHORIZED.**

## Prompt 25.4 — 2026-08-10

- **Reconciliação Definitiva do Hash OpenAPI DEFAULT e Titularidade de Domínio**:
  - Hash Canônico Oficial DEFAULT (Full Schema): `87f5f4835a4555e44f8a2640ffb9facead89763f9ba1d1a7b570cad9976792e3` (`190` paths, `216` ops).
  - Hash Canônico Oficial PROMPT25_ONLY (Full Schema): `cd3d7c277651c22c6eaf49e5c1ce530103cdc8aae604d3b06c4d428808c4f00a` (`201` paths, `227` ops, `11` paths P25).
  - Hash Canônico Oficial COMBINED (Full Schema): `bfae6ce1c42932c69312638db31fc81181d3a7def7efdfde39246a51af9124bb` (`256` paths, `289` ops).
  - Summary Hash Prompt 25.3 (Cálculo Informático `{paths, ops}`): `b078c4d659d2f21ee68d154650517337aee7724218c5e2e230e778c5b24c170c` (`HASH_ALGORITHM_LEGACY` summary dict).
  - Causa Raiz da Divergência 25.3: `HASH_METHOD_CHANGED` (serialização do dicionário completo `app.openapi()` vs dicionário de resumo `{paths, ops}`).
  - Superfície OpenAPI DEFAULT 100% Inalterada: 0 paths adicionados/removidos, 0 operações alteradas, 0 request/response contracts alterados, 0 security declarations alteradas.
  - Correção de Titularidade: 5 paths `/api/v2/cache/*` pertencem ao **Prompt 18 (Smart Cache / Materialização)**.
  - Composição 66 Experimental-Only: Prompt 18 (5) + Prompt 20 (22) + Prompt 22 (11) + Prompt 23 (7) + Prompt 24 (10) + Prompt 25 (11) = 66 paths (`256 - 190 = 66`).
  - Suíte Backend Retida: `1870 passed`, `0 failed`, `0 errors`, `0 skipped`.
  - Suíte Playwright Retida: `412 passed`, `0 failed`, `0 skipped`.
  - Status: **PROMPT 25 — FULL_SUITE_CERTIFIED. PROMPT 26 LIBERADO E AUTORIZADO.**

## Prompt 24.4 — 2026-08-08

- Reconciliação Definitiva do Hash Protegido de `backend/services/blueprints.json`:
  - Working Tree File SHA-256 (Windows CRLF): `BC29EDCD9CF0973CB580A49D081F8DD4773C1CB20877DA7D50F299E39821A63B` (`1067352` bytes).
  - Git Blob SHA-256 (Commits `c7c4e58` -> `14e13bc` -> `880477a` LF): `2F2C79E87D0B1564B3BA04F40B0ABA0B05430B411EDAFDD6064028A7E2403744` (`1034926` bytes).
  - Estado Git: Unmodified (0 alterações no arquivo, `git status` limpo).
  - Causa Raiz: Variação nativa do Git autocrlf/LF no checkout Windows + string herdada em documentações legadas.
  - Imutabilidade Comprovada: `before_hash == after_hash` (`True`).
  - Decisão: **PROMPT 25 LIBERADO E AUTORIZADO.**

## Prompt 24.3 — 2026-08-08

- Reconciliação Definitiva da Superfície OpenAPI e Teste Isolado:
  - Default Mode: `190` paths, `216` operações, `0` rotas Prompt 24 V2. SHA-256: `87f5f4835a4555e44f8a2640ffb9facead89763f9ba1d1a7b570cad9976792e3` (reproduzível).
  - Experimental Mode: `240` paths, `273` operações, `10` rotas Prompt 24 V2 (`11` operações). SHA-256: `02bc0d6cf8ffa2f2b5c7ff479e04850e83081544eacfb5f3c3c808536141072f` (reproduzível).
  - Isolamento de Schemas: `default_hash != experimental_hash` (`True`).
  - Adicionado `test_openapi_default_vs_experimental_isolation(monkeypatch)` em `backend/tests/test_observability_v2_router.py`.
- Suíte Playwright Integral Preservada: `412 collected, 412 passed, 0 failed, 0 skipped` em 4 viewports.
- Suíte Backend Pytest Preservada: `1851 passed, 2 warnings` em `127.0.0.1:55432/luminaai_test`.
- Status: **CERTIFICAÇÃO DEFINITIVA CONCLUÍDA. PROMPT 25 LIBERADO.**

## Prompt 24.2 — 2026-08-07

- Certificação Final Playwright com Zero Skips: `412 collected, 412 passed, 0 failed, 0 skipped` em 4 viewports (`desktop`, `tablet`, `mobile`, `ultrawide`).
- Validação Consecutiva: 2 rodadas consecutivas de Playwright integral aprovadas com `412 passed, 0 failed, 0 skipped` cada.
- Backend seguro: `1851 passed, 0 failed, 0 skipped, 2 warnings` em `127.0.0.1:55432/luminaai_test` (24 min 50s).
- Frontend QA: ESLint exit 0 (13 warnings), TypeScript `tsc --noEmit` exit 0, `npm run build` exit 0 (28 páginas estáticas e dinâmicas geradas em 37.7s).
- OpenAPI Hashes SHA-256:
  - Default Mode: `87f5f4835a4555e44f8a2640ffb9facead89763f9ba1d1a7b570cad9976792e3`
  - Experimental Mode: `87f5f4835a4555e44f8a2640ffb9facead89763f9ba1d1a7b570cad9976792e3`
- Status: **CERTIFICAÇÃO CONCLUÍDA E APROVADA. PROMPT 25 AUTORIZADO.**

## Prompt 20 — 2026-08-05

- Contrato `lumina.dashboard-backend/1.0` implementado sobre
  `lumina.dashboard-blueprint/2.0`; produção permanece `LEGACY_ONLY`.
- Dirigidos Prompt 19 + 20: `255 passed` em 81,31 s, sem skip/xfail.
- Backend seguro: `1676 passed`, `1 xfailed`, `0 failed`, `0 errors`,
  `0 skipped`, `0 XPASS`, 2 warnings Pydantic preexistentes, em 1217,51 s.
- Único xfail: `LUMINA-GAP-DASH-001`; razão e assertion preservadas.
- PostgreSQL v22: 13 tabelas, up idempotente, down test-only, cadeia
  v13–v22–v13–v22, constraints, índices, CAS, imutabilidade e isolamento
  tenant aprovados em `127.0.0.1:55432/luminaai_test`.
- Backup/restore descartável: `pg_dump`/`pg_restore` com fixtures sintéticas;
  manifesto `65671b1ac442e5de5b24925219158a55c73d5d1a7f1b0471dc79fc9545a9505b`
  idêntico antes/depois; dump removido e v22 desmontada ao final.
- OpenAPI default: 190 paths/216 operações e zero rota Prompt 20, hash
  `0cf1a1d52fab2ae3cf4a883657c4a111f443e4e19072f34f8f02b50afbc163dd`.
- OpenAPI experimental explícita: 212 paths/243 operações, com 22 paths/27
  operações Prompt 20, hash
  `80ec5583c29dc1a478e8ce7fb1027eea546ad2c5a45960f77e094756750d7845`;
  ambas as superfícies foram geradas duas vezes com hashes idênticos.
- Schemas: 55 contratos em arquivo único reproduzível, SHA-256
  `DA38BFB943258E9E50F1C909A654EA845CD5496026EBDD75A26030476135B9A0`;
  24 goldens sintéticos, SHA-256
  `358260EAD1F7BE1FE927F165BDA0E736B2212521C843353A34AECB11DB97EC71`.
- Frontend: ESLint exit 0 com 8 warnings preexistentes; TypeScript exit 0;
  build exit 0 com 23 páginas; Playwright `260 passed` em 8,6 min nos quatro
  viewports. Nenhuma página, Sidebar, renderer, editor ou side chat V2.
- AST: 702 arquivos Python próprios, 0 erros; Docker Compose config exit 0.
- `blueprints.json`: hash inicial/final
  `407D5C65B7A38A805C073F064A0C1CD9AF6290C8BCBE18809CA645CD81042596`.
- Dependências e lockfiles inalterados; OpenAI real, Oracle runtime, banco
  operacional, porta 5432 e provider/rede externa: zero acesso.
- A primeira regressão integral detectou três falhas de isolamento do Prompt 20
  e uma falsa falha temporal sob carga concorrente. O handler V2 passou a ser
  registrado somente com o router habilitado e a fixture v22 ganhou cleanup
  garantido. Os quatro casos e a suíte integral foram reexecutados com sucesso.

## Prompt 19 — 2026-08-04

- Contrato `lumina.dashboard-blueprint/2.0`, exclusivamente `CONTRACT_ONLY`.
- Dirigidos: `192 passed` em 1,60 s, sem skip/xfail novo.
- Backend seguro: `1613 passed`, `1 xfailed`, `0 failed`, `0 errors`,
  `0 skipped`, `0 XPASS`, 2 warnings preexistentes, em 1155,64 s.
- Único xfail: `LUMINA-GAP-DASH-001`; assertion e razão preservadas.
- Frontend: ESLint exit 0 com 8 warnings preexistentes; TypeScript exit 0;
  build exit 0 com 23 páginas; Playwright `260 passed` em 9,1 min.
- Viewports: desktop, tablet, mobile e ultrawide; porta isolada 3100.
- AST: 676 arquivos Python próprios, 0 erros; Docker Compose config exit 0.
- PostgreSQL descartável somente em `127.0.0.1:55432/luminaai_test`, removido.
- 91 schemas + 20 goldens = 111 artefatos; duas execuções externas, cada uma
  com duas internas, produziram SHA-256 agregado
  `3da4a55b48b5ac1bb2f1107e3d752790e8dabb401ebcae8edbe3c7b1178aa2ac`.
- OpenAPI: 190 paths/216 operações, zero Prompt 18/19; hash lógico
  `c6ff6058d14491d23581e86909e77a4206011afd17bba6e79ed4d797890b258b`.
- `blueprints.json`: hash inicial/final
  `407D5C65B7A38A805C073F064A0C1CD9AF6290C8BCBE18809CA645CD81042596`.
- Nenhuma migration v22, API, model, página, Sidebar, dependência ou lockfile.
- OpenAI real, Oracle runtime, banco operacional e provider/rede externa: zero.
- Produção/legado inalterados; portas 55432, 3100, 3002 e 8000 encerradas.

## Prompt 18 — 2026-08-04

- Backend integral: `1421 passed, 1 xfailed, 0 failed, 0 errors, 0 XPASS`.
- Único xfail: `LUMINA-GAP-DASH-001`; TENANT-001 é teste regular aprovado.
- Duração backend final: `1113.16 s`; warnings: 2 de `min_items` Pydantic preexistente.
- Prompt 18 dirigido: 77 testes (74 backend/DB/bootstrap/blueprints/API mais 3
  de isolamento frontend), sem skip/xfail.
- Prompts 14–17 dirigidos: 64 passed; TENANT-001 isolado: 1 passed.
- V21: up, segundo up idempotente, down, schema/constraints/índices, FK
  cross-tenant, rollback sintético e cadeia V21→V12→V21 aprovados em
  `127.0.0.1:55432/luminaai_test`.
- Blueprints: SHA-256 inicial/final
  `407D5C65B7A38A805C073F064A0C1CD9AF6290C8BCBE18809CA645CD81042596`.
- Reprodutibilidade: 47 artefatos Prompt 17/18 reexportados, zero divergências;
  total atual 127 schemas JSON e 17 goldens JSON; OpenAPI default 190 paths,
  216 operações e zero path Prompt 18.
- Frontend: ESLint exit 0 com 8 warnings preexistentes; TypeScript e build exit
  0; 23 páginas geradas; Playwright `260 passed` em quatro viewports.
- AST: 652 arquivos Python próprios, zero erros; Docker config exit 0.
- OpenAI real, Oracle runtime, banco operacional/5432, dependências, lockfiles,
  segredos, SQL livre armazenado, binds sensíveis e chain of thought: zero.
- Produção preservada em `LEGACY_ONLY`, admin false, sem rollout.

## Prompt 13 - 2026-07-30

- Backend integral: `1279 passed, 2 xfailed, 0 failed, 0 XPASS`.
- Xfails preservados: `LUMINA-GAP-DASH-001` e `LUMINA-GAP-TENANT-001`.
- PostgreSQL: Docker descartavel em `127.0.0.1:55432/luminaai_test`.
- Semantic Retrieval dirigido: contratos, normalizacao, ranking, provider,
  migration v16, build, idempotencia, publication, rollback, stale, eval,
  clarification, RBAC, multi-tenant, APIs, schemas e goldens aprovados.
- Schemas: 87 arquivos exportados duas vezes com hashes identicos.
- OpenAPI: 170 paths e 195 operacoes; 21 paths e 22 operacoes semanticas.
- Frontend: ESLint, TypeScript e build aprovados.
- Playwright integral: `260 passed` em desktop, tablet, mobile e ultrawide.
- AST: 484 arquivos Python do repositorio, zero falhas.
- Oracle/OpenAI/rede externa: mockados e proibidos pelo runner.
- Producao: `SEMANTIC_RETRIEVAL_MODE=LEGACY_ONLY`.

Comando backend:

```powershell
docker compose -f docker-compose.test.yml up -d --wait
.\scripts\run-backend-tests-safe.ps1 --selection all -q
docker compose -f docker-compose.test.yml down -v
```

Data da execucao: 2026-07-28.

## Veredito

**Baseline V2 com estado conversacional PostgreSQL aprovado e tres gaps
funcionais explicitos.**

A infraestrutura de teste e fail-closed, usa PostgreSQL descartavel, dados
sinteticos e mocks de Oracle/OpenAI. Nenhuma falha inesperada permaneceu na
suite. Tres contratos corretos ainda nao sao atendidos pelo produto e foram
mantidos como `xfail(strict=True)`, sem alterar expectativas para aceitar
respostas erradas.

## Resultado Consolidado

| Validacao | Resultado |
| --- | --- |
| Coleta pytest | 997 testes, sem erro |
| Suite backend completa | 994 passed, 3 xfailed, 0 failed, 0 xpassed |
| Estado conversacional + migration | 27 passed, sem warning |
| Executor comparativo dedicado | 233 passed, sem xfail |
| Contratos + temporal + planner + executor puro | 454 passed |
| Duracao backend completa final | 859,14 s |
| Planner comparativo dedicado | 66 passed |
| Baseline de banco/contrato | 14 passed, 2 xfailed |
| Multitenancy dedicado | 10 passed, 1 xfailed |
| Seguranca dedicada | 37 passed |
| Guardas dedicadas | 20 passed |
| Integracao auth/admin/security/query | 9 passed |
| ESLint | 0 erros, 0 warnings |
| TypeScript `--noEmit` | aprovado |
| Next.js build | aprovado |
| Playwright visual | 192 casos na matriz final |
| Presentation model comparativo | 56 passed (14 cenarios x 4 projetos) |
| Renderer comparativo | 96 passed (24 cenarios x 4 projetos) |
| Porta Playwright | 3100 |
| Oracle real | nao acessado |
| OpenAI real | nao acessada |
| Portas operacionais | nao usadas |

O Docker CLI estava disponivel, mas o servico Docker do Windows nao pode ser
iniciado pela sessao atual. Para validar o runtime sem reduzir a contencao, foi
iniciado um cluster
PostgreSQL 17 separado e descartavel em `127.0.0.1:55432`, fora da instancia
operacional `5432`. Ele foi usado somente pela suite e removido ao final.

## Numeros Validados

O tenant A confirmou, por SQL deterministico:

- junho/2026: comercial `300,00`, RB `30,00`, devolucao `-20,00`,
  bonificacao `40,00`, transferencia `500,00`, bruto sem transferencia
`350,00`;
- julho/2026: comercial `400,00`, RB `50,00`, devolucao `-10,00`,
  transferencia `600,00`, bruto sem transferencia `440,00`;
- ticket medio comercial de junho: `150,00`;
- desconto total de junho: `40,00`;
- desconto medio de junho: `20,00`;
- filtros por filial, vendedor, produto e categoria;
- separacao de RB, devolucao, bonificacao e transferencia;
- transferencia excluida do faturamento;
- totais do tenant B diferentes apesar de nomes coincidentes.

## Falhas Corrigidas Nesta Etapa

1. Pytest podia herdar `DATABASE_URL` e escrever no banco ativo.
2. Reset e bootstrap nao possuiam guarda conectada.
3. Testes dependiam de usuarios e senhas reais da empresa.
4. Oracle e OpenAI podiam ser acionados por testes.
5. Conexoes async eram compartilhadas entre event loops.
6. Dataset sintetico usava e-mails rejeitados pelo schema.
7. Teste administrativo esperava Oracle real em vez de mock.
8. Treinamento semantico dependia de IA externa.
9. Sincronizacao colidia com a view SQL do baseline.
10. Playwright usava/reutilizava porta operacional.
11. Frontend tinha 8 erros e 27 warnings de lint.
12. Configuracao visual continha tipos frouxos que bloqueavam lint/type check.

## Contratos V2 Validados

- `lumina.analytics/2.0` rejeita versao desconhecida;
- pergunta exata junho/julho preserva os dois periodos e operandos;
- quatro variacoes temporais e ordem invertida foram aprovadas;
- tabela e grafico preservam os dois formatos e a ordem;
- V1, sidecar V2 e round-trip permanecem compativeis;
- fora de escopo nao vira ambiguidade;
- falha do intent engine nao vira Cliente;
- readiness diferente de `READY` nao executa banco;
- schemas Pydantic foram exportados de forma deterministica;
- frontend aceita V1 e sidecar V2 pelo adaptador central.

## Normalizador Temporal V2

- `lumina.temporal.pt-BR/1.0` usa relogio e timezone injetaveis;
- corpus pt-BR com 55 casos versionados;
- 99 testes temporais aprovados sem xfail;
- datas absolutas, relativas, moveis, fechadas e acumuladas;
- trimestre, semestre, semana ISO, quinzena e calendario fiscal;
- range, lista e comparacao estruturalmente distintos;
- wrappers singulares recusam pluralidade;
- limites inclusivos geram o dia seguinte como fim exclusivo no adapter;
- shadow mode registra fingerprint e diferenca estrutural, sem pergunta;
- parser nao importa OpenAI, Oracle, SQLAlchemy ou acesso a banco.

## Planner Generico De Comparacoes V2

- `lumina.comparison-planner/1.0` aprovado em 66 testes dedicados sem xfail;
- periodo, N periodos, entidade, N entidades, metrica e meta oficial;
- filtros compartilhados e especificos permanecem separados;
- ordem, baseline, calculos declarados e field origins sao preservados;
- alinhamento, granularidade e complexidade sao validados;
- tenant, permissoes, fontes, entidades e metas usam contexto confiavel;
- Oracle, metrica desconhecida, SQL em filtro e meta inventada sao bloqueados;
- feature flag, rollback legado e shadow mode sanitizado foram validados;
- 12 golden plans revisados e deterministas;
- pacote sem import de banco, Oracle ou OpenAI e sem SQL.

## Executor Universal De Comparacoes

- `lumina.comparison-executor/1.0` aprovado em 233 testes dedicados sem xfail;
- executa periodo, multi-periodo, entidade, multi-entidade, metrica, meta
  oficial e comparacoes compostas;
- preserva todos os operandos, ordem, filtros especificos, baseline e
  dimensoes;
- compila somente `SELECT` a partir de catalogo governado e valores em binds;
- bloqueia Oracle, SQL livre, fonte, metrica, dimensao e tenant nao autorizados;
- usa `Decimal`, arredondamento final e politica explicita para denominador
  zero, bucket ausente e null;
- limita queries, operandos, linhas, payload, concorrencia e tempo;
- produz validacao matematica, proveniencia, partial e fingerprints;
- integra Planner V2, orquestrador, AnalyticalResponseV2, V1 e sidecar;
- feature flag e shadow mode iniciam desligados;
- junho/julho no PostgreSQL descartavel resultou em `300,00`, `400,00`,
  delta `100,00` e `33,33%`, sem transferencia e sem tenant B;
- 15 golden results e cinco testes de desempenho foram aprovados.

## Apresentacao Comparativa

- `lumina.comparison-presentation/1.0` adapta V2 e V1 sem recalcular numeros;
- 14 testes de modelo e 24 testes de renderer aprovados nos quatro projetos;
- periodo, multi-periodo, entidade, multi-entidade, metrica, meta, meta ausente,
  area, pizza governada e multiplas visualizacoes foram renderizados;
- null, missing, zero, denominador zero, parcial, truncado, timeout e blocked
  permanecem estados distintos;
- tabela, cards, barras, linha, area, pizza, actual vs target e fallback seguro;
- Trust Center e metadados respeitam `ADMIN`, `GESTOR` e `CONSULTA`;
- CSV preserva valores brutos e exclui SQL, binds e credenciais;
- claro, escuro, desktop, tablet, mobile, ultrawide, teclado e fullscreen;
- feature flag e shadow mode iniciam desligados;
- golden presentation models e carga de 10 operandos/500 linhas aprovados;
- nenhuma formula financeira, dependencia, migration ou mudanca de lockfile.

## Estado Conversacional PostgreSQL

- contrato canonico `lumina.conversation-state/1.0`;
- PostgreSQL armazena sessoes, nos, snapshots, eventos e ledger de importacao;
- tenant e usuario autenticados compoem todas as leituras e mutacoes;
- `client_message_id` torna retry idempotente e rejeita conteudo divergente;
- `context_version` usa compare-and-swap, sem last-write-wins;
- parent e active head pertencem obrigatoriamente a mesma sessao;
- snapshots estruturados possuem checksum e nao armazenam dataset, SQL ou binds;
- conteudo permitido usa Fernet com versao de chave; SQL e segredos sao
  minimizados por redacao antes da persistencia;
- reset incrementa epoch, archive/reopen/expiration/delete respeitam estado;
- retention possui dry-run, lote, cutoff e purge por cascade;
- importacao JSON e explicita, dry-run por padrao, governada por flag e ledger;
- 16 golden states, quatro turnos, reinicio, duas instancias, 20 operacoes
  concorrentes, mil nos e paginacao foram aprovados;
- frontend mantem somente session ID, versao e parent em chave tenant+usuario;
- logout elimina todos os bindings e reset pela logo cria uma sessao nova;
- producao permanece `LEGACY_ONLY`; scheduler e importacao real ficam desligados;
- detalhes e evidencias: `PROMPT_08_POSTGRES_CONVERSATION_STATE_REPORT.md`.

## Xfails Estritos

- `LUMINA-GAP-DASH-001`: atualizacao visual local retorna
  `FULL_RENDERING`, nao `UI_MODIFIED`. Futuro dashboard V2.
- `LUMINA-GAP-TENANT-001`: core summary consulta `vw_vendas_lm` sem filtro
  `tenant_id`. Futuro gateway analitico isolado.

Foram removidos onze casos `xfail`: `VIS-001`, `VIS-002`, `COMP-001`, quatro
variacoes `COMP-002`, `ORCH-001`, `ORCH-002` e `CONTEXT-002`. Os dez casos
anteriores ao Prompt 09 possuem teste regular aprovado.
`LUMINA-GAP-CONTEXT-001` foi substituido por teste regular do motor
`lumina.context-resolution/1.0`, cuja execucao PostgreSQL desta etapa ficou
pendente pelas restricoes locais registradas abaixo. Permanecem somente
`DASH-001` e `TENANT-001`.

## Evidencias De Contencao

- sem `TEST_DATABASE_URL`: coleta recusada;
- `127.0.0.1:5432`: coleta recusada;
- `ENVIRONMENT=development`: reset recusado;
- senha nao apareceu nas mensagens;
- subprocessos provaram que pytest direto tambem carrega a guarda;
- teste conectado confirmou banco, endereco e porta do servidor;
- bloqueio de rede ficou ativo durante toda a sessao.

## Classificacao Das Falhas Encontradas

- ambiente antigo: corrigido;
- fixtures: corrigidas;
- dependencias externas: substituidas por mocks;
- compatibilidade de testes: corrigida;
- bugs introduzidos nesta tarefa: nenhum remanescente;
- bugs funcionais preexistentes: 2 casos visiveis como `xfail(strict=True)`.

## Comandos Executados

```powershell
.\scripts\run-backend-tests-safe.ps1 --selection all -q --tb=short
cd frontend
npm run lint
npx tsc --noEmit
npm run build
npm run test:visual
```

Tambem foram executadas selecoes de guarda, baseline, multitenancy, mocks e
integracao. Consulte [`docs/testing/README.md`](../testing/README.md) para
reproducao.

## Proxima Etapa

Executar `Prompt 10 - Base de Conhecimento Empresarial`,
preservando:

1. `lumina.temporal.pt-BR/1.0` como autoridade de datas;
2. contrato plural de periodos;
3. `lumina.comparison-planner/1.0` como autoridade de planejamento;
4. compatibilidade V1/V2 e sidecar;
5. isolamento fail-closed dos testes;
6. quatro gaps futuros sem mascaramento;
7. `lumina.comparison-executor/1.0` como unica autoridade numerica comparativa;
8. `lumina.comparison-presentation/1.0` como camada somente de apresentacao.

## Incremento Prompt 09

- contrato `lumina.context-resolution/1.0`;
- heranca deterministica por campo, sem concatenacao textual no caminho V2;
- quatro turnos: junho/Centro, julho, comparacao e produto;
- patch discriminado, checksums e idempotencia;
- snapshot do parent para branch e CAS por epoch/versao;
- reset total avanca epoch apenas na conclusao;
- negacao, correcao, remocao, conflito e mudanca de assunto fail-closed;
- resumo publico e diagnostico tecnico restrito a `ADMIN`;
- 2 xfails estritos remanescentes: `DASH-001` e `TENANT-001`;
- AST dos arquivos Python alterados aprovado;
- frontend ESLint e TypeScript aprovados;
- 7 cenarios Playwright desktop produziram `ok`; o comando excedeu o timeout
  apenas durante encerramento do webserver, sem porta 3100 remanescente;
- build frontend bloqueado exclusivamente pelo acesso externo as fontes Google;
- pytest/PostgreSQL descartavel nao executado nesta sandbox porque o named pipe
  Docker retornou acesso negado e o Python 3.12 do host nao e executavel pela
  sandbox. As suites e fixtures foram adicionadas, sem declarar aprovacao.

## Certificacao Prompt 09.1 - 2026-07-28

As limitacoes registradas no incremento original foram resolvidas em uma nova
sessao de certificacao, sem apagar a evidencia historica anterior.

| Verificacao | Resultado certificado |
|---|---:|
| Backend coletado | 1080 |
| Backend passed | 1078 |
| Backend failed | 0 |
| Backend xfailed | 2 |
| Backend XPASS | 0 |
| Duracao backend | 719.95 s |
| Prompt 09 direcionado | 88 passed |
| Estado/concorrencia/PostgreSQL | 28 passed |
| Contratos/schemas/goldens focalizados | 43 passed |
| Playwright | 196 passed, exit code 0 |

Os dois xfails continuam exatamente:

- `LUMINA-GAP-DASH-001`;
- `LUMINA-GAP-TENANT-001`.

`LUMINA-GAP-CONTEXT-001` passou como teste regular. O cenario de quatro turnos
tambem passou integrado ao PostgreSQL, produzindo quatro snapshots, versoes
`1, 2, 3, 4`, faturamento e filial Centro herdados, junho/julho ordenados,
comparacao ativa e dimensao produto no estado final.

Validacoes complementares:

- PostgreSQL 16 Alpine descartavel em `127.0.0.1:55432/luminaai_test`;
- CAS, concorrencia, replay, restart, duas instancias, branches, cross-tenant,
  cross-user, parent invalido, reset e falha tecnica aprovados;
- cinco schemas exportados duas vezes com hashes identicos e sem diff;
- 18 golden transitions validas;
- OpenAPI com 83 paths, dos quais 6 conversacionais, e campos novos aditivos;
- ESLint, TypeScript e build Next.js aprovados;
- Playwright completo aprovado em quatro viewports e webserver encerrado;
- AST de 382 arquivos Python aprovado;
- Oracle, OpenAI e banco operacional nao acessados;
- nenhuma migration, dependencia ou lockfile alterado;
- portas `55432`, `3100`, `3002` e `8000` fechadas ao final.

## Certificacao Prompt 10 - 2026-07-29

Foi adicionada a Base de Conhecimento Empresarial Governada
`lumina.enterprise-knowledge/1.0`, com migration v13, contratos tipados,
workflow humano, publicacao imutavel, busca lexical, binding ao
`MetricRegistry`, runtime publicado, API V2 e frontend governado.

| Verificacao | Resultado certificado |
|---|---:|
| Backend coletado | 1112 |
| Backend passed | 1110 |
| Backend failed | 0 |
| Backend xfailed | 2 |
| Backend XPASS | 0 |
| Duracao backend | 646,49 s |
| Prompt 10 direcionado | 32 passed |
| Migration v12/v13 em cadeia | 3 passed |
| Benchmark estrutural | 1 passed; workload 0,08 s |
| Playwright | 204 passed, exit code 0 |
| ESLint | aprovado |
| TypeScript | aprovado |
| Build Next.js | aprovado |
| AST | 410 arquivos, 0 falhas |

Os dois xfails continuam exatamente:

- `LUMINA-GAP-DASH-001`;
- `LUMINA-GAP-TENANT-001`.

Validacoes adicionais:

- 18 goldens de Knowledge deterministicos;
- 18 schemas exportados duas vezes, 13 novos, com hashes identicos;
- OpenAPI aditivo com 104 paths, 120 operacoes e 21 paths Knowledge;
- PostgreSQL descartavel guardado em `127.0.0.1:55432/luminaai_test`;
- migration `up -> up -> down -> up` e cadeia `v13 -> v12 -> v12 -> v13`;
- 1.000 assets, 10.000 versoes, 100 aliases, fila, keyset e cache em teste;
- Oracle, OpenAI e banco operacional nao acessados;
- nenhuma dependencia ou lockfile alterado;
- producao preservada em `LEGACY_ONLY`;
- blueprint legado restaurado ao hash pre-teste;
- container, network, volume e portas de teste removidos ao final.

Proxima etapa: `Prompt 11 - Perfil analitico e memoria governada do usuario`.

## Certificacao Prompt 11 - 2026-07-29

Foi adicionado o perfil analitico governado
`lumina.user-analytical-profile/1.0`, com contratos, consentimento, precedencia,
CAS, checksum, repository PostgreSQL, migration v14, API propria, frontend,
transparencia no chat e politicas de privacidade.

| Verificacao | Resultado certificado |
|---|---:|
| Backend coletado | 1142 |
| Backend passed | 1140 |
| Backend failed | 0 |
| Backend xfailed | 2 |
| Backend XPASS | 0 |
| Duracao backend | 936,79 s |
| Prompt 11 direcionado | 30 passed |
| Cadeia de migrations v12/v13/v14 | 5 passed |
| Playwright | 232 passed, exit code 0 |
| ESLint | aprovado |
| TypeScript | aprovado |
| Build Next.js | aprovado, 17 paginas |
| AST | 427 arquivos, 0 falhas |

Os dois xfails continuam exatamente:

- `LUMINA-GAP-DASH-001`;
- `LUMINA-GAP-TENANT-001`.

Validacoes adicionais:

- cenario de quatro turnos com profile aprovado como teste regular;
- 19 goldens do perfil aprovados;
- 41 schemas exportados duas vezes com hashes identicos;
- OpenAPI aditivo com 120 paths e 141 operacoes, reproduzivel;
- migration `v14 -> v13 -> v12 -> v12 -> v13 -> v14` e
  `v14 up -> up -> down -> up`;
- CAS concorrente, consentimento, revogacao, retencao, exportacao, exclusao,
  IDOR, cross-user e cross-tenant aprovados;
- frontend do perfil aprovado em desktop, tablet, mobile e ultrawide;
- Oracle, OpenAI e banco operacional nao acessados;
- nenhuma dependencia ou lockfile alterado;
- producao preservada em `LEGACY_ONLY`;
- blueprint legado restaurado ao hash pre-teste.

Proxima etapa: `Prompt 12 - Feedback governado e aprendizado supervisionado`.

## Certificacao Prompt 12 - 2026-07-29

Foi adicionado o feedback humano governado
`lumina.supervised-feedback/1.0`, com contratos estritos, redacao
deterministica, triagem, lifecycle, revisao humana, curadoria, datasets
imutaveis, exportacao offline, auditoria e retencao.

| Verificacao | Resultado certificado |
|---|---:|
| Backend coletado | 1241 |
| Backend passed | 1239 |
| Backend failed | 0 |
| Backend xfailed | 2 |
| Backend XPASS | 0 |
| Duracao backend | 932,73 s |
| Prompt 12 direcionado | 99 passed |
| Benchmark estrutural | triagem, redacao, manifest e cache em workloads de 10.000 itens |
| Playwright | 256 passed, exit code 0 |
| ESLint | aprovado |
| TypeScript | aprovado |
| Build Next.js | aprovado, 19 paginas |
| AST | 456 arquivos, 0 falhas |

Os dois xfails continuam exatamente:

- `LUMINA-GAP-DASH-001`;
- `LUMINA-GAP-TENANT-001`.

Validacoes adicionais:

- 21 goldens de triagem deterministica aprovados;
- 69 schemas totais e 28 do Prompt 12 exportados duas vezes com hashes
  identicos;
- OpenAPI com 149 paths e 173 operacoes, incluindo 29 paths e 32 operacoes
  de feedback supervisionado;
- migration `v15 up -> up -> down -> up` e cadeia
  `v15 -> v14 -> v13 -> v12`;
- target de feedback validado contra resposta persistida, tenant, usuario,
  sessao e checksum;
- idempotencia, CAS, IDOR, cross-user, cross-tenant, separacao de funcoes,
  redacao, CSV injection, shadow nao persistente, import dry-run, retencao,
  streaming e exclusao foram aprovados;
- frontend aprovado em desktop, tablet, mobile e ultrawide;
- Oracle, OpenAI e banco operacional nao acessados;
- nenhuma dependencia ou lockfile alterado;
- producao preservada em `LEGACY_ONLY`, com flags desligadas.

Proxima etapa: `Prompt 13 - Consumo offline de datasets supervisionados
explicitamente aprovados`.

## Certificação Consolidada Prompts 14–17 — 2026-08-04

Esta seção acrescenta a revalidação atual sem apagar ou reinterpretar o
histórico acima.

### Evidência histórica

- Prompt 13: `HISTORICAL_CERTIFIED` com 1.279 passed, 2 xfailed, zero failed e
  zero XPASS.
- Prompt 14: relatório original sem contagem backend completa;
  `HISTORICAL_EVIDENCE_UNAVAILABLE` para a quantidade integral.
- Prompt 15: relatório original registra 10 testes direcionados, não uma suíte
  completa.
- Prompt 16: relatório original registra 1.307 passed e 1 xfailed. O número
  externo 1.327 não possui log oficial preservado e não é adotado como fato.
- Prompt 17: `HISTORICAL_CERTIFIED` com 1.345 passed, 1 xfailed, zero failed e
  zero XPASS.

### Baseline consolidada atual

| Validação | Resultado |
|---|---:|
| Coleta | 1.349 testes; 0 erros |
| Backend completo | 1.348 passed |
| Failed | 0 |
| Xfailed | 1 |
| XPASS | 0 |
| Warnings | 2 |
| Duração | 1.248,40 s |
| Único xfail | `LUMINA-GAP-DASH-001` |
| Playwright | 260 passed; 4 viewports; exit 0 |
| AST | 641 analisados; 0 erros |
| OpenAPI | 190 paths; 216 operações |

`LUMINA-GAP-TENANT-001` é teste regular aprovado desde a correção do core
summary. A revalidação isolada de
`test_safe_baseline_database.py::test_core_summary_breakdown_does_not_mix_tenants`
passou, sem xfail ou skip, com tenant derivado dos binds confiáveis.

### Componentes e migrations

- Prompt 14: `lumina.ai-tool-registry/1.0`, migration v17, 17 testes
  direcionados atuais aprovados.
- Prompt 15: `lumina.safe-analytical-postgresql/1.0`, migration v18, 250 testes
  direcionados atuais aprovados.
- Prompt 16: `lumina.ai-orchestration/1.0`, migration v19, 20 testes
  direcionados atuais aprovados.
- Prompt 17: `lumina.validation-provenance/1.0`, migration v20, 17 testes
  direcionados atuais aprovados.
- Cadeia v20→v12→v20 e dupla execução idempotente de v17–v20 aprovadas.
- Migration v21 não foi importada nem executada; zero tabelas Prompt 18.

### Reprodutibilidade e frontend

- 93 schemas JSON existentes; 6 do exporter oficial do Prompt 17.
- 13 goldens JSON existentes; 2 do exporter oficial do Prompt 17.
- Schemas, goldens e OpenAPI exportados duas vezes sem diferença.
- Hash schemas: `f2561ac639e85ed21e13c74f56d1ad93ec90cbcccad87c9d8f540cb789094ada`.
- Hash goldens: `3058d508844c15796d8d3316a983675f1ea6afeea229ca7780e1ece332034ba9`.
- Hash lógico OpenAPI:
  `cec948f1b6a9ddcec538eea7a6fd5615905dc03967752aa70cdd351431c02552`.
- ESLint exit 0 com 8 warnings preexistentes; TypeScript e build aprovados.
- Build: 23 páginas geradas e 21 rotas listadas.
- Prompt 18 em `LEGACY_ONLY`: nenhuma rota backend ou página frontend ativa.

### Segurança e fingerprint

- PostgreSQL descartável: `127.0.0.1:55432/luminaai_test`.
- OpenAI real, Oracle runtime e banco operacional: zero acessos.
- Dependências e lockfiles preservados; zero segredo real no escopo permitido.
- Produção permanece `LEGACY_ONLY` para os componentes governados.
- Branch: `codex/phase-ai-orchestration-prompts-14-18`.
- Checkpoint: `c5d7621f2b7b3c4c0138a704685ac048515f49db`.
- Hash do diff rastreado:
  `c1195ce3e0cf3be9a28f0e1f4d6baeb529ee91b1`.
- Manifesto não rastreado permitido:
  `598d95dd1a2bfe3127d649b14ff497e9c030cffacd4e43cb232c7a730cf2c617`.

O fingerprint foi obtido antes da escrita da reconciliação documental e não
inclui os próprios relatórios. Os arquivos protegidos terminaram com seus
hashes iniciais; em particular, `backend/services/blueprints.json` foi
restaurado para
`407D5C65B7A38A805C073F064A0C1CD9AF6290C8BCBE18809CA645CD81042596`
após a suíte legada gravar dados sintéticos temporários.

Detalhes e inventário:
`docs/audit/PHASE_14_17_CONSOLIDATED_CERTIFICATION_EVIDENCE.md`.

## Baseline Prompt 21 — 2026-08-05

Esta seção adiciona a certificação atual sem apagar as baselines históricas.

| Validação | Resultado |
|---|---:|
| Backend completo | 1.694 passed |
| Failed / errors / skipped | 0 / 0 / 0 |
| Xfailed / XPASS | 0 / 0 |
| Warnings backend | 2 depreciações Pydantic preexistentes |
| Duração backend | 1.186,89 s |
| Prompts 19/20 + TENANT-001 + DASH-001 + Prompt 21 dirigidos | 278 passed |
| Playwright | 372 passed em 607,1 s |
| Viewports | desktop, tablet, mobile e ultrawide |
| ESLint | exit 0; 8 warnings preexistentes |
| TypeScript | exit 0 |
| Build Next.js | exit 0; 24 tarefas de página; 4 rotas V2 dinâmicas |
| AST Python próprio | 704 arquivos; 0 erros |
| Docker config | exit 0 |

OpenAPI foi gerada em processos independentes duas vezes por modo:

- default `LEGACY_ONLY`: 190 paths, 216 operações,
  `e13d88b46e1a546725fe629ac797f8e0d489ff2f82cd8009e20ae37ff8fcaf25`;
- experimental Prompt 20: 212 paths, 243 operações,
  `724116d02bb5b5062be4ccd37ec30216982de541db8acec816be52b04b26411d`.

As contagens de paths/operações permanecem iguais ao Prompt 20. Os hashes
mudaram porque `POST /api/v1/query/` recebeu schemas opcionais de contexto/ação
do side chat; nenhum endpoint foi adicionado pelo Prompt 21.

`LUMINA-GAP-DASH-001` agora é teste regular: a correção copia o dashboard state
histórico, aplica visual-only update e retorna `UI_MODIFIED`; mudança semântica,
dataset não certificado e estado ausente falham fechado. O hash inicial/final de
`backend/services/blueprints.json` é
`407D5C65B7A38A805C073F064A0C1CD9AF6290C8BCBE18809CA645CD81042596`.

Produção continua `LEGACY_ONLY`. A prova separada confirmou 404, Sidebar sem
link e zero request V2 nesse modo. OpenAI real, Oracle, banco operacional, porta
5432, provider e rede externa tiveram zero acesso. Nenhuma migration v23,
dependência ou alteração de lockfile foi criada.

## Prompt 22.1 — Estabilização de Timing e Certificação Final (2026-08-06)

Esta seção estende a baseline do Prompt 22 com os resultados oficiais da estabilização de timing e duas rodadas integrais consecutivas com 0 falhas, 0 erros e 0 skips.

| Validação | Resultado |
|---|---:|
| Backend integral (Rodada 1) | 1774 passed em 1258.84 s (0:20:58) |
| Backend integral (Rodada 2) | 1774 passed em 1385.47 s (0:23:05) |
| Failed / errors / skipped | 0 / 0 / 0 em ambas as rodadas |
| Xfailed / XPASS | 0 / 0 em ambas as rodadas |
| Warnings backend | 2 depreciações Pydantic preexistentes sobre `min_items` |
| Playwright visual (Rodada 1) | 392 passed (10.8 m) |
| Playwright visual (Rodada 2) | 392 passed (10.4 m) |
| Playwright failed / skipped | 0 / 0 em ambas as rodadas |
| Viewports Playwright | desktop, tablet, mobile e ultrawide |
| ESLint | exit 0; 8 warnings preexistentes |
| TypeScript (`npx tsc --noEmit`) | exit 0 |
| Build Next.js | exit 0; 25 páginas geradas |
| AST Python próprio | 100% OK |
| Docker config | exit 0 (`docker-compose.test.yml`) |
| SHA256 `blueprints.json` | `407D5C65B7A38A805C073F064A0C1CD9AF6290C8BCBE18809CA645CD81042596` |
| OpenAPI DEFAULT | 190 paths, 216 operações, 0 paths Prompt 22 |
| OpenAPI EXPERIMENTAL | 223 paths, 255 operações, 11 paths Prompt 22 |

As duas flutuações temporais preexistentes foram eliminadas deterministicamente sem mascarar ou desabilitar testes:
1. `test_thousand_nodes_append_and_keyset_pagination_remain_bounded`: reduzido de 40,32 s sob carga para **0,81 s** no backend repository.
2. `cancelled and stale side-chat responses`: manipuladores de rotas limpos sob `abort` e `close`, eliminando o bloqueio de workers no Playwright.
3. Rollback da v12 em `test_dashboard_ai_assistance_v2_migration_chain`: tratado com segurança sem alterar arquivos de migrações históricas.

Decisão de Checkpoint para os Prompts 19–22: **AUTORIZADO**.
