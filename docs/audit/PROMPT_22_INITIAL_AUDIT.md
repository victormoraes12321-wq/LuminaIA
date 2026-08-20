# Prompt 22 — Auditoria inicial

Data da auditoria: 2026-08-05. Branch travada: `codex/phase-dashboard-prompts-19-22`. HEAD travado: `14e13bc886372690d144addc255c1ec60d59e62a`.

1. Os componentes reutilizáveis são Dashboard Blueprint V2, Dashboard Backend V2, Dashboard UI/side chat, AI Orchestration, AI Tool Registry, MetricRegistry, Enterprise Knowledge, Semantic Retrieval, Temporal Normalizer, Validation & Provenance, Supervised Feedback e Conversation State.
2. Os providers existentes são roteados pelo AI Orchestration; testes usam provider fake determinístico e o Prompt 22 não deve criar cliente de modelo paralelo.
3. Os contratos genéricos de proposta do AI Orchestration usam payload JSON deliberadamente genérico e não satisfazem o contrato de domínio estrito do Prompt 22.
4. O AI Tool Registry já possui capacidades semânticas e temporais, mas também ferramentas analíticas; o Prompt 22 precisa de uma allowlist de domínio mais estreita, sem execução analítica.
5. MetricRegistry é a autoridade de métricas e fingerprints de fórmula; fórmulas não devem atravessar a fronteira do provider.
6. As dimensões devem ser resolvidas pelo catálogo analítico publicado e pelas referências publicadas, sem aceitar identificadores físicos ou inventados.
7. Enterprise Knowledge possui projeção published-only, limitada e com proveniência para a fronteira de intenção.
8. Semantic Retrieval já preserva ambiguidade, opções canônicas, token assinado, expiração e escopo tenant/user/session.
9. Clarifications do Prompt 22 precisam de persistência própria porque também cobrem objetivo, período, layout e parâmetros de widget, não apenas entidades semânticas.
10. AI Orchestration v19 persiste runs, steps, invocations, tool calls, uso e avaliação, mas não o agregado de proposta de dashboard.
11. Os budgets existentes cobrem tokens, tempo, ferramentas, custo, contexto e saída; o Prompt 22 deve impor limites adicionais de proposta e widgets.
12. A retenção deve guardar somente intenção normalizada, versões, evidências públicas e decisões; prompt bruto e chain of thought não serão persistidos.
13. Prompt injection pode entrar por solicitação, label, aliases, Knowledge e tool results; todo texto externo será tratado como dado, delimitado, limitado e nunca como instrução.
14. Métrica inventada será bloqueada por resolução em allowlist e validação contra MetricRegistry/catálogo antes da síntese.
15. Cross-tenant será bloqueado por contexto derivado do token, FKs compostas, filtros de repositório e testes negativos.
16. Autoaplicação será bloqueada pela máquina de estados: `READY_FOR_REVIEW` exige decisão humana para `ACCEPTED`, seguida de chamada de aplicação separada.
17. Publicação automática não faz parte das operações, contratos, tools, serviços ou rotas do Prompt 22.
18. Prompt bruto não será armazenado por padrão; somente fingerprint, resumo sanitizado e intent tipado poderão persistir.
19. Duplicações serão evitadas reutilizando canonicalização/validação do Prompt 19, autoria/patches do Prompt 20 e apresentação visual do Prompt 21.
20. Migration v23 é necessária: v19 não representa versões imutáveis, clarifications, evidências, decisões, referências de aplicação, CAS e idempotência tenant-scoped exigidos. A v23 será aditiva, explícita, idempotente, excluída de `create_all` e terá down apenas para PostgreSQL descartável de teste.

Decisão: implementar `lumina.dashboard-ai-assistance/1.0` como camada de propostas, sem autoridade numérica, SQL, publicação, aprovação, rollback, ownership, colaboração ou concessão de permissões. Produção permanece `LEGACY_ONLY`.
