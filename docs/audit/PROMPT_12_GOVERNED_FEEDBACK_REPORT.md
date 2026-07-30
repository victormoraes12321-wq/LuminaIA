# Relatorio Do Prompt 12 - Feedback Governado

1. **Resumo.** `lumina.supervised-feedback/1.0` foi implementado e certificado sem ativar producao.
2. **Arquitetura.** O fluxo e resposta persistida -> ownership -> redacao -> triagem -> review -> candidate -> exemplo -> snapshot -> export offline.
3. **Arquivos criados.** Foram criados contracts, model, migration v15, repository, services puros, router, telas, tipos, testes, schemas, ADR, runbook e este relatorio.
4. **Arquivos alterados.** Integracoes aditivas atingem config, main, query response, Conversation State FK, sidebar, proxy, renderer do chat, documentacao e exporter de schemas.
5. **Versao.** Contratos, registros, eventos, APIs, schemas e documentacao usam `lumina.supervised-feedback/1.0`.
6. **Fronteiras de autoridade.** Feedback registra declaracoes e decisoes humanas; nao governa formulas, conhecimento, perfil, contexto, SQL ou modelo.
7. **Contracts.** Pydantic 2 estrito, frozen, `extra=forbid` e unioes discriminadas protegem a fronteira.
8. **Feedback target.** O alvo usa response node, sessao publica, query node opcional, versao e checksum.
9. **Ownership validation.** Tenant e usuario autenticados devem coincidir com sessao e resposta persistidas.
10. **Tipos de feedback.** Dezenove categorias distinguem positivo, parcial, erros analiticos, contexto, seguranca, performance e outros.
11. **Tipos de correcao.** Onze correcoes tipadas cobrem metrica, periodo, filtro, entidade, dimensao, comparacao, visual, relacionamento, clarificacao, escopo e texto.
12. **Labels supervisionados.** Nove labels finais sao definidos somente pelo revisor autorizado.
13. **Lifecycle do feedback.** RECEIVED, VALIDATED, TRIAGED, IN_REVIEW, NEEDS_INFORMATION, APPROVED, REJECTED, WITHDRAWN, EXPIRED e ARCHIVED possuem transicoes fechadas.
14. **Lifecycle do candidate.** CANDIDATE precisa passar por VALIDATED antes de APPROVED; rejeicao, dataset, depreciacao e archive sao explicitos.
15. **Lifecycle do dataset.** DRAFT -> IN_REVIEW -> APPROVED -> PUBLISHED, com rejeicao, depreciacao e archive.
16. **Idempotencia.** Chave do usuario e armazenada somente como hash e replay retorna o mesmo feedback sem duplicar eventos.
17. **Duplicate fingerprint.** Tenant, checksum da resposta, categoria, correcao e versao formam fingerprint deterministico.
18. **Checksum.** Contratos usam JSON canonico; exportacao usa SHA-256 dos bytes JSONL entregues.
19. **Optimistic concurrency.** Feedback, candidate e snapshot usam `lock_version` e CAS.
20. **Redaction engine.** `FeedbackRedactionEngine` e puro, deterministico, limitado e sem LLM.
21. **Redaction manifest.** O manifest registra policy, campos, reason codes, tamanhos e checksum sem copiar valores removidos.
22. **Minimizacao.** O frontend envia referencias do target e correcao; nao reenvia resposta, dataset, SQL ou binds.
23. **Dados permitidos.** Categoria, explicacao limitada, correcao canonica, IDs estruturais, checksums e metadados de workflow.
24. **Dados proibidos.** Segredo, token, credential, cookie, connection string, chain of thought, SQL, binds e dataset bruto.
25. **Triage engine.** Regras locais geram severity, priority, queue, flags, warnings e fingerprint.
26. **Severity.** LOW, MEDIUM, HIGH e CRITICAL sao derivados por categoria governada.
27. **Priority.** P1 a P4 ordenam risco de seguranca, integridade, contexto/performance e casos gerais.
28. **Review queue.** SECURITY, DATA_INTEGRITY, CONTEXT, PERFORMANCE, VISUALIZATION e GENERAL sao allowlisted.
29. **Review workflow.** ADMIN/GESTOR atribui reviewer; reviewer registra label e justificativa redigida; decisao final permanece separada.
30. **Separation of duties.** Autor nao revisa o proprio feedback e reviewer da resposta nao aprova o exemplo.
31. **Self-review.** Constraints, service e testes bloqueiam autor igual a reviewer.
32. **Information request.** Reviewer solicita complemento; o dono responde e o item volta para IN_REVIEW por CAS.
33. **Approval.** Exige review humano registrado e permissao explicita.
34. **Rejection.** Exige review humano registrado, lifecycle valido e evento auditavel.
35. **Withdrawal.** O dono retira apenas em estados permitidos; auditoria permanece.
36. **Candidate creation.** Somente feedback APPROVED gera candidate por acao explicita e idempotente.
37. **Candidate validation.** Quality VALID e transicao CANDIDATE -> VALIDATED sao obrigatorias.
38. **Approved example.** Exemplo referencia feedback, reviewer, curator, redaction manifest, contrato e restricoes offline.
39. **Example quality.** VALID, INCOMPLETE, AMBIGUOUS, SENSITIVE, CONFLICTING, OUTDATED_CONTRACT e BLOCKED sao distintos.
40. **Dataset snapshot.** Snapshot tenant-scoped contem IDs de exemplos e manifest, nunca dataset analitico bruto.
41. **Dataset versioning.** Primeiro snapshot e v1; sucessor deve ser exatamente a proxima versao.
42. **Dataset immutability.** PUBLISHED nao pode ser editado; mudanca exige novo snapshot.
43. **Dataset scope.** Runtime cria apenas dataset real tenant-scoped.
44. **Global promotion policy.** Promocao global fica bloqueada sem anonimizacao forte, policy e aprovacao separadas.
45. **Dataset export.** Somente snapshot PUBLISHED e finalidade registrada podem gerar arquivo.
46. **JSONL.** Repository usa cursor em lotes, spool temporario e StreamingResponse de 64 KiB.
47. **Manifest.** Lista ordenada de checksums, criterios, policy de redacao, versao e checksum acompanha o snapshot.
48. **CSV protection.** Prefixos `=`, `+`, `-` e `@` sao neutralizados quando texto vai para CSV.
49. **Import dry-run.** JSONL governado, fixture sintetica e evaluation case sao validados sem persistir, publicar ou executar.
50. **Retention.** Relogio injetavel, keyset/limit e CAS movem pendentes para EXPIRED e finais para ARCHIVED.
51. **Deletion request.** Pedido proprio e idempotente fica auditado; execucao legal automatica nao foi inventada.
52. **Conversation State boundary.** Resposta persistida e autoridade do target; feedback nao reescreve sessoes, nodes ou snapshots.
53. **Context Resolution integration.** Feedback pode rotular erro de heranca, mas nao altera contexto historico nem patch ativo.
54. **Enterprise Knowledge boundary.** Sugestao nao publica alias, regra, metrica ou conhecimento.
55. **Knowledge suggestion.** Deve iniciar workflow separado do Prompt 10 e permanece nao publicada.
56. **User Profile boundary.** Feedback nao cria preference, default ou consentimento.
57. **Profile suggestion.** Preferencia declarada exige confirmacao explicita no perfil antes de uso.
58. **Analytical contracts.** Target registra versao estrutural; nenhum numero e produzido ou recalculado pelo feedback.
59. **Validation integration.** Ownership, checksum, schema, lifecycle, quality e manifest sao validacoes deterministicas.
60. **Provenance integration.** IDs e checksums referenciam resposta, query, feedback, review, candidate, exemplo e snapshot.
61. **Repository.** Toda operacao publica recebe tenant; joins e FKs compostas impedem mistura.
62. **Service.** Permissoes, redacao, triagem, lifecycle, CAS, auditoria, curadoria, export e retencao ficam centralizados.
63. **APIs do usuario.** Criar, ler, listar, complementar, responder, retirar, exportar e solicitar exclusao usam `/api/v2/me`.
64. **APIs de review.** Fila, detalhe redigido, duplicate group, atribuicao, review, aprovacao, rejeicao e complemento sao governados.
65. **APIs de curation.** Candidates, exemplos, snapshots, transicoes, publicacao, export, import dry-run e retencao sao explicitos.
66. **Errors.** Erros tipados cobrem feature, acesso, target, checksum, lifecycle, CAS, candidate e imutabilidade.
67. **RBAC.** Backend e autoridade final; frontend apenas oculta rotas e controles conforme ergonomia.
68. **CONSULTA.** Cria e administra somente feedback proprio.
69. **Reviewer.** GESTOR/ADMIN acessa apenas fila redigida do tenant e nao pode ser o autor.
70. **Curator.** ADMIN valida candidate, aprova exemplo e cria snapshot.
71. **Publisher.** Permissao `feedback:publish_dataset` e snapshot APPROVED sao obrigatorios.
72. **Cross-tenant.** Repository, service, constraints, cache e testes falham fechado.
73. **Cross-user.** Ownership do target, leitura propria, retirada e exclusao impedem IDOR.
74. **Audit.** Eventos estruturais registram ator, tenant, tipo, reason code, request ID opcional e checksum.
75. **Observability.** Contadores aceitam somente nomes allowlisted e nao carregam conteudo.
76. **Cache.** Somente manifest publicado entra no cache, com tenant, snapshot, versao, checksum, TTL e invalidacao.
77. **Feature modes.** LEGACY_ONLY, SHADOW, V2_COLLECT, V2_REVIEW e V2_CURATE separam capacidades.
78. **Production default.** `SUPERVISED_FEEDBACK_MODE=LEGACY_ONLY` e todas as flags iniciam desligadas.
79. **Shadow mode.** Valida target, categoria, severity, redacao, fingerprint e elegibilidade, retornando `persisted=false`.
80. **Frontend do usuario.** Chat coleta positivo/parcial/negativo; historico permite retirada, complemento e exportacao.
81. **Frontend administrativo.** Abas de review e curadoria cobrem reviewer, decision, candidate, exemplo, snapshot e export.
82. **Transparencia.** O usuario ve estado e explicacao propria; comentario interno e SQL nao sao expostos.
83. **Accessibility.** Labels, roles, tablist, botoes nomeados e controles por teclado foram exercitados.
84. **XSS protection.** React escapa texto; backend limita e redige entradas; nenhum HTML bruto foi adicionado.
85. **Stored prompt injection protection.** Texto e dado nao executavel, redigido e nunca entra automaticamente em prompt, knowledge ou treinamento.
86. **Migration.** `migration_v15_0.py` cria 11 tabelas e depende das FKs governadas anteriores.
87. **Migration up.** Up e verify passaram em PostgreSQL descartavel.
88. **Migration idempotency.** Duas aplicacoes consecutivas preservaram schema e dados.
89. **Migration down test-only.** Down falha fora de test e passou no banco descartavel.
90. **Compatibility v15/v14/v13/v12.** Downgrade e upgrade em ordem foram aprovados.
91. **Constraints.** Tenant/user, ownership, lifecycle, checksums, JSON, lock e timestamps possuem checks/FKs.
92. **Indices.** Owner, data, lifecycle, queue, reviewer, duplicate, retention, candidate, dataset e export sao indexados.
93. **Resultado do feedback positivo.** Submissao envia apenas referencias e registra categoria POSITIVE.
94. **Resultado do periodo incorreto.** Correcao EXPECTED_PERIOD e triada como integridade P2.
95. **Resultado do valor incorreto.** INCORRECT_VALUE vai para DATA_INTEGRITY sem alterar numero oficial.
96. **Resultado do filtro incorreto.** EXPECTED_FILTER preserva campo canonico, operador e valores.
97. **Resultado da heranca indevida.** UNWANTED_INHERITANCE vai para CONTEXT sem reescrever estado.
98. **Resultado de self-review.** Service rejeitou atribuicao ao autor.
99. **Resultado da redacao.** Senha, token, connection string, CPF, CNPJ, e-mail e controles foram removidos.
100. **Resultado da duplicidade.** Replay idempotente nao duplicou evento; fingerprint equivalente permaneceu tenant-scoped.
101. **Resultado do review.** Reviewer atribuido registrou label e justificativa com CAS.
102. **Resultado do candidate.** Aprovacao direta de CANDIDATE falhou; validacao previa passou.
103. **Resultado do dataset v1.** Snapshot DRAFT v1 foi criado com exemplo aprovado.
104. **Resultado do dataset v2.** Regra de versao sucessora e imutabilidade da v1 foram testadas.
105. **Resultado do withdrawal.** Item elegivel virou WITHDRAWN sem apagar auditoria.
106. **Resultado cross-tenant.** Target e recursos de outro tenant retornaram falha segura.
107. **Resultado de knowledge suggestion.** Nenhum asset, alias ou publication foi criado.
108. **Resultado de profile suggestion.** Nenhuma preference ou consent foi criado.
109. **Resultado do cenario de quatro turnos.** Regressao preservou contexto, comparacao e drill-down dos Prompts 09/11.
110. **Resultado do feedback no quarto turno.** Feedback parcial e visual permaneceu separado do resultado analitico e do perfil.
111. **Resultado da exportacao.** JSONL terminou com newline, checksum bateu os bytes e nenhum segredo apareceu.
112. **Testes criados.** Seis arquivos backend, 21 goldens e seis cenarios Playwright cobrem o modulo.
113. **Total backend coletado.** 1.241 testes.
114. **Total backend aprovado.** 1.239 passed.
115. **Total failed.** 0.
116. **Total xfailed.** 2.
117. **Total XPASS.** 0.
118. **IDs dos xfails.** `LUMINA-GAP-DASH-001` e `LUMINA-GAP-TENANT-001`.
119. **Testes direcionados.** 99 passed em 108,44 s.
120. **Testes PostgreSQL.** Service ponta a ponta, migration, ownership, CAS, review, dataset, export, retencao e isolamento passaram.
121. **Testes de feedback.** Categorias, target, idempotencia, update, complemento, retirada e expiracao passaram.
122. **Testes de redaction.** PII, segredos, controles, tamanho e CSV injection passaram.
123. **Testes de review.** Atribuicao, self-review, label, informacao, approval e rejection passaram.
124. **Testes de dataset.** Candidate validado, exemplo, v1, transicoes, publish, imutabilidade e streaming passaram.
125. **Testes de RBAC.** Matriz completa de roles e permissions passou.
126. **Testes de seguranca.** IDOR, payload estrito, segredo, injection, replay, stale version e campos proibidos passaram.
127. **Testes multi-tenant.** Target, feedback, candidate, dataset, cache e export permaneceram isolados.
128. **Testes cross-user.** Leitura, target, retirada e self-review cruzados foram bloqueados.
129. **Testes dos contratos V2.** Contratos analiticos e dos Prompts 03-11 permaneceram verdes.
130. **Testes temporais.** Corpus e normalizador temporal permaneceram verdes na regressao.
131. **Testes do planner.** Comparison Planner permaneceu verde.
132. **Testes do executor.** Comparison Executor permaneceu verde.
133. **Testes do renderer.** Renderer comparativo permaneceu verde; o gap historico DASH continua xfail.
134. **Testes conversacionais.** Conversation State e Context Resolution permaneceram verdes.
135. **Testes de Knowledge Base.** Enterprise Knowledge permaneceu verde.
136. **Testes de User Profile.** User Analytical Profile permaneceu verde.
137. **Cenario de quatro turnos.** O teste regular continuou aprovado com contexto versionado.
138. **Resultado dos goldens.** 21 cenarios deterministas de feedback passaram.
139. **Resultado dos schemas.** 69 schemas totais, 28 do Prompt 12, foram exportados duas vezes com hashes iguais.
140. **Resultado OpenAPI.** 149 paths e 173 operacoes, sendo 29 paths e 32 operacoes de feedback.
141. **Resultado ESLint.** Aprovado sem erro.
142. **Resultado TypeScript.** `tsc --noEmit` aprovado.
143. **Resultado build.** Next.js 16.2.10 compilou 19 paginas.
144. **Resultado Playwright.** 256 passed em desktop, tablet, mobile e ultrawide, exit code 0.
145. **Resultado AST.** 456 arquivos Python, 0 falhas.
146. **Resultado Docker config.** `docker compose -f docker-compose.test.yml config --quiet` aprovado.
147. **Oracle nao acessado.** Nenhum modulo ou teste do Prompt 12 abriu Oracle.
148. **OpenAI nao acessada.** Nenhum modulo ou teste do Prompt 12 chamou OpenAI.
149. **Banco operacional nao acessado.** Runner aceitou somente `127.0.0.1:55432/luminaai_test`.
150. **Nenhum treinamento executado.** Nao houve fine-tuning, alteracao de peso ou treino online/offline.
151. **Nenhum embedding criado.** Nao foi criada vector store, embedding ou busca semantica.
152. **Dependencias inalteradas.** Nenhum pacote foi adicionado ou atualizado.
153. **Lockfiles inalterados.** Nenhum lockfile foi modificado.
154. **Producao em LEGACY_ONLY.** Defaults e flags continuam fail-closed.
155. **Nenhum dataset analitico, SQL ou bind persistido.** Persistencia contem apenas referencias e artefatos supervisionados minimizados.
156. **Portas fechadas.** 55432, 3100, 3002 e 8000 foram confirmadas sem listener.
157. **Ambiente descartavel removido.** Container, network e volume de teste terminaram em zero.
158. **Deprecation ledger.** DEP-005 e DEP-006 registram legado e rollout com condicao objetiva de retirada.
159. **Technical debt register.** TD-005 preserva worker legal de exclusao; TD-006 registra benchmark futuro em massa operacional anonimizada.
160. **Comandos executados.** Git audit, safe pytest, schemas duplos, OpenAPI, AST, lint, tsc, build, Playwright, Docker config/down e scans de segredo foram executados.
161. **Comandos nao executados e motivo.** Migration produtiva, benchmark em dados reais, worker legal, treinamento e push nao foram executados por seguranca ou proibicao.
162. **Estado final do Git.** Branch `codex/phase-knowledge-prompts-10-13`, tudo unstaged, sem commit, tag ou push.
163. **git diff --stat.** Auditada ao final; inclui Prompts 10-12 e arquivos locais preexistentes porque o checkpoint da fase ocorre somente apos o Prompt 13.
164. **Arquivos protegidos preservados.** Blueprint e scripts start/stop voltaram exatamente aos hashes iniciais; `.env`, runtime logs e scripts operacionais nao foram incluidos.
165. **Limitacoes restantes.** Worker legal, benchmark com massa operacional e os dois gaps historicos permanecem explicitamente registrados.
166. **Proxima etapa.** Prompt 13 - Recuperacao semantica e resolucao governada de entidades, consumindo somente datasets offline aprovados.
