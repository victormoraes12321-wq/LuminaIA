# Prompt 08 - Estado Conversacional Escalavel No PostgreSQL

Data da auditoria: 2026-07-28.

## Relatorio Obrigatorio

1. **Resumo da implementacao.** O estado conversacional estruturado passou a
   poder usar PostgreSQL como autoridade duravel, com rollout governado e
   producao ainda em `LEGACY_ONLY`.
2. **Arquitetura final.** HTTP autenticado -> query/conversations router ->
   service transacional -> repository tenant+usuario -> cinco tabelas
   PostgreSQL; o pipeline analitico executa fora das transacoes.
3. **Arquivos criados.** Contratos em
   `backend/contracts/conversation_state_v2/`, model, router, schema, migration
   v12, service/repository/protector/importador, CLI, testes, golden, ADR,
   contrato, runbook e este relatorio.
4. **Arquivos alterados.** Config, registro de models, `User`, `main`, query
   router, orquestrador, conversation graph, QueryRequest/QueryResponse,
   hook/tipos frontend, AuthContext, documentacao e baseline.
5. **Versao do estado conversacional.** `lumina.conversation-state/1.0`.
6. **Contratos criados.** Estado, sessao, node, snapshot, evento, turn start,
   completion/failure, conflito, load/mutation, retention e import result.
7. **Models criados.** `ConversationSession`, `ConversationNodeRecord`,
   `ConversationStateSnapshot`, `ConversationEvent` e
   `ConversationLegacyImport`.
8. **Tabelas criadas.** `conversation_sessions`, `conversation_nodes`,
   `conversation_state_snapshots`, `conversation_events` e
   `conversation_legacy_imports`.
9. **Constraints.** Owner composto, status/enums, versoes nao negativas,
   sequence, expiry, parent/head same-session, timestamps e unicidades.
10. **Indices.** Owner+atividade, status+expiry, session+sequence,
    session+parent, client message parcial, snapshots, eventos e ledger.
11. **Migration criada.** `migration_v12_0.py`, SQL explicito e transacional,
    independente de `create_all`.
12. **Resultado da migration up.** Aprovado apenas no PostgreSQL 17
    descartavel em `127.0.0.1:55432/luminaai_test`.
13. **Resultado da execucao idempotente.** Dois `up` consecutivos aprovados.
14. **Resultado da migration down em teste.** Down guardado, aprovado em
    ambiente de teste, seguido por novo up aprovado.
15. **Repository.** Todas as leituras de sessao/node/snapshot usam
    `tenant_id`, `user_id` e identidade de sessao.
16. **Service.** Transacoes curtas, protecao de conteudo, erros tipados,
    idempotencia, CAS, lifecycle e retention.
17. **Transacao de inicio.** Resolve identidade, bloqueia sessao, valida
    status/parent/versao, grava query+evento e libera antes do pipeline.
18. **Transacao de conclusao.** Bloqueia sessao, valida query/base, grava
    resposta, CAS, snapshot e eventos atomicamente.
19. **Compare-and-swap.** `context_version` esperada e status ativo fazem parte
    do `UPDATE`; conflito nao sobrescreve estado.
20. **Concorrencia.** Vinte operacoes simultaneas produziram sequence unica,
    um vencedor e 19 conflitos tipados.
21. **Turnos fora de ordem.** O segundo completion com base antiga foi
    recusado como `CONTEXT_VERSION_CONFLICT`.
22. **Idempotencia.** Replay com mesmo client ID e conteudo retorna os nodes
    existentes; conteudo diferente e recusado.
23. **Session ID.** Gerado no servidor quando ausente, imprevisivel e nunca
    concede acesso sem owner autenticado.
24. **Client message ID.** UUID obrigatorio no fluxo novo e reutilizado pelo
    retry automatico do frontend.
25. **Nodes.** Append-only para queries, respostas, erro, reset e eventos de
    sistema; conteudo nao e autoridade analitica.
26. **Snapshots.** Estado estruturado versionado e checksummed, sem dataset,
    SQL, binds ou payload de debug.
27. **Events.** Ledger minimo com tipo, versoes, node/fingerprint e metadata
    sanitizada.
28. **Context version.** Incrementa por completion/reset/import e participa do
    CAS e do contrato HTTP.
29. **Context epoch.** Incrementa em reset para separar contextos anteriores.
30. **Active head.** FK composta garante que o head pertence a mesma sessao.
31. **Branches.** Parent antigo da mesma sessao foi aceito; parent externo foi
    recusado.
32. **Reset.** Limpa estado sem apagar auditoria, cria node RESET, incrementa
    epoch/version e troca o head.
33. **Archive.** Bloqueia novos/completing turns e registra evento.
34. **Reopen.** Somente sessao arquivada volta a ACTIVE com novo TTL.
35. **Expiration.** Detectada e persistida no acesso; a sessao expirada nao
    aceita novo turno.
36. **Soft delete.** Marca `DELETED`, registra data/evento e some da listagem.
37. **Purge.** Remove em lote somente soft deletes anteriores ao cutoff, por
    cascade, e nunca foi executado em producao.
38. **Retention.** TTL/cutoffs/lote governados; dry-run, elegibilidade,
    idempotencia e limite foram testados.
39. **Criptografia ou minimizacao.** Fernet autenticado para texto permitido;
    SQL e padroes de segredo sao redigidos antes de persistir.
40. **Politica de chave.** Chave obrigatoria quando persistencia esta ativa,
    versao gravada por node e falha fechada sem chave/corrupcao.
41. **SearchHistory.** Permanece separado; node guarda somente FK opcional.
42. **SemanticMemory.** Permanece separada e nao e usada como snapshot/grafo.
43. **Compatibilidade com JSON legado.** Disponivel em `LEGACY_ONLY`; autoridade
    PostgreSQL usa adapter stateless e nao escreve JSON.
44. **Importador.** Um arquivo explicito, checksum, validacao/ciclo, dry-run
    default, flag desligada, owner exigido e ledger contra duplicacao.
45. **Rollout modes.** `LEGACY_ONLY`, `SHADOW_WRITE`,
    `DUAL_WRITE_LEGACY_READ`, `POSTGRES_READ_WRITE` e `POSTGRES_ONLY`.
46. **Shadow mode.** PostgreSQL pode receber escrita sem mudar resposta legada;
    falha shadow nao derruba o fluxo de usuario.
47. **Rollback.** Alterar a unica flag para `LEGACY_ONLY`; dados v12 ficam
    preservados para auditoria.
48. **Integracao com o orquestrador.** Autoridade PostgreSQL injeta
    `ConversationStateV2` e usa graph adapter sem estado local.
49. **Integracao com QueryRequest.** Campos aditivos `client_message_id` e
    `expected_context_version`; session/history/parent legados preservados.
50. **Integracao com QueryResponse.** Session, query/response node, parent,
    version, epoch, status e replay sao aditivos.
51. **Integracao frontend.** Hook propaga contrato server-side, parent de
    resposta e versao; retry usa o mesmo body/UUID.
52. **LocalStorage.** Somente session ID, context version e parent, em chave
    `tenant_id:user_id`; nenhum historico e autoridade.
53. **Logout.** Remove todas as chaves `lumina-conversation:*`.
54. **Troca de usuario e tenant.** Chaves sao isoladas e o backend revalida o
    owner em toda operacao.
55. **APIs criadas ou alteradas.** CRUD/lifecycle em `/conversations`,
    `/nodes`, `/reset`, `/archive`, `/reopen`; `/query` recebeu metadata
    aditiva.
56. **Paginacao.** Sessoes usam cursor composto atividade+UUID; nodes usam
    sequence; ambos possuem limite.
57. **Recovery.** Falha vira node ERROR seguro; retry e replay sao
    idempotentes; frontend trata conflict/expired/archive/delete tipados.
58. **Checksum.** SHA-256 deterministico exclui somente `updated_at`; adulteracao
    de snapshot foi detectada.
59. **Observabilidade.** Eventos, fingerprints, versions e status permitem
    diagnostico sem registrar pergunta/resposta em claro.
60. **Cache.** Nenhum cache RAM e autoridade; default consistente e sem cache
    conversacional distribuido.
61. **Multi-replica.** Duas instancias do service compartilharam estado apenas
    via PostgreSQL e resolveram replay/conflito.
62. **Reinicio.** Recriacao completa do service preservou head, nodes,
    snapshot e versao.
63. **Performance.** Append de mil nodes e paginacao 100+100 ficaram abaixo do
    limite de 30 s; vinte operacoes concorrentes foram aprovadas.
64. **Golden states.** Dezesseis casos versionados: vazio, primeiro turno,
    simples, comparacao, multi-periodo, reset, branch, clarification, error,
    timeout, archived, expired, import, conflict, replay e quatro turnos.
65. **Testes criados.** 27 backend dedicados e 24 casos Playwright
    conversacionais (seis cenarios x quatro viewports), alem da regressao total.
66. **Total backend coletado.** 997 testes.
67. **Total backend aprovado.** 994 aprovados.
68. **Total de falhas.** Zero na certificacao final.
69. **Total de xfails.** Tres, todos strict e preexistentes.
70. **Total de XPASS.** Zero.
71. **Cada xfail removido.** `LUMINA-GAP-CONTEXT-002`; o teste agora e regular
    e confirma ausencia do cache `_last_semantic_plans`.
72. **Cada xfail mantido.** `DASH-001`, parte semantica de `CONTEXT-001` e
    `TENANT-001`, todos fora do escopo permitido.
73. **Resultado de CONTEXT-002.** Aprovado sem xfail; o cache local nao e
    recriado.
74. **Resultado da parte persistente de CONTEXT-001.** Quatro turnos,
    snapshots, markers, parent e restart aprovados.
75. **Parte restante para o Prompt 09.** Heranca/resolucao automatica de ano,
    filial, metrica, periodos comparados e dimensao.
76. **Resultado do cenario de quatro turnos.** Versao final 4, head correto e
    markers completos apos quatro instancias independentes.
77. **Estado persistido apos cada turno.** Snapshots 1, 2, 3 e 4 confirmados.
78. **Resultado apos reinicio.** Estado integral restaurado por nova instancia.
79. **Resultado com duas replicas.** Replay e conflito consistentes sem RAM
    compartilhada.
80. **Resultado de dois writers.** Um completion venceu e o outro recebeu
    conflito; sem last-write-wins.
81. **Resultado de replay idempotente.** Mesmos query/response nodes, sem nova
    execucao.
82. **Resultado de conflito.** Erro tipado inclui versao atual e frontend a
    usa na proxima tentativa.
83. **Resultado cross-tenant.** Sessao alheia nao foi encontrada/vinculada.
84. **Resultado cross-user.** Load/archive/delete/reset alheios retornaram
    not-found.
85. **Resultado de parent cross-session.** `INVALID_PARENT`, com rollback sem
    node residual.
86. **Resultado de sessao expirada.** Status/evento persistidos e novo turno
    recusado.
87. **Resultado de reset.** Epoch/version/head/snapshot e timestamp aprovados;
    logo inicia novo binding.
88. **Resultado de importacao legada.** Dry-run, apply sintetico, ancestry,
    ledger e duplicate replay aprovados; apply sem flag recusado.
89. **Resultado de retention.** Dry-run nao alterou dados; candidatos e lotes
    foram contados corretamente.
90. **Resultado de purge.** Dois lotes de tamanho um removeram sessoes e
    ciphertext dependente; ativa permaneceu.
91. **Resultado de conteudo sem chave.** Falha fechada; corrupcao e key version
    divergente tambem recusadas.
92. **Resultado dos testes de seguranca.** Owner, ID forjado, parent, payload,
    segredo, SQL, checksum e replay divergente aprovados.
93. **Resultado dos testes multi-tenant.** Suite integral aprovada, exceto o
    `TENANT-001` preexistente do core summary explicitamente mantido.
94. **Resultado dos contratos V2.** Analytical V2 e conversation state 1.0
    aprovados, strict, imutaveis e com versao desconhecida recusada.
95. **Resultado dos testes temporais.** 99 aprovados, autoridade temporal
    inalterada.
96. **Resultado dos testes do planner.** 66 dedicados aprovados, planner
    inalterado.
97. **Resultado dos testes do executor.** 233 dedicados aprovados, executor
    inalterado.
98. **Resultado do renderer.** Presentation model/renderer comparativo
    continuaram aprovados nos quatro viewports.
99. **Resultado do ESLint.** Aprovado, zero erros e zero warnings.
100. **Resultado do TypeScript.** `tsc --noEmit` aprovado.
101. **Resultado do build.** Next.js 16.2.10 aprovado, 15 rotas.
102. **Resultado do Playwright.** 192 aprovados na matriz final em desktop,
     tablet, mobile e ultrawide, porta isolada 3100.
103. **Resultado dos schemas.** Pydantic/OpenAPI/import smoke aprovados; rotas
     registradas.
104. **Resultado do AST.** Arquivos Python alterados parseados sem erro.
105. **Confirmacao de que Oracle nao foi acessado.** Confirmado; mock e network
     guard permaneceram ativos.
106. **Confirmacao de que OpenAI nao foi acessada.** Confirmado; provider mock e
     network guard permaneceram ativos.
107. **Confirmacao de que banco operacional nao foi acessado.** Confirmado pela
     guarda; somente `127.0.0.1:55432/luminaai_test`.
108. **Confirmacao de que nenhuma dependencia foi adicionada.** Confirmado.
109. **Confirmacao de que nenhum lockfile foi alterado.** Confirmado.
110. **Confirmacao de que nenhum dataset foi persistido.** Confirmado por
     contrato/model/importador e testes.
111. **Confirmacao de que nenhum SQL ou bind foi persistido.** Confirmado;
     conteudo SQL e redigido e snapshots nao possuem esses campos.
112. **Comandos executados.** Runner seguro pytest (coleta, selecoes e suite
     completa), migration test, AST/import/OpenAPI, ESLint, TypeScript, build,
     Playwright direcionado e completo, `git diff --check/status/stat`.
113. **Comandos nao executados e motivo.** Migration/rollout/purge operacional,
     Oracle/OpenAI reais, `test:load` contra 8000, instaladores, firewall,
     commit/reset/clean; todos proibidos ou desnecessarios nesta etapa.
114. **Estado final do Git.** Worktree permanece intencionalmente suja com
     alteracoes preexistentes de prompts anteriores; nada foi revertido,
     staged ou commitado.
115. **git diff --stat.** O stat global registrou 61 arquivos versionados,
     9.544 insercoes e 855 remocoes. Ele inclui trabalho preexistente de outras
     etapas e nao contabiliza untracked, portanto nao representa autoria
     exclusiva do Prompt 08.
116. **Limitacoes restantes.** Heranca semantica e `CONTEXT-001`, dashboard
     `DASH-001`, isolamento do core summary `TENANT-001`, scheduler desativado e
     rollout/migration operacional ainda nao aplicados.
117. **Proxima etapa.** `Prompt 09 - Motor de heranca e resolucao de contexto`.

## Veredito

O PostgreSQL esta apto a ser a fonte de verdade conversacional quando o rollout
for deliberadamente ativado apos migration operacional aprovada. O default de
producao continua seguro em `LEGACY_ONLY`; nao houve ativacao automatica,
migration operacional, acesso externo, dependencia nova ou lockfile alterado.
