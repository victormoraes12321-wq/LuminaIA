# Prompt 20 — Backend Governado de Dashboards — Relatório de Certificação

Data da certificação: 2026-08-05. Contrato:
`lumina.dashboard-backend/1.0`. Este relatório certifica somente o backend
governado e seu rollout fail-closed. Não autoriza migration, ativação ou rollout
produtivo e não implementa o Prompt 21 ou o Prompt 22.

1. **Status:** APROVADO após correções de isolamento e regressão integral verde.
2. **Trava de entrada:** branch, HEAD, índice e hash protegido confirmados; a retomada ocorreu sobre worktree já iniciado, sem reverter mudanças locais.
3. **Branch:** `codex/phase-dashboard-prompts-19-22`, preservada.
4. **HEAD:** `14e13bc886372690d144addc255c1ec60d59e62a`, preservado.
5. **Auditoria legado:** confirmou Dashboard Studio, models/repositories legados, `BlueprintStorage`, storage JSON, permissões, runtime, cache, query execution e consumidores existentes.
6. **Arquivos criados:** package de contratos, 13 models, migration v22, router, package de serviços, 8 testes, golden, schemas, tipos TypeScript, exportador, rehearsal, contrato, runbook, ADR e este relatório.
7. **Arquivos alterados:** configuração, montagem condicional da aplicação, exports de models, bootstrap seguro de testes e documentação governada; arquivos protegidos preexistentes foram preservados.
8. **Versão:** `lumina.dashboard-backend/1.0` em contratos, models, APIs, runtime, auditoria, schemas e documentação.
9. **Contracts:** 55 schemas Pydantic v2 exportados, estritos, `extra=forbid`, tipos fechados e `Decimal` para valores financeiros.
10. **Lifecycle:** estados do Blueprint V2 preservados: DRAFT, IN_REVIEW, APPROVED, PUBLISHED, SUPERSEDED, DEPRECATED, ARCHIVED e REJECTED.
11. **State machine:** tabela estática; transições livres vindas do payload são recusadas.
12. **Ownership:** server-controlled com USER, TEAM, TENANT e SYSTEM_TEMPLATE; payload não transfere autoridade.
13. **Collaborators:** VIEWER, EDITOR_VISUAL, EDITOR_SEMANTIC, REVIEWER, PUBLISHER e ADMINISTRATOR, sempre tenant-scoped.
14. **Access policy:** RBAC global é intersectado com owner, collaborator, classification, lifecycle e policy; collaborator nunca eleva RBAC.
15. **Revisions:** rows imutáveis com parent, números visual/semântico, canonical JSON, checksums, validação, autor, motivo, origem e lock.
16. **Visual revision:** incrementa somente a versão visual e preserva semantic checksum.
17. **Semantic revision:** incrementa versão semântica, exige revalidação e invalida approval anterior.
18. **Visual patch:** aplica allowlist em cópia, valida checksum/CAS e bloqueia mudança semântica.
19. **Semantic patch:** exige `requires_revalidation`, mudança semântica real, nova revisão e retorno do head a DRAFT.
20. **Validation:** reutiliza validator e canonicalizer oficiais de `lumina.dashboard-blueprint/2.0`.
21. **Review:** submit, changes requested e reject são decisões humanas append-only vinculadas a revisão.
22. **Approval:** exige reviewer autorizado, diferente do autor, e checksum exato da revisão.
23. **Publication:** explícita, confirmada, idempotente, posterior a approval válido e criada como registro imutável.
24. **Active publication:** ponteiro único por tenant/dashboard, trocado atomicamente por CAS de generation.
25. **Supersession:** publicação anterior é referenciada e preservada; nenhuma linha histórica é mutada.
26. **Rollback:** cria nova publication para revisão histórica compatível e incrementa generation.
27. **Archive:** usa CAS, preserva histórico e bloqueia runtime.
28. **Clone:** cria nova identidade DRAFT e owner autenticado sem collaborators, publications, approvals ou audit antigo.
29. **CAS:** aplicado a metadata, head, review, approval, active publication, collaborators, rollback e archive.
30. **Idempotência:** tenant/user/operation/resource/key/payload checksum; replay igual reutiliza, conteúdo diferente conflita.
31. **Runtime request:** tipada, limitada, sem tenant, SQL, owner, role, permission ou identificador físico.
32. **Runtime plan:** contém publication/revision/checksum, scope, filtros, período, limites, dependências, grupos e deadline; nunca SQL.
33. **Widget plans:** IDs canônicos, shape, métricas, dimensões, entidades, período, filtros, classification, permission, freshness e checksum.
34. **Execution groups:** agrupamento determinístico somente para planos semanticamente equivalentes e scopes compatíveis.
35. **Filters:** somente filtros publicados, tipos/seleções limitados, canonicalização e ausência obrigatória bloqueadora.
36. **Interactions:** somente ações e targets declarados; checksum, source, target, dimension e permission são validados.
37. **Widget results:** dados tipados, facts, certification, provenance, completeness, freshness, truncation, warnings e checksum.
38. **Partial:** COMPLETE, PARTIAL, BLOCKED e UNAVAILABLE são explícitos; erro nunca vira zero.
39. **Freshness:** propagada da autoridade analítica/cache/materialização e stale não é apresentado como atual.
40. **Provenance:** pública e sanitizada; não inclui SQL, binds, DSN, credenciais, tenant proof ou trace interno.
41. **Safe PostgreSQL integration:** runtime resolve query spec governada e delega compilação/execução à autoridade existente.
42. **Validation integration:** certificação e facts vêm de Validation & Provenance, não do dashboard backend.
43. **Smart Cache integration:** lookup/write reutilizam pipeline governado com permission/classification/freshness preservados.
44. **Materialization integration:** somente snapshot publicado, FRESH, VALID e íntegro pode ser reutilizado.
45. **MetricRegistry integration:** metric IDs e fingerprints são consumidos; nenhuma fórmula foi duplicada ou alterada.
46. **Classification:** ceiling efetivo é fail-closed e não pode sofrer downgrade.
47. **Permissions:** resolvidas a cada operação; remoção de grant impede reutilização de acesso/cache.
48. **Repositories:** seis autoridades tenant-scoped cobrem dashboard, revisions/review, publication, access, audit e runtime/evaluation.
49. **Services:** lifecycle, authoring, revision/patch, review, publication/rollback, access/clone, planning/execution/widget, audit, backup e evaluation são separados.
50. **APIs authoring:** create/list/detail/update/clone/archive versionadas sob `/api/v2/dashboards`.
51. **APIs revisions:** list/detail/create/compare e patches visual/semantic.
52. **APIs review:** submit, approve e reject.
53. **APIs publication:** publish, history, active publication e rollback.
54. **APIs access:** list/add/update/remove collaborators.
55. **APIs runtime:** plan, execute e provenance.
56. **APIs audit:** timeline tenant-scoped com acesso governado.
57. **Errors:** códigos tipados, status HTTP estável e inexistência cross-tenant não revelada.
58. **RBAC:** capabilities server-controlled; blueprint declara requisito, nunca grant.
59. **CONSULTA:** view/execute de publication autorizada e provenance pública; sem authoring/publication/admin.
60. **GESTOR:** create, visual/semantic edit por policy, review, clone e audit limitada; publish não é default.
61. **ADMIN:** review, approve, publish, rollback, archive, collaborator management e audit conforme permission.
62. **Audit events:** append-only, tenant-scoped e sem SQL, binds, credenciais ou resultados empresariais completos.
63. **Observability:** métricas somente estruturais de lifecycle, conflito, runtime, widgets, cache, materialização e rollout.
64. **Feature modes:** enum centralizado e validado pela configuração.
65. **LEGACY_ONLY:** default; router V2 e handler V2 ausentes, zero persistência/runtime V2 produtivos.
66. **SHADOW_VALIDATE:** valida adaptação em memória, sem persistir, publicar ou executar V2.
67. **V2_AUTHORING:** authoring somente para tenant allowlisted e flags explícitas.
68. **V2_PUBLISHED_READ:** leitura governada, ainda sem autorização automática de execução.
69. **V2_RUNTIME:** execução exige modo, flags, allowlist e aprovação operacional.
70. **Legacy dry-run:** adapter existente gera proposta/warnings sem escrever `blueprints.json`.
71. **Migration v22:** `migration_v22_0.py`, aditiva, explícita, idempotente, guarded e com down test-only.
72. **Tabelas v22:** 13 tabelas justificadas para identidade, history, access, audit, runtime e evaluation.
73. **Constraints:** tenant composite FKs, checks, uniqueness, revision/publication ownership e referências de approval.
74. **Índices:** tenant/dashboard, lifecycle, owner, checksums, publication, collaborator, audit, runtime, status, idempotency e evaluation.
75. **v22 up:** aprovado no PostgreSQL descartável.
76. **v22 idempotência:** segundo up aprovado.
77. **v22 down:** aprovado somente com confirmação test-only.
78. **Cadeia v22–v12:** v22 até v13 down, preservando v12 como baseline, aprovada.
79. **Cadeia v12–v22:** v13 até v22 up aprovada.
80. **Migrations históricas:** v12–v21 não foram alteradas; regressão da v12 passou após cleanup da fixture v22.
81. **Backup:** `pg_dump` custom/data-only/no-owner/no-privileges apenas das 13 tabelas e fixtures sintéticas.
82. **Restore:** v22 down/up e `pg_restore --disable-triggers` no container descartável, seguido de validação.
83. **Backup checksums:** manifesto antes/depois `65671b1ac442e5de5b24925219158a55c73d5d1a7f1b0471dc79fc9545a9505b`; active pointer também idêntico.
84. **Cenário draft:** owner autenticado, DRAFT, blueprint/checksums e audit aprovados.
85. **Cenário visual patch:** nova revisão visual e semantic checksum preservado.
86. **Cenário semantic patch:** nova revisão semântica, revalidação, DRAFT e approval invalidado.
87. **Cenário stale revision:** um CAS vence e o stale recebe conflito tipado.
88. **Cenário review:** DRAFT para IN_REVIEW aprovado.
89. **Cenário approve:** reviewer independente move head para APPROVED.
90. **Cenário publish sem approval:** bloqueado.
91. **Cenário publication:** registro imutável, ponteiro ativo, generation e audit aprovados.
92. **Cenário supersession:** nova publication preserva e referencia a anterior.
93. **Cenário concurrent publication:** CAS mantém uma única active publication.
94. **Cenário rollback:** nova publication criada para revisão anterior, sem reativar linha histórica.
95. **Cenário archive:** runtime bloqueado e history preservada.
96. **Cenário clone:** nova identidade/owner, sem authority herdada.
97. **Cenário collaborators:** visual e semantic roles respeitam limites; publish exige capability própria.
98. **Cenário runtime unpublished:** bloqueado.
99. **Cenário runtime published:** plano e widgets tipados aprovados.
100. **Cenário faturamento junho:** fixture sintética `Decimal('300.00')`, certification e shape SCALAR.
101. **Cenário faturamento julho:** golden sintético preserva `400` como resultado da autoridade.
102. **Cenário comparação:** golden sintético preserva delta 100 e percentual +33,33% já calculados pela autoridade.
103. **Cenário total vs média:** metric IDs distintos permanecem distintos.
104. **Cenário ranking:** shape RANKING, completeness e truncation explícitos.
105. **Cenário contas abertas:** classification/permission governadas.
106. **Cenário estoque:** freshness explícita.
107. **Cenário cache hit:** evita nova execução e preserva certification.
108. **Cenário visual cache:** semantic checksum idêntico permite reutilização analítica.
109. **Cenário semantic invalidation:** mudança semântica altera fingerprint e invalida.
110. **Cenário materialization:** hit somente em snapshot publicado/fresh/valid.
111. **Cenário stale:** warning explícito ou miss; nunca atualidade falsa.
112. **Cenário widget failure:** PARTIAL preserva widgets certificados quando policy permite.
113. **Cenário tenant failure:** dashboard inteiro bloqueado.
114. **Cenário filter invalid:** rejeitado antes da execução.
115. **Cenário injection:** payload SQL/HTML/JS e campos desconhecidos bloqueados; nenhuma execução.
116. **Cenário cross-filter:** somente interação declarada é aceita.
117. **Cenário drilldown:** hierarchy/target/checksum/permission validados.
118. **Cenário execution grouping:** equivalência compartilha grupo sem alterar facts ou shape.
119. **Cenário quatro turnos:** estado já resolvido vira IDs/períodos canônicos; texto conversacional não entra no blueprint.
120. **Cenário aliases:** aliases canônicos preservam semantic checksum e runtime plan.
121. **Cenário backup/restore:** fixtures, counts, checksums, active pointer, constraints e índices idênticos.
122. **Cenário legacy dry-run:** proposta e warnings, sem persistência/publication/query.
123. **Cenário shadow:** validação estrutural, sem writes.
124. **Cenário LEGACY_ONLY:** router/handler V2 não carregados e zero comportamento V2 produtivo.
125. **Cenário duas réplicas:** CAS/idempotency impedem active publication ou revision duplicada indevida.
126. **Testes criados:** 8 arquivos Prompt 20 mais golden sintético e rehearsal de backup.
127. **Testes dirigidos:** 255 passed em 81,31 s.
128. **Backend collected:** 1677 casos.
129. **Backend passed:** 1676.
130. **Backend failed:** 0 na execução final.
131. **Backend errors:** 0.
132. **Backend skipped:** 0.
133. **Xfailed:** 1.
134. **XPASS:** 0.
135. **Único xfail:** `LUMINA-GAP-DASH-001`, razão/assertion preservadas.
136. **Warnings:** 2 Pydantic `min_items` preexistentes; ESLint 8 warnings preexistentes e zero erro.
137. **Duração:** backend 1217,51 s (20m17s), dirigidos 81,31 s e Playwright 8,6 min.
138. **Schemas:** 55 contratos; SHA-256 `DA38BFB943258E9E50F1C909A654EA845CD5496026EBDD75A26030476135B9A0`.
139. **Goldens:** 24 casos; SHA-256 `358260EAD1F7BE1FE927F165BDA0E736B2212521C843353A34AECB11DB97EC71`.
140. **OpenAPI paths:** default 190; experimental 212.
141. **OpenAPI operações:** default 216; experimental 243.
142. **Novos paths:** 22 somente quando flags explícitas habilitam o router.
143. **Novas operações:** 27.
144. **OpenAPI hashes:** default `0cf1a1d52fab2ae3cf4a883657c4a111f443e4e19072f34f8f02b50afbc163dd`; experimental `80ec5583c29dc1a478e8ce7fb1027eea546ad2c5a45960f77e094756750d7845`; duas runs idênticas.
145. **Frontend types:** `frontend/types/dashboard_backend_v2.ts`, sem cliente produtivo.
146. **Frontend pages:** nenhuma página Prompt 20.
147. **Sidebar:** inalterada pelo Prompt 20.
148. **ESLint:** exit 0, 8 warnings preexistentes.
149. **TypeScript:** `npx tsc --noEmit`, exit 0.
150. **Build:** Next 16 exit 0, 23 páginas geradas.
151. **Playwright:** 260 passed em 8,6 min.
152. **Viewports:** desktop, tablet, mobile e ultrawide na porta isolada 3100.
153. **AST:** 702 arquivos Python próprios, zero erros.
154. **Docker config:** exit 0.
155. **OpenAI real:** zero; mocks e bloqueio de rede do runner.
156. **Oracle:** zero no runtime/testes do Prompt 20.
157. **Banco operacional:** zero; somente `127.0.0.1:55432/luminaai_test`.
158. **Dependências:** nenhuma adicionada; requirements/package manifest inalterados.
159. **Lockfiles:** inalterados.
160. **Blueprints hash inicial:** `407D5C65B7A38A805C073F064A0C1CD9AF6290C8BCBE18809CA645CD81042596`.
161. **Blueprints hash final:** o mesmo valor, byte a byte preservado.
162. **Deprecation ledger:** legado permanece ACTIVE_LEGACY, com gates de rollout e dependências dos Prompts 21/22.
163. **Technical debt register:** frontend/renderer/editor/side chat/IA/migração legado/load/backup produtivo/scheduled refresh permanecem abertos.
164. **Baseline:** atualizado sem sobrescrever histórico.
165. **Documentação:** contrato, runbook, architecture, API reference, changelog, blueprint repository e AGENTS registram a autoridade V2.
166. **ADR:** 0023 aceita revisões/publicações/runtime governados, desabilitados por default.
167. **Portas:** 55432 e 3100 usadas somente nos ambientes isolados; 3002 e 8000 não foram iniciadas.
168. **Recursos descartáveis:** dump, container, network, tmpfs, `test-results` e `playwright-report` removidos; Docker Desktop iniciado para o ensaio foi encerrado.
169. **Índice Git:** permaneceu vazio; nenhum stage.
170. **Commits:** nenhum; HEAD preservado.
171. **Tags:** nenhuma criada; tag preexistente no HEAD preservada.
172. **Push:** nenhum; upstream não alterado.
173. **Produção:** inalterada e sem migration/rollout V2.
174. **Rollout:** bloqueado em `LEGACY_ONLY`; todas as flags V2 desligadas e allowlist vazia.
175. **Limitações:** sem frontend, renderer, editor, side chat, IA, migração automática de legado, backup produtivo ou load test; DASH-001 permanece.
176. **Prompt 21 — Interface de Dashboards e Side Chat:** AUTORIZADO somente como próxima tarefa explícita de implementação/teste, mantendo rollout produtivo bloqueado e sem resolver artificialmente DASH-001 fora do fluxo real.

## Incidentes de validação e correções

A primeira suíte integral terminou com 1672 passed, 1 xfailed e quatro falhas.
Uma falha era temporal sob carga concorrente do Playwright e passou isoladamente
sem mudança de código. Três eram regressões de isolamento do Prompt 20: o import
do handler V2 carregava serviços mesmo em `LEGACY_ONLY`, e a fixture PostgreSQL
deixava as tabelas v22 montadas antes do teste histórico de down da v12. O
handler passou a ser registrado somente junto com o router V2, e a fixture v22
agora executa down em `finally`. Os quatro casos afetados, a sequência v22→v12,
os 255 dirigidos e a suíte integral foram reexecutados com sucesso.

O `git diff --check` global continua reportando trailing whitespace apenas em
`runtime-logs/backend-network.err.log`, arquivo protegido e preexistente. Os
arquivos do Prompt 20 e as correções finais passam no check dirigido. Nenhum
arquivo protegido foi restaurado, formatado ou atribuído a esta tarefa.
