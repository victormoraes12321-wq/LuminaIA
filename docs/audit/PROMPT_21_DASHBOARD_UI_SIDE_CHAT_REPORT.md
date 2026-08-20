# Relatório de certificação — Prompt 21

Data da certificação: 2026-08-05. Escopo: interface governada de dashboards e side chat contextual, contrato `lumina.dashboard-ui-sidechat/1.0`.

1. **Status:** Prompt 21 implementado e certificado; suítes backend e frontend integrais verdes, sem `xfail`, `XPASS`, falhas ou erros.
2. **Trava de entrada:** a entrada exigia Prompt 19 e Prompt 20 presentes, branch/HEAD exatos, índice vazio e preservação dos arquivos protegidos; todas as condições foram conferidas antes das alterações.
3. **Branch:** `codex/phase-dashboard-prompts-19-22`.
4. **HEAD:** `14e13bc886372690d144addc255c1ec60d59e62a`.
5. **Auditoria frontend:** foram auditados App Router, dashboard legado/Studio, `Sidebar`, `AuthContext`, `useLuminaQuery`, `DynamicRenderer`, Recharts/ECharts, comparação, Trust Center e temas antes da implementação V2.
6. **Causa DASH-001:** o gerenciador mutava por referência o `dashboard_state` histórico e respondia `FULL_RENDERING` mesmo quando a alteração era estritamente visual e local.
7. **Solução DASH-001:** cópia profunda do estado, nó histórico imutável, validação de dataset certificado e retorno `UI_MODIFIED` para atualização visual governada; mudanças semânticas seguem o pipeline completo.
8. **Arquivos criados:** novos contratos/tipos, cliente e políticas V2, quatro rotas, componentes de biblioteca/runtime/editor/histórico/side chat, fixtures, testes e documentação do Prompt 21.
9. **Arquivos alterados:** integração mínima em query/conversation graph, `Sidebar`, configuração Playwright, mocks de regressão e índices/documentação; alterações preexistentes dos Prompts 19–20 foram preservadas.
10. **Versão:** `lumina.dashboard-ui-sidechat/1.0`.
11. **Contracts:** contratos fechados TypeScript e Pydantic cobrem contexto mínimo, ações tipadas, resultados do interceptor, runtime e capabilities, com rejeição de campos arbitrários.
12. **Feature modes:** `LEGACY_ONLY`, `V2_PREVIEW`, `V2_READ`, `V2_AUTHORING` e `V2_SIDE_CHAT`, interpretados de forma fail-closed.
13. **LEGACY_ONLY:** continua padrão e oculta rotas/link V2; prova Playwright dedicada passou com zero chamadas à API V2 de dashboards.
14. **V2_PREVIEW:** permite superfície de leitura/preview conforme capabilities retornadas pelo backend, sem autorizar escrita por configuração cliente.
15. **V2_READ:** habilita biblioteca e runtime publicado, mantendo edição e lifecycle condicionados às capabilities servidoras.
16. **V2_AUTHORING:** habilita editor/histórico somente para usuários e dashboards com capabilities autorizadas pelo backend.
17. **V2_SIDE_CHAT:** adiciona o side chat contextual sobre o runtime governado, sem conceder poderes semânticos ou de lifecycle.
18. **Routes:** `/dashboard/v2`, `/dashboard/v2/[dashboardId]`, `/dashboard/v2/[dashboardId]/edit` e `/dashboard/v2/[dashboardId]/history`.
19. **Route guards:** guardas no servidor aguardam o modo efetivo e retornam `notFound()` quando a superfície não está autorizada; edição/histórico exigem modo de autoria.
20. **Sidebar:** link V2 aparece apenas fora de `LEGACY_ONLY` e após capability `dashboard:view`; troca de usuário/mode remove acesso antigo.
21. **Dashboard library:** lista/search/lifecycle, skeleton, erro, vazio, badges de capability e criação manual por clone governado, sem IA.
22. **Dashboard shell:** concentra cabeçalho, filtros, grid, status, interações, proveniência e side chat sem recalcular fatos analíticos.
23. **Widget registry:** registry estático e fechado com 16 tipos, sem plugin ou import dinâmico.
24. **Widget renderer:** valida tipo e shape, falha fechado, preserva ordenação do backend e expõe fallback textual para gráficos.
25. **KPI:** renderiza valor/unidade/status fornecidos pelo backend, sem cálculo no navegador.
26. **Comparison KPI:** apresenta baseline, target, delta e percentual já certificados, sem recomputação.
27. **Charts:** barras, linhas, áreas, composição e demais séries usam Recharts somente após bounds positivos observados.
28. **Pie/donut:** fatias e legendas respeitam ordem e valores recebidos; existe fallback tabular acessível.
29. **Table:** tabela preserva colunas/linhas, estados parciais e truncation declarados pelo backend.
30. **Ranking:** exibe posição e valores certificados sem reordenar ou recalcular participação.
31. **Layout:** grid declarativo limita posição e dimensão aos valores governados do blueprint.
32. **Breakpoints:** desktop, tablet, mobile e ultrawide foram exercitados, com quatro layouts responsivos.
33. **Editor:** editor manual separa patches, preview, descarte, undo, envio governado e tratamento de conflito.
34. **Visual editor:** título e layout formam patch visual allowlisted e exigem preview antes da persistência.
35. **Semantic editor manual:** alterações semânticas são separadas, explícitas e manuais; nunca são convertidas em patch visual.
36. **Preview:** nenhuma proposta visual é confirmada sem etapa de preview e confirmação humana.
37. **Drag/keyboard controls:** controles numéricos nativos e teclado permitem mover/redimensionar; drag avançado por toque não foi introduzido.
38. **CAS:** writes incluem checksum/revision esperados e nunca sobrescrevem uma revisão concorrente.
39. **Idempotência:** operações mutáveis usam chave de idempotência gerada no cliente e aceita pela API governada.
40. **Conflicts:** conflito CAS é mostrado, mantém a edição local segura e oferece recarga governada.
41. **Filters:** somente filtros publicados no blueprint podem ser enviados; submissão é explícita.
42. **Filter state:** rascunho e estado aplicado são distintos, reset é fechado e mudanças disparam runtime cancelável.
43. **Cross-filter:** só interações declaradas atingem widgets allowlisted e o backend continua autoridade do novo dataset.
44. **Drilldown:** envia interação fechada, mantém breadcrumb acessível e permite voltar sem inventar dados.
45. **Provenance:** drawer mostra somente fatos públicos permitidos, freshness/classification/partial, nunca SQL, binds ou credenciais.
46. **Side chat:** usa o endpoint de consulta já governado, com contexto mínimo e ações fechadas.
47. **Side chat context:** envia IDs/version/checksum, widget em foco, filtros e interação mínima sanitizada; não envia dataset, SQL ou valores empresariais brutos.
48. **Side chat modes:** `ASK` explica em texto; ações somente são aplicáveis quando o backend devolve união tipada válida.
49. **Side chat actions:** `NO_ACTION`, `FOCUS_WIDGET`, `OPEN_PROVENANCE`, `APPLY_FILTER`, `RESET_FILTERS`, `DRILLDOWN`, proposta/aplicação visual e `BLOCKED`.
50. **Visual patch proposal:** título/layout allowlisted geram proposta revisável; campos semânticos e accessibility arbitrária são recusados.
51. **Visual patch apply:** aplica via API de revisão e só conclui depois da resposta persistida do backend.
52. **Visual interceptor:** classifica `UI_MODIFIED`, `FULL_RENDERING_REQUIRED`, `NO_OP`, `BLOCKED`, `CONFLICT` e `INVALID_ACTION`.
53. **UI_MODIFIED:** exige confirmação do backend e preservação do semantic checksum; não é inferido apenas pelo cliente.
54. **FULL_RENDERING_REQUIRED:** reservado a resultado válido que exige novo runtime; não mascara conflito ou ação inválida.
55. **Semantic edit via chat:** bloqueado; side chat não altera métrica, dimensão, fonte, fórmula ou significado.
56. **Publish via chat:** bloqueado; publicação permanece operação humana dedicada de lifecycle.
57. **Rollback via chat:** bloqueado; rollback permanece operação humana confirmada e auditável.
58. **Streaming:** o corpo incremental da query existente é consumido com estados `CONNECTING`, `RECEIVING`, `COMPLETE`, `CANCELLED`, `FAILED`, `RETRYABLE`, `ACTION_PENDING` e `ACTION_CONFIRMED`; chunks não executam ação antes do envelope completo.
59. **Cancellation:** runtime e side chat usam `AbortController` e descartam resposta cancelada.
60. **Stale response protection:** generation tokens impedem respostas antigas de substituir runtime/texto mais recente.
61. **Security:** IDs e ownership vêm do servidor, actions são allowlisted, HTML/URLs livres são rejeitados e credenciais não entram nos payloads.
62. **Markdown:** respostas textuais não executam HTML arbitrário; ações mutáveis nunca são extraídas de markdown livre.
63. **Lifecycle UI:** histórico oferece request changes, approve, reject, publish e rollback segundo capabilities.
64. **Review UI:** revisão é ação humana separada e registrada por endpoint governado.
65. **Approval UI:** aprovação exige confirmação/capability e não é acessível pelo side chat.
66. **Publication UI:** publicação exige confirmação, CAS/idempotência e endpoint específico.
67. **Rollback UI:** rollback cria nova publication no backend e nunca reativa/apaga linha histórica pelo cliente.
68. **Collaborators UI:** add/update/remove respeitam capabilities e papéis de colaborador não elevam RBAC global.
69. **History:** exibe revisions/publications e comparação de revisões sem mutar histórico.
70. **Comparison:** comparação visual usa fatos/deltas certificados e não recalcula matemática financeira.
71. **Error boundaries:** rotas possuem `error.tsx`, estados de erro locais e retry controlado.
72. **Accessibility:** labels, tabelas alternativas, breadcrumb, foco, diálogo mobile e controles por teclado foram implementados.
73. **Responsive:** não houve overflow horizontal nos viewports certificados; side chat vira diálogo no mobile.
74. **Light/dark:** estados normal, partial, stale e truncated foram verificados em tema escuro e permanecem legíveis.
75. **Telemetry:** eventos são estruturais e não registram pergunta, valor, SQL ou dado empresarial.
76. **API client:** usa `getApiBase()`, `credentials: 'include'`, `no-store`, correlation ID, timeout, abort e idempotência.
77. **APIs consumidas:** lista/detalhe/runtime/revisions/lifecycle/publications/collaborators do Prompt 20 e query existente para side chat.
78. **Backend changes:** novo schema de side chat, extensão opcional e compatível de query, sanitização de contexto e correção do conversation graph.
79. **Multi-tenant:** tenant/user não são aceitos como autoridade do cliente; autenticação, API e capability servidoras mantêm o isolamento.
80. **Tenant switch:** remount por chave tenant/user cancela estado/runtime anterior e força nova autorização.
81. **Logout:** desmontagem do contexto autenticado remove link/superfície e impede reuso de estado V2.
82. **Cenário LEGACY_ONLY:** passou com rota V2 404, link ausente e zero requests V2.
83. **Cenário V2 read:** biblioteca e runtime publicado aparecem somente com mode/capabilities compatíveis.
84. **Cenário unpublished:** conteúdo não publicado não é tratado como runtime público; autoria depende de capability.
85. **Cenário junho:** fixture certificada de junho é exibida sem síntese numérica no frontend.
86. **Cenário julho:** fixture certificada de julho é exibida e preserva o período informado.
87. **Cenário comparação:** comparação junho/julho preserva operands, baseline, target e valores recebidos.
88. **Cenário total vs média:** widgets exibem total e média como métricas distintas já calculadas no backend.
89. **Cenário ranking:** ranking mantém ordenação governada e posições recebidas.
90. **Cenário contas abertas:** tabela/KPI de contas abertas usa somente payload certificado da fixture.
91. **Cenário estoque:** visualização de estoque usa o widget declarado e não consulta fonte paralela.
92. **Cenário partial:** marcador partial permanece explícito no shell/widget.
93. **Cenário stale:** freshness stale permanece explícito e não é ocultado por tema/layout.
94. **Cenário truncation:** dataset truncado mostra aviso e não aparenta totalidade.
95. **Cenário filter:** rascunho não consulta; submit/reset produzem request governado.
96. **Cenário cross-filter:** target allowlisted é atualizado e resposta antiga é descartada.
97. **Cenário drilldown:** interação fechada, breadcrumb e back passaram no Playwright.
98. **Cenário provenance:** drawer mostra metadados permitidos e exclui SQL/binds/segredos.
99. **Cenário create manual:** criação manual clona fonte governada sem chamar query ou IA.
100. **Cenário visual edit:** patch de título/layout passa por preview, revisão backend e confirmação.
101. **Cenário semantic edit manual:** editor mantém patch semântico separado e sujeito a nova revision/revalidação.
102. **Cenário conflict:** CAS 409 não sobrescreve e apresenta reload.
103. **Cenário review:** request changes/review usa endpoint governado e confirmação humana.
104. **Cenário approval:** aprovação é capability-gated e não ocorre pelo chat.
105. **Cenário publication:** publicação usa confirmação, idempotência e atualização do histórico.
106. **Cenário rollback:** rollback usa endpoint dedicado e fluxo humano confirmado.
107. **Cenário collaborator:** add/update/remove preservam restrição entre papel colaborativo e RBAC.
108. **Cenário side chat ask:** texto contextual é retornado sem mutação não tipada.
109. **Cenário explain:** explicação fica textual; fatos/proveniência continuam vindos do runtime certificado.
110. **Cenário chat filter:** filtro tipado só atinge filtro publicado e recarrega runtime.
111. **Cenário chat focus:** foco local só aceita widget existente no blueprint.
112. **Cenário chat provenance:** abre drawer do widget declarado, sem ampliar dados públicos.
113. **Cenário visual title:** proposta requer preview e confirmação backend antes de `UI_MODIFIED`.
114. **Cenário move widget:** alteração de layout é visual, governada e persistida com CAS.
115. **Cenário compatible chart:** mudança de `widget_type` permanece bloqueada porque o contrato Blueprint 2.0 vigente a classifica como semântica; não houve enfraquecimento do Prompt 19.
116. **Cenário metric change:** bloqueado no chat e separado no editor semântico manual.
117. **Cenário chat publish:** bloqueado e não convertido a partir de texto livre.
118. **Cenário chat rollback:** bloqueado e não convertido a partir de texto livre.
119. **Cenário injection:** parser rejeitou HTML-like text, URL arbitrária, action name aberto e patch fora da allowlist.
120. **Cenário cancellation:** request abortada não aplica ação nem altera UI.
121. **Cenário stale chat:** resposta atrasada não substitui texto/ação do turno mais novo.
122. **Cenário tenant switch:** estado é reinicializado por chave de identidade e reautorizado.
123. **Cenário logout:** link/estado V2 são removidos com o contexto autenticado.
124. **Cenário mobile:** grid sem overflow e side chat em diálogo passaram no viewport mobile.
125. **Cenário keyboard:** layout pode ser alterado por controles nativos de teclado.
126. **Cenário dark:** partial/stale/truncation passaram no tema escuro.
127. **Cenário boundary:** widget desconhecido falha fechado enquanto widgets válidos continuam renderizados.
128. **Cenário DASH-001:** teste antes marcado como gap agora passa com `UI_MODIFIED`, sem mutar o gráfico do nó pai.
129. **Cenário quatro turnos:** conversation graph mantém sequência e estado histórico entre turnos, aplicando apenas a atualização visual permitida.
130. **Cenário aliases:** aliases visuais continuam sujeitos ao conjunto fechado de visualizações e não autorizam mudança semântica.
131. **Cenário duas abas:** CAS e generation tokens impedem overwrite silencioso entre clientes/abas concorrentes.
132. **Testes criados:** contratos backend, regressão conversation graph, 5 testes de contrato frontend e 23 cenários Playwright V2 executados nos projetos configurados.
133. **Testes dirigidos:** regressão Prompt 19/20 + tenant/dashboard/Prompt 21: `278 passed` em `121.13s`; targeted backend do Prompt 21: `22 passed`.
134. **DASH-001 isolado:** o teste isolado e a suíte integral confirmaram a correção; nenhum marcador esperado de falha permanece.
135. **Backend collected:** 1694 testes coletados/executados pelo runner seguro.
136. **Backend passed:** 1694.
137. **Backend failed:** 0.
138. **Backend errors:** 0.
139. **Backend skipped:** 0.
140. **Backend xfailed:** 0.
141. **Backend XPASS:** 0.
142. **Warnings:** 2 warnings Pydantic preexistentes sobre `min_items`; ESLint reportou 8 warnings preexistentes, sem erros.
143. **Duração:** suíte backend integral `1186.89s` (19min46s); suíte visual final renovada `607.1s` (10min07s).
144. **Prompt 19 regressão:** contratos/canonicalização/validação/exports do Blueprint V2 permaneceram verdes e `blueprints.json` foi preservado.
145. **Prompt 20 regressão:** contratos/governança/policy/router/runtime/PostgreSQL/migration/goldens permaneceram verdes.
146. **OpenAPI default paths:** 190.
147. **OpenAPI default operações:** 216.
148. **OpenAPI experimental paths:** 212.
149. **OpenAPI experimental operações:** 243.
150. **OpenAPI hashes:** default reproduzível `e13d88b46e1a546725fe629ac797f8e0d489ff2f82cd8009e20ae37ff8fcaf25`; experimental reproduzível `724116d02bb5b5062be4ccd37ec30216982de541db8acec816be52b04b26411d`.
151. **Migration v23:** não criada, não encontrada e não executada.
152. **Migrations históricas:** nenhuma migration foi alterada/executada pelo Prompt 21; a v22 existente do Prompt 20 permaneceu no worktree.
153. **ESLint:** `npm run lint` concluiu com exit 0, zero erros e 8 warnings preexistentes.
154. **TypeScript:** `npx tsc --noEmit` concluiu com exit 0.
155. **Build:** `npm run build` concluiu com exit 0 no Next.js 16, incluindo as quatro rotas V2 dinâmicas.
156. **Páginas geradas:** build completou 24 tarefas de geração estática; rotas V2 aparecem como dinâmicas conforme autenticação/mode.
157. **Playwright:** suíte visual integral final `372 passed`, `0 failed`, `0 skipped`, `0 xfailed/XPASS`.
158. **Viewports:** desktop, tablet, mobile e ultrawide.
159. **AST:** 704 arquivos Python próprios analisados, 0 erros sintáticos.
160. **Docker config:** `docker compose -f docker-compose.test.yml config --quiet` retornou exit 0.
161. **OpenAI real:** 0 chamadas; runner e mocks mantiveram rede/IA externa bloqueadas.
162. **Oracle:** 0 chamadas; Oracle não foi fonte de consulta nem validação.
163. **Banco operacional:** 0 acesso; PostgreSQL descartável na porta 55432 foi o único banco dos testes backend.
164. **Dependências:** nenhum arquivo de dependências foi alterado e nenhuma instalação foi realizada.
165. **Lockfiles:** `frontend/package-lock.json` e demais lockfiles não foram alterados.
166. **Blueprints hash inicial:** `407D5C65B7A38A805C073F064A0C1CD9AF6290C8BCBE18809CA645CD81042596`.
167. **Blueprints hash final:** `407D5C65B7A38A805C073F064A0C1CD9AF6290C8BCBE18809CA645CD81042596`, idêntico ao inicial.
168. **Deprecation ledger:** atualizado para registrar coexistência e critérios de retirada do runtime legado, sem antecipar remoção.
169. **Technical debt register:** DASH-001 reconciliado como resolvido após suíte integral; limitações restantes foram explicitadas.
170. **Baseline:** `docs/audit/TEST_BASELINE.md` recebeu baseline certificado do Prompt 21.
171. **Documentação:** contrato, runbook, arquitetura, frontend, API, blueprint repository, changelog e instruções do repositório foram atualizados.
172. **ADR:** `0024-governed-dashboard-ui-and-contextual-side-chat.md` registra limites, decisões e rollback.
173. **Portas:** 55432, 3100, 3002 e 8000 confirmadas fechadas ao final.
174. **Recursos descartáveis:** container/network PostgreSQL removidos com `down -v`; nenhum volume nomeado ficou ativo. `frontend/test-results` e `frontend/playwright-report` restaram porque a política de segurança do terminal bloqueou duas remoções nativas verificadas.
175. **Índice Git:** vazio; `git diff --cached --stat` não produziu saída.
176. **Commits:** nenhum commit criado; HEAD permaneceu inalterado.
177. **Tags:** nenhuma tag criada; a tag preexistente `lumina-phase-ai-orchestration-14-18` já apontava para o HEAD inicial.
178. **Push:** nenhum push e nenhum upstream configurado para a branch atual.
179. **Produção:** inalterada; nenhum serviço operacional iniciado, porta encerrada, migration, firewall ou configuração produtiva modificada pelo Prompt 21.
180. **Rollout:** produção permanece `LEGACY_ONLY`; flags V2 continuam opt-in/fail-closed e capabilities do servidor são obrigatórias.
181. **Limitações:** `widget_type` não pode ser patch visual pelo contrato atual; não há drag touch avançado nem benchmark/load test; artefatos Playwright citados no item 174 exigem remoção manual autorizada. O `git diff --check` global acusa apenas whitespace no log protegido preexistente `runtime-logs/backend-network.err.log`, não alterado por esta tarefa.
182. **Prompt 22 — Criação de Dashboards Assistida por IA:** bloqueado/não autorizado nesta tarefa. O Prompt 21 está tecnicamente certificado, mas Prompt 22 exige solicitação explícita e suas próprias travas de entrada/rollout; nenhuma implementação de geração por IA foi iniciada.
