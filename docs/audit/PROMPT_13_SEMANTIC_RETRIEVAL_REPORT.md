# Prompt 13 - Semantic Retrieval E Entity Resolution

Data: 2026-07-30

Status: certificado em ambiente isolado.

1. **Resumo.** Implementado `lumina.semantic-retrieval/1.0` com indice publicado, retrieval deterministico e resolucao governada.
2. **Arquitetura.** O motor roda depois de contexto/perfil e antes do planner.
3. **Arquivos criados.** Contratos, models, migration v16, repository, services, router, frontend, testes, schemas, goldens, ADR e runbook.
4. **Arquivos alterados.** Integracoes, configuracao, query schema, navegacao, documentacao, exporter e testes de compatibilidade.
5. **Versao.** Contrato `lumina.semantic-retrieval/1.0`.
6. **Fronteiras de autoridade.** Knowledge define significado; MetricRegistry define metrica; executor define numeros.
7. **Contracts.** Models Pydantic estritos, frozen e `extra=forbid`.
8. **Document types.** Term, metric, KPI, dimension, entity, rule, alias, relation, approved example e system concept.
9. **Entity types.** Metric, dimension, concept e entidades empresariais tipadas.
10. **Data classification.** Public e tenant business metadata no indice padrao.
11. **Fontes permitidas.** Enterprise Knowledge publicada e MetricRegistry.
12. **Fontes proibidas.** Draft, feedback bruto, Oracle, OpenAI, SQL livre, resposta e banco operacional.
13. **Enterprise Knowledge indexing.** Somente versao publicada e vigente.
14. **Analytical entity indexing.** Contrato existe; flag inicia desligada.
15. **Dados pessoais.** Nao entram no indice padrao; restricted exige permission.
16. **Normalizacao.** NFKC, case fold, diacriticos, pontuacao, espacos, stopwords e trigramas.
17. **Tokens.** Tokens e significant tokens sao deterministas.
18. **Codigos.** Zeros a esquerda e separadores controlados sao preservados.
19. **Diacriticos.** `Sao Jose` e variante acentuada convergem.
20. **Aliases.** Apenas aliases publicados entram.
21. **Correspondencia canonica.** Canonical ID exato e o canal prioritario.
22. **Busca lexical.** Executada no PostgreSQL com conjunto limitado.
23. **Prefix.** Prefixo controlado possui canal proprio.
24. **Token overlap.** Jaccard deterministico.
25. **Character similarity.** Trigramas deterministas.
26. **Relation expansion.** Relacoes sao persistidas; expansao automatica fica conservadora e registrada como divida.
27. **Vector provider.** Feature hash local, nao neural.
28. **Provider utilizado.** `DETERMINISTIC_FEATURE_HASH`.
29. **Provider version.** `lumina.deterministic-feature-hash/1.0`.
30. **Deterministic feature hashing.** SHA-256 signed hashing.
31. **Dimensao.** 256 no runtime padrao; 64 no golden sintetico.
32. **Cosine similarity.** Limitada a candidatos e clamp deterministico.
33. **Ausencia de rede.** Provider declara e testa `network_required=false`.
34. **Ranking engine.** Maior identidade + boosts - penalidades.
35. **Ranking policy.** `lumina.semantic-ranking/1.0`.
36. **Score breakdown.** Completo para inspector; redigido para CONSULTA.
37. **Threshold policy.** `lumina.semantic-thresholds/1.0`.
38. **Minimum score.** Retrieval `0.30`; auto-resolution `0.72`.
39. **Ambiguity margin.** `0.08`.
40. **Maximum candidates.** 10 publicos e 100 internos.
41. **Resolved.** Exige score e margem.
42. **Ambiguous.** Empate/margem insuficiente gera opcoes.
43. **Unresolved.** Ausencia de candidato confiavel e explicita.
44. **Blocked.** Mencao nao resolvida bloqueia autoria V2.
45. **Mention extraction.** Deterministica; temporal fica fora.
46. **Entity resolution.** Tenant/user/permission scoped.
47. **Entity patch.** Tipado e com checksum.
48. **Filter field.** Resolvido pelo `filter_id` de origem.
49. **Filter value.** Resolvido separadamente, preservando operador e cardinalidade.
50. **Nomes iguais.** Permanecem ambiguous sem tipo/contexto suficiente.
51. **Tipo esperado.** Incompativeis sao eliminados antes do ranking.
52. **Domain compatibility.** Dominio explicito e fail-closed.
53. **Context compatibility.** Boost fraco; pedido atual prevalece.
54. **Profile tie-breaker.** Opt-in, consentido, fraco e na cache key.
55. **Canonical reference.** ID, tipo, label, tenant, dominio e fonte.
56. **Provenance.** Source type/id/version e index version preservados.
57. **Index definition.** Policies, provider, owner, active pointer e CAS.
58. **Index version.** Snapshot numerado e checksumado.
59. **Index lifecycle.** DRAFT/BUILDING/VALIDATING/READY/PUBLISHED/FAILED/DEPRECATED/ARCHIVED.
60. **Source manifest.** Source versions, checksums, tenant scope e watermark.
61. **Build.** Nova version, validacao, nunca auto-publica.
62. **Incremental build.** Contrato e flag existem; snapshot inicial ainda e recompilado.
63. **Watermark.** Preservado no manifest/version.
64. **Tombstone.** Delta provider ainda pendente e registrado.
65. **Snapshot consistency.** Fontes sao capturadas no instante do build.
66. **Build validation.** Conteudo, fonte, classificacao, provider, counts e checksum.
67. **Publication.** Explicita, transacional e com CAS.
68. **Immutability.** Trigger e services protegem published/deprecated/archive.
69. **Rollback.** Republica snapshot anterior e preserva historico.
70. **Stale source.** Detectada por version/checksum sem mutar published.
71. **Repository.** Todo metodo publico recebe tenant.
72. **Services.** Build, retrieval, resolution, clarification e evaluation separados.
73. **Cache.** Limitado, TTL curto, copia profunda, nao autoridade.
74. **Cache key.** Tenant, permission, version, policies, locale, query, tipo, dominio, contexto, perfil e top_k.
75. **Cache invalidation.** Publication e rollback invalidam tenant/index.
76. **Canonicalizer integration.** Patch canonico substitui apenas campos resolvidos.
77. **Intent integration.** Depois de contexto/perfil e antes do planner.
78. **Context integration.** Explicit precedence permanece no Context Resolution.
79. **Knowledge integration.** Fonte publicada, sem mutar lifecycle.
80. **Profile integration.** Somente desempate quando habilitado.
81. **Feedback integration.** Nao altera ranking automaticamente.
82. **MetricRegistry boundary.** Fornece IDs/metadados, nunca valores.
83. **Planner integration.** Recebe `QueryIntentV2` canonico.
84. **Executor boundary.** Nao importa nem consulta semantic retrieval.
85. **Clarification.** Persistida em PostgreSQL com escopo composto.
86. **Clarification token.** HMAC, expiracao, option membership e CAS.
87. **APIs runtime.** Capabilities, search, resolve, entity resolve, candidate detail e clarification.
88. **APIs admin.** Definition, versions, build, publish, rollback, deprecate, manifest, stale, inspector, eval, audit e observability.
89. **Errors.** Codigos `SEMANTIC_*` e `ENTITY_*` tipados.
90. **RBAC.** Matriz de permissions por ADMIN/GESTOR/CONSULTA.
91. **CONSULTA.** Search/resolve/public detail; sem vetor e breakdown interno.
92. **Index builder.** Permission explicita e idempotency hash tenant-scoped.
93. **Publisher.** Permission, READY, validation e CAS obrigatorios.
94. **Restricted entities.** Flag desligada e permission separada.
95. **Cross-tenant.** Not found/denial sem enumeracao.
96. **Cross-user.** Clarification e contexto exigem o mesmo usuario.
97. **Audit.** Eventos estruturais sem pergunta/dataset.
98. **Observability.** Contadores allowlisted.
99. **Feature modes.** LEGACY_ONLY, SHADOW, HYBRID_READ e V2_AUTHORITATIVE.
100. **Production default.** `LEGACY_ONLY`.
101. **Shadow mode.** Executa sem autoria.
102. **Hybrid mode.** Leitura V2 sem alterar intent.
103. **Frontend chat.** Clarification usa token antes de continuar.
104. **Frontend admin.** Versions, sources, evals, inspector e audit.
105. **Search inspector.** Tipo, dominio, candidates, score e channels.
106. **Accessibility.** Labels, headings, keyboard controls, alert e responsive.
107. **XSS protection.** HTML ativo e controles sao recusados.
108. **Stored prompt injection.** Padroes de instrucao e prompt sao bloqueados no build.
109. **Index poisoning.** Privacy/classification/allowlist/checksum reduzem poisoning.
110. **Vector poisoning.** Provider local e fontes governadas; sem vetor do cliente.
111. **Migration.** v16 explicita e aditiva.
112. **Migration up.** Executada no PostgreSQL descartavel.
113. **Migration idempotency.** Up repetido preserva schema.
114. **Migration down test-only.** Protegido por confirmacao e ambiente.
115. **Compatibility v16/v15/v14/v13/v12.** Ordem de downgrade/upgrade coberta.
116. **Constraints.** Escopo composto, lifecycle, checksum, JSON, counts, CAS e idempotency.
117. **Indices PostgreSQL.** Active, versions, labels, aliases, terms, relations, sources, eval e audit.
118. **Extension opcional.** Nenhuma extension obrigatoria.
119. **Fallback sem extension.** Feature hash e lexical usam bibliotecas existentes.
120. **Resultado exact canonical.** `faturamento_comercial` resolve deterministicamente.
121. **Resultado alias publicado.** `receita de vendas` resolve Faturamento.
122. **Resultado draft leakage.** Draft nao e fonte do provider.
123. **Resultado filial Centro.** Tipo BRANCH seleciona `branch.centro`.
124. **Resultado Centro ambiguo.** Sem tipo, branch e region exigem clarification.
125. **Resultado tipo esperado.** Metrica nao resolve como vendedor.
126. **Resultado codigo 00123.** Zero a esquerda preservado.
127. **Resultado erro de grafia.** Character similarity oferece candidato limitado.
128. **Resultado baixa confianca.** Fica unresolved/ambiguous conforme policy.
129. **Resultado alias ambiguo.** Nao escolhe primeiro.
130. **Resultado asset deprecated.** Documento deprecated e excluido.
131. **Resultado profile tie-breaker.** Peso fraco nao supera pedido explicito.
132. **Resultado feedback aprovado.** Nao entra sem provider/flag explicitos.
133. **Resultado dado restrito.** Bloqueado sem permission/policy.
134. **Resultado cross-tenant.** Outro tenant recebe NOT_FOUND.
135. **Resultado publicacao v1.** READY virou PUBLISHED com publication history.
136. **Resultado build v2.** Nova version, sem alterar runtime antes de publish.
137. **Resultado rollback.** v1 voltou ativa e historico foi preservado.
138. **Resultado source stale.** Versao da fonte alterada foi detectada read-only.
139. **Resultado quatro turnos.** Regressao conversacional permaneceu no baseline.
140. **Resultado quatro turnos com aliases.** Contexto continua autoridade; aliases sao resolvidos antes do planner.
141. **Resultado clarification.** Opcao valida resolve; forged/replay falham.
142. **Resultado index poisoning.** Credencial, SQL e prompt injection foram bloqueados.
143. **Resultado provider deterministico.** Golden e repeticao produziram mesmo checksum.
144. **Resultado restart.** Repository novo produziu resultado identico.
145. **Resultado duas replicas.** Estado PostgreSQL e provider deterministico nao dependem de RAM.
146. **Evaluations.** Corpus sintetico versionado executado.
147. **Top-1 accuracy.** `1.0` no corpus dirigido.
148. **Top-k recall.** `1.0` no corpus dirigido.
149. **Ambiguity precision.** Medida e persistida.
150. **Unresolved precision.** Medida e persistida.
151. **Forbidden leakage.** `0.0` no corpus dirigido.
152. **Cross-tenant leakage.** `0.0`.
153. **Deterministic repeatability.** `1.0`.
154. **Testes criados.** Contratos, migration, service, integration, API, golden, performance e OpenAPI.
155. **Total backend coletado.** 1.281 testes.
156. **Total backend aprovado.** 1.279 passed.
157. **Total failed.** 0.
158. **Total xfailed.** 2.
159. **Total XPASS.** 0.
160. **IDs dos xfails.** Esperados: `LUMINA-GAP-DASH-001` e `LUMINA-GAP-TENANT-001`.
161. **Testes direcionados.** 40 testes semanticos coletados; suites dirigidas e remediacoes aprovadas.
162. **Testes PostgreSQL.** Build, publication, rollback, stale, eval, API e migration passaram.
163. **Testes de normalizacao.** Acentos, stopwords, codigo, controles e determinismo passaram.
164. **Testes de ranking.** Ordem, weights, thresholds e golden passaram.
165. **Testes de entity resolution.** Resolved, ambiguous, unresolved, patch e clarification passaram.
166. **Testes de indices.** Full build, idempotency, CAS, publication, rollback e stale passaram.
167. **Testes de RBAC.** Search, inspector, admin e public detail passaram.
168. **Testes de seguranca.** Mass assignment, injection, restricted, forged token e limites passaram.
169. **Testes multi-tenant.** Busca e resources permaneceram isolados.
170. **Testes cross-user.** Contexto e clarification validam ownership.
171. **Testes dos contratos V2.** Schemas estritos e limites passaram.
172. **Testes temporais.** Autoridade temporal permaneceu inalterada.
173. **Testes do planner.** Planner nao importa repository semantico.
174. **Testes do executor.** Executor nao consulta indice e permaneceu inalterado.
175. **Testes do renderer.** Renderer nao recalcula score ou numero.
176. **Testes conversacionais.** Context Resolution/Conversation State permanecem autoridades.
177. **Testes de Knowledge Base.** Lifecycle publicado permaneceu governado.
178. **Testes de User Profile.** Consentimento e precedencia permaneceram.
179. **Testes de Feedback.** Workflow nao altera ranking.
180. **Cenario de quatro turnos.** Coberto pela regressao integral.
181. **Cenario de quatro turnos com aliases.** Coberto por contexto + golden/alias dirigido.
182. **Resultado dos goldens.** Golden semantico revisado e deterministico.
183. **Resultado dos schemas.** 87 schemas exportados duas vezes com hashes iguais.
184. **Resultado OpenAPI.** 170 paths, 195 operations; 21 paths/22 operations semanticas.
185. **Resultado ESLint.** Aprovado sem erro ou warning.
186. **Resultado TypeScript.** `tsc --noEmit` aprovado.
187. **Resultado build.** Next.js 16.2.10 compilou 20 paginas.
188. **Resultado Playwright.** 260 passed na suite integral; cenario semantico 4/4, quatro viewports.
189. **Resultado AST.** 484 arquivos Python do repositorio, zero falhas.
190. **Resultado Docker config.** `docker compose ... config --quiet` aprovado.
191. **Oracle nao acessado.** Codigo e testes sem import/chamada Oracle.
192. **OpenAI nao acessada.** Codigo e testes sem cliente/chamada OpenAI.
193. **Banco operacional nao acessado.** Runner aceitou somente 127.0.0.1:55432/luminaai_test.
194. **Nenhum download de modelo.** Provider usa somente biblioteca padrao.
195. **Dependencias inalteradas.** `backend/requirements.txt` e `frontend/package.json` sem diff.
196. **Lockfiles inalterados.** `frontend/package-lock.json` sem diff.
197. **Producao em LEGACY_ONLY.** Confirmado nos defaults.
198. **Nenhum dataset, SQL ou bind persistido.** Models e events excluem esses campos.
199. **Portas fechadas.** 55432, 3100, 3002 e 8000 sem listener ao final.
200. **Ambiente descartavel removido.** Container, network e volume removidos com `down -v`.
201. **Deprecation ledger.** Canonicalizer, RAM, fallback, adapter e provider registrados.
202. **Technical debt register.** Incremental, jobs, entities, feedback, vector, stale e relations registrados.
203. **Comandos executados.** Git audit, schemas, targeted pytest, full pytest, lint, tsc, build e Playwright.
204. **Comandos nao executados e motivo.** Migration produtiva, Oracle, OpenAI, dados reais, push e benchmark 100k nao executados por seguranca/escopo.
205. **Estado final do Git.** Branch `codex/phase-knowledge-prompts-10-13`; 0 staged, sem commit/tag/push; worktree amplo preserva Prompts 10-13 e arquivos locais.
206. **git diff --stat.** 36 arquivos tracked, 9.034 insercoes e 57 remocoes antes do fechamento do relatorio; 177 entradas untracked incluem a fase e arquivos preexistentes.
207. **Arquivos protegidos preservados.** Blueprint `09B7...B52`, start `2794...FFA1` e stop `BED9...620F`, iguais aos hashes iniciais.
208. **Limitacoes restantes.** Incremental recompila snapshot; tombstone/job/relations avancadas e entities restritas ficam desligados.
209. **Proximo passo.** Checkpoint certificado da fase Prompts 10-13.
210. **Proxima etapa arquitetural.** Prompt 14 - Registro governado de ferramentas da IA.
