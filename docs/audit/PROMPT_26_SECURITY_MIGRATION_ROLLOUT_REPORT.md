# Prompt 26 — Security, Migration e Rollout

Versão: `lumina.security-migration-rollout/1.0`. Data: 2026-08-10.

1. Status: `PROMPT 26 — FULL_SUITE_CERTIFIED`.
2. Classification: `A`.
3. Branch: `codex/phase-operations-prompts-23-26`.
4. HEAD: `880477a980aeaef840ac0a5c66f8541eb6c7c349`.
5. Version: `lumina.security-migration-rollout/1.0`.
6. Threat model: concluído antes da implementação.
7. Threat surfaces: 36 superfícies mapeadas.
8. Security controls: 32.
9. Controls passed: 32.
10. Controls failed: 0.
11. Critical findings: 0 não resolvidos; três remediados.
12. High findings: 0 não resolvidos; três remediados.
13. Tenant authority: usuário autenticado PostgreSQL; payload/header não é autoridade.
14. TENANT-001: PASS; disclosure 0, mutation 0.
15. IDOR/BOLA: PASS com tenant filter e concealment 404.
16. Auth matrix: estática, extraída das policies reais, deny-by-default.
17. CONSULTA: somente capabilities de leitura/ack/dismiss permitidas.
18. GESTOR: leitura governada e authoring/review conforme policy; sem admin operacional.
19. ADMIN: capabilities administrativas explícitas; sem bypass de tenant.
20. Privilege escalation: PASS; role/capability/tenant forjados não concedem autoridade.
21. Header forging: PASS; identity headers ignorados e request ID server-owned.
22. CORS: PASS; wildcard + credentials e localhost produtivo recusados.
23. CSRF: PASS; cookie mutation exige Origin allowlisted; bearer não usa cookie como autoridade.
24. Security headers: nosniff, frame deny, referrer, permissions, API CSP; HSTS só produção.
25. XSS: PASS no corpus visual; sem renderer HTML bruto Prompt 26.
26. SQL injection: PASS; Prompt 26 não aceita SQL e execução analítica continua bind/catalog-driven.
27. Command injection: PASS; zero shell/subprocess em runtime Prompt 26.
28. Path traversal: PASS; trace ID bounded e parent path verificado.
29. SSRF: PASS; zero cliente HTTP/import de rede no runtime Prompt 26.
30. Secret leakage: 0 segredo real em 97 arquivos da fase/P26 escaneados.
31. CoT leakage: 0; keys prompt/reasoning/chain-of-thought são redigidas.
32. Error sanitization: PASS; erro genérico constante e detail estrutural redigido.
33. Input bounds: PASS; body 2 MiB, paginação e recursão/strings limitadas.
34. Pagination: PASS; limits/offsets existentes permanecem bounded.
35. Replay safety: PASS; queue só DEAD_LETTER/ADMIN; inspector fail-closed.
36. Security evaluations: sete suites novas, registry total 26.
37. Configuration readiness: READY para baseline produtiva desligada.
38. Invalid prod configs: fail-closed em oito cenários dirigidos.
39. Test-only guards: PASS; local test DB, mocks e egress guard.
40. Migration v27: `NOT_REQUIRED`.
41. Migration v27 reason: Prompt 26 não persiste estado novo.
42. Migration tables: 0 novas.
43. Migration constraints: 0 novas.
44. Migration indexes: 0 novos.
45. v27 first up: N/A, corretamente não executado.
46. v27 second up: N/A, corretamente não executado.
47. v27 down: N/A, corretamente não executado.
48. Migration chain down: PASS nas regressões v12–v26 descartáveis.
49. Migration chain up: PASS nas regressões v12–v26 descartáveis.
50. Historical migrations: v1–v23 tracked intactas; v24–v26 preexistentes untouched.
51. Migration lock: PASS fake e PostgreSQL real com duas sessões.
52. Schema drift: PASS; objeto crítico ausente resulta BLOCKED.
53. Schema compatibility: mínimo 12, atual/máximo testado 26.
54. Previous-app/current-db: COMPATIBLE para migrations aditivas testadas.
55. Current-app/previous-db: feature gate exige migration mínima e bloqueia quando ausente.
56. Unknown future schema: `DATABASE_TOO_NEW`, fail-closed.
57. Consolidated backup: PASS na regressão de migrations existente.
58. Consolidated restore: PASS na regressão de migrations existente.
59. Manifest A: gerado no banco descartável pelas cadeias certificadas.
60. Manifest B: gerado após restore/re-up.
61. Manifest equality: PASS.
62. Feature inventory: 8 features governadas.
63. Rollout policy: registry estático, sem plugin/import dinâmico.
64. Rollout stages: 9 estados fechados.
65. Dependency gates: PASS; migration/dependencies/environment/rollback declarados.
66. Kill switches: 8 feature switches ativos por default.
67. Global emergency disable: ativo por default.
68. Kill switch precedence: global → feature → demais gates.
69. Canary policy: SHA-256 versionado, server-side, allowlist interna explícita.
70. Canary determinism: PASS.
71. Canary client forging: PASS; não existe API/field de seleção do cliente.
72. Active real canary tenants: 0.
73. Rollout readiness state: `READY_FOR_CANARY` técnico em simulação; runtime atual DISABLED.
74. SHADOW readiness: PASS estrutural, side-effect-free.
75. INTERNAL readiness: PASS estrutural, exige operador/capability futura.
76. CANARY readiness: PASS técnico, não executado.
77. FULL readiness: BLOCKED por evidência produtiva futura obrigatória.
78. Abort conditions: security/tenant/schema/error budget/performance/queue/rollback.
79. Error budget integration: gate obrigatório de canary/expansion/full.
80. Performance integration: gate estrutural; harness continua test-only.
81. Rollback types: feature, application, database e data-effect.
82. Rollback matrix: 8/8 features completas.
83. Queue rollback: stop enqueue/drain/preserve leases/jobs.
84. Post-sync rollback: stop consumer/publication; sync/reconciliation preservados.
85. Dashboard AI rollback: cancel provider/tools; drafts/publicações preservados.
86. Application rollback compatibility: declarada para as oito features.
87. Database rollback policy: nunca automática em produção.
88. Compatibility matrix: previous/current/future cobertos.
89. Startup readiness: DB failure aborta staging/production/test.
90. Health: `/health` é liveness.
91. Readiness: `/health/deep` inclui dependências e configuration readiness.
92. Prompt26 APIs: 0.
93. Prompt26 frontend: 0 páginas/componentes/requests.
94. Tenant switch: proteção server-side preservada.
95. Logout: cookie removido; Playwright PASS.
96. Stale request handling: regressão Playwright PASS.
97. Security corpus: PASS.
98. Rollout simulation: PASS sem side effects.
99. Failure injection: PASS em critical gate, drift, contention e invalid config.
100. Rollback simulation: PASS estrutural; banco produtivo não tocado.
101. Incident readiness: runbook concluído.
102. Break-glass: auditado como `BREAK_GLASS_NOT_IMPLEMENTED`; zero bypass.
103. Security observability: eventos restricted e payloads redigidos.
104. Metric cardinality: labels fechadas, sem tenant/user/request/resource ID.
105. Redaction: Prompt 24 reutilizado e ampliado para SQL/DSN/JWT/PEM/path/CoT.
106. Security baseline: golden imutável exportado.
107. Baseline status: 32 PASS, 0 FAIL, 0 CRITICAL FAIL.
108. Schema count: 26.
109. Schema hash run1: `fff4376d81318e8735176ef1e83bee4675c9551347420ff498ba46939101730b`.
110. Schema hash run2: idêntico ao run1.
111. Golden count: 4.
112. Golden hash run1: `7473486463db4934a54746ae88d7f5113a1bd6d5a6a3d6bdf79e0c58718389c9`.
113. Golden hash run2: idêntico ao run1.
114. DEFAULT paths: 190.
115. DEFAULT operations: 216.
116. DEFAULT Prompt26 paths: 0.
117. DEFAULT canonical hash run1: `ab2ed7a6f3f67828ab3837f9b9f12e6746c1198449beb74fd66a0ef1cf718f0b`.
118. DEFAULT canonical hash run2: idêntico ao run1.
119. COMBINED paths: 256.
120. COMBINED operations: 289.
121. Prompt18 paths: 5.
122. Prompt20 paths: 22.
123. Prompt22 paths: 11.
124. Prompt23 paths: 7.
125. Prompt24 paths: 10.
126. Prompt25 paths: 11.
127. Prompt26 paths: 0.
128. Missing previous paths: 0.
129. Combined hash run1: `c4f7c6731be6a074d9f589d6def0dcedcbaf0ab1269581854524ac538c26b52c`.
130. Combined hash run2: idêntico ao run1.
131. Import side effects: 0 DB/network/worker/rollout side effects em clean OpenAPI imports.
132. Regression Prompt09: PASS.
133. Regression Prompt10: PASS.
134. Regression Prompt11: PASS.
135. Regression Prompt12: PASS.
136. Regression Prompt13: PASS.
137. Regression Prompt14: PASS.
138. Regression Prompt15: PASS.
139. Regression Prompt16: PASS.
140. Regression Prompt17: PASS.
141. Regression Prompt18: PASS.
142. Regression Prompt19: PASS.
143. Regression Prompt20: PASS.
144. Regression Prompt21: PASS.
145. Regression Prompt22: PASS.
146. Regression Prompt23: PASS.
147. Regression Prompt24: PASS.
148. Regression Prompt25: PASS.
149. DASH-001: PASS; zero xfail na suíte final.
150. Prompt26 directed collected: 36.
151. Prompt26 directed passed: 36.
152. Prompt26 directed failed: 0.
153. Prompt26 directed skipped: 0.
154. Backend collected: 1906.
155. Backend passed: 1906.
156. Backend failed: 0.
157. Backend errors: 0.
158. Backend skipped: 0.
159. Backend xfailed: 0.
160. Backend XPASS: 0.
161. Backend warnings: 2 Pydantic deprecation preexistentes.
162. Backend duration: 1752.99s (`29m12s`).
163. Lint errors: 0.
164. Lint warnings: 13 preexistentes, documentadas.
165. TypeScript: PASS, 0 errors.
166. Build: PASS.
167. Pages/routes: 28.
168. Playwright run count: 2.
169. Playwright total: 412 por run; 824 execuções somadas.
170. Playwright passed: 412 + 412.
171. Playwright failed: 0 + 0.
172. Playwright skipped: 0 + 0.
173. Viewports: desktop, mobile, tablet e ultrawide.
174. AST discovered: 826.
175. AST analyzed: 826.
176. AST errors: 0.
177. Docker config: PASS.
178. OpenAI: 0 chamadas reais.
179. Oracle: 0 acessos runtime.
180. Operational DB: 0 acessos.
181. Port 5432: 0 uso.
182. Real provider: 0.
183. External network: 0 no backend test; Playwright usa apenas localhost isolado.
184. Dependencies: 0 novas.
185. Lockfiles: unchanged.
186. Secrets: 0 reais; candidatos encontrados eram fixtures/placeholders sintéticos.
187. Blueprints blob initial: `2F2C79E87D0B1564B3BA04F40B0ABA0B05430B411EDAFDD6064028A7E2403744`.
188. Blueprints blob final: idêntico ao initial.
189. Blueprints Git diff: vazio, 0 bytes.
190. Production mode: `LEGACY_ONLY`.
191. Worker production: disabled.
192. Performance production: disabled.
193. Rollout execution: disabled.
194. Canary execution: not executed; 0 tenants.
195. Production migration: not executed.
196. Security report: este documento + golden `security_readiness.json`.
197. Rollout report: READY_FOR_CANARY técnico; FULL bloqueado.
198. Rollback report: 8/8 plans ready.
199. Threat model docs: `docs/security/THREAT_MODEL_V2.md`.
200. Runbook: três runbooks Prompt 26 concluídos.
201. ADR: 0029.
202. TEST_BASELINE: atualizado somente após verde final.
203. Deprecation ledger: atualizado; nenhum legado removido.
204. Technical debt: atualizado com canary/SLO/WAF/secrets/broker/DR/pentest/load.
205. Diff check: 0 erro novo no escopo; apenas trailing whitespace preexistente em runtime-log protegido.
206. Cleanup: concluído; relatórios, test DB e Docker Desktop da tarefa removidos/parados.
207. Ports final: 55432, 3100, 3002 e 8000 fechadas.
208. Workers final: 0 workers V2.
209. Containers: 0 da tarefa.
210. Networks: 0 da tarefa.
211. Volumes: 0 da tarefa.
212. Dumps: 0.
213. Git index: vazio.
214. Commits: 0.
215. Tags: 0 novas.
216. Push: 0.
217. Upstream: inalterado; branch atual sem upstream novo.
218. Unresolved limitations: rollout/canary/SLO/load/pentest/DR produtivos, WAF/proxy,
     external alerting/secret manager, broker/autoscaling/multi-region/pool tuning e guard
     frontend server-side permanecem futuros; nenhum é bypass de autoridade backend.
219. Final decision: `PHASE 23–26 CHECKPOINT — AUTHORIZED`.

Nenhum checkpoint, stage, commit, tag, push, branch switch, rollout, canary,
worker ou migration produtiva foi executado.

## CERTIFICATION ADDENDUM — OPENAPI CANONICAL DELTA BEFORE PHASE CHECKPOINT

### Método e recuperação do baseline

O algoritmo canônico continua exatamente o método oficial do Prompt 25.4, sem
summary dict, timestamps, separators customizados ou transformação de components:

```python
hashlib.sha256(
    json.dumps(app.openapi(), sort_keys=True).encode()
).hexdigest()
```

O JSON integral certificado no Prompt 25.4 não foi preservado. A recuperação foi
auditável e não baseada em memória: o router Validation V2 anterior foi carregado
diretamente do blob de `HEAD`, e o enum anterior de avaliações veio dos schemas
exportados pelo Prompt 24/25. O DEFAULT reconstruído produziu exatamente
`87f5f4835a4555e44f8a2640ffb9facead89763f9ba1d1a7b570cad9976792e3`; aplicando
também o enum anterior de 19 valores, o COMBINED reconstruído produziu exatamente
`bfae6ce1c42932c69312638db31fc81181d3a7def7efdfde39246a51af9124bb`.
Isso fecha a limitação de ausência do JSON histórico por reprodução exata dos dois
hashes certificados.

### Baselines canônicos

| Superfície | Prompt 25.4 | Prompt 26 / atual R1 | Atual R2 | Paths | Operações | Components |
|---|---|---|---|---:|---:|---|
| DEFAULT | `87f5f4835a4555e44f8a2640ffb9facead89763f9ba1d1a7b570cad9976792e3` | `ab2ed7a6f3f67828ab3837f9b9f12e6746c1198449beb74fd66a0ef1cf718f0b` | idêntico a R1 | 190 | 216 | 358 schemas + 1 security scheme |
| COMBINED | `bfae6ce1c42932c69312638db31fc81181d3a7def7efdfde39246a51af9124bb` | `c4f7c6731be6a074d9f589d6def0dcedcbaf0ab1269581854524ac538c26b52c` | idêntico a R1 | 256 | 289 | 589 schemas + 1 security scheme |

Os hashes atuais foram gerados duas vezes em processos Python completamente
limpos. DEFAULT permaneceu com Prompt 26 paths = 0. COMBINED preservou Prompt 18 =
5, Prompt 20 = 22, Prompt 22 = 11, Prompt 23 = 7, Prompt 24 = 10, Prompt 25 = 11,
Prompt 26 = 0 e missing previous paths = 0. Worker, performance, rollout e canary
real permaneceram desligados durante a certificação.

### Diff semântico DEFAULT

- `added_paths = 0`; `removed_paths = 0`.
- `added_operations = 0`; `removed_operations = 0`;
  `changed_operation_ids = 0`.
- Request bodies, path/query parameters, fields, bounds e formats: zero mudança.
- `POST /api/v2/validation/run`: remove da declaração os headers opcionais e não
  confiáveis `X-Tenant-ID` e `X-User-ID`; adiciona
  `security: [{"OAuth2PasswordBearer": []}]`. Body, respostas 200/422, schemas,
  summary e tags permanecem idênticos.
- `GET /api/v2/validation/policy/default`: remove os mesmos dois headers, adiciona
  o mesmo requisito OAuth2 e remove a resposta OpenAPI 422 que existia apenas pela
  validação desses headers. A resposta 200 e `ValidationPolicyV2` não mudam.
- `securitySchemes`: zero mudança; `OAuth2PasswordBearer` já existia.
- Components DEFAULT adicionados/removidos/alterados: 0/0/0.
- Success responses, response headers, examples, descriptions, tags e metadata:
  zero mudança. O único error-contract delta é a remoção do 422 documental no GET;
  `HTTPValidationError` permanece inalterado.

### Diff semântico COMBINED

O COMBINED contém todo o delta DEFAULT e exatamente mais uma alteração:

- Components adicionados/removidos: 0/0.
- Changed components: somente `EvaluationSuiteKindV2`.
- O enum foi ampliado de 19 para 26 valores com:
  `AUTHORIZATION_SECURITY`, `TENANT_ISOLATION_SECURITY`, `API_INPUT_SECURITY`,
  `SECRET_LEAKAGE_SECURITY`, `ERROR_SANITIZATION_SECURITY`,
  `ROLLOUT_GUARD_SECURITY` e `MIGRATION_COMPATIBILITY_SECURITY`.
- Paths, operações, operationIds, bodies, responses, security schemes, metadata,
  descriptions, tags, examples e headers adicionais: zero mudança além do delta
  Validation V2 já descrito.

### Compatibilidade e causa raiz

Classificação principal: `INTENTIONAL_SECURITY_SCHEMA_HARDENING`.

Não existe `HASH_METHOD_DRIFT`, mudança somente de metadata ou regressão OpenAPI
inexplicada. A remoção de headers client-controlled e a exigência de identidade
assinada são deliberadamente incompatíveis para clientes que dependiam de
autorização insegura sem bearer token; essa incompatibilidade foi explicitamente
autorizada pelo hardening Prompt 26 e é necessária ao isolamento de tenant. Enviar
os headers continua sendo tolerado pelo HTTP, mas eles não concedem autoridade. A
remoção do 422 documental no GET é compatível, pois elimina uma classe de erro sem
alterar o sucesso. A expansão do enum é aditiva e ocorre somente na superfície
experimental COMBINED; consumidores de enums fechados devem regenerar clientes,
mas nenhuma API DEFAULT recebe esse component.

Resultado: zero breaking change DEFAULT indevida. Os novos hashes tornam-se os
baselines canônicos oficiais pós-Prompt 26:

- DEFAULT: `ab2ed7a6f3f67828ab3837f9b9f12e6746c1198449beb74fd66a0ef1cf718f0b`.
- COMBINED: `c4f7c6731be6a074d9f589d6def0dcedcbaf0ab1269581854524ac538c26b52c`.

### Evidência dirigida e decisão

Foram executadas as suítes proporcionais de security rollout, Validation/auth,
tenant, Observability/Evaluation e hashes do Work Queue: `36 passed`, `0 failed`,
`0 skipped`, `0 xfailed`, com duas advertências Pydantic preexistentes. Como nenhum
código runtime/router/contract foi alterado nesta reconciliação, ficam retidos:
backend `1906 passed`, Playwright `412 + 412 passed` e AST `826/0`.

Dependências e lockfiles permanecem inalterados; migrations v1-v26 permanecem
intactas e v27 ausente; blueprint mantém SHA-256 Git/LF
`2F2C79E87D0B1564B3BA04F40B0ABA0B05430B411EDAFDD6064028A7E2403744`
e status vazio. Produção permanece `LEGACY_ONLY`, com worker, performance, rollout,
canary e migration produtiva em zero.

Decisão da reconciliação: `PHASE 23–26 CHECKPOINT — AUTHORIZED`.
O checkpoint não foi executado nesta tarefa.
