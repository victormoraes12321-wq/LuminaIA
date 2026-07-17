# Estado Atual Do Sistema

Data da atualizacao: 2026-07-17

Este documento resume o estado atual do LuminaAI apos as correcoes recentes de perguntas criticas, continuidade de conversa, ranking, descontos, login/sessao e encoding de textos.

## Resumo Executivo

O sistema permanece estruturado como uma plataforma Enterprise de BI com IA, backend FastAPI, frontend Next.js, Data Platform, catalogos, runtime de dashboards e governanca multi-tenant.

A certificacao completa de 2026-07-09 continua registrada como baseline historico. Em 2026-07-17 foram feitas validacoes incrementais focadas nas falhas reportadas pelo usuario e nas alteracoes recentes do codigo.

## Correcoes Recentes Validadas

- Perguntas criticas de vendas ganharam caminho deterministico no `NewQueryOrchestrator` quando ha periodo explicito ou periodo herdado da conversa.
- Consultas de faturamento, ticket medio, descontos, maior vendedor e maior cliente usam regras estaveis sobre `vw_vendas_lm`.
- Ranking de vendedor desconsidera o cadastro tecnico `PADRAO`.
- Ranking/top cliente desconsidera `LAGES E LOPES LTDA` quando a pergunta pede cliente externo, pois esse nome representa a loja interna.
- Desconto total e desconto medio usam derivacao deterministica por item: `quantidade * preco_unitario - valor_faturado`, limitado para nao somar desconto negativo.
- Continuidade de conversa envia `session_id`, historico recente e `parent_id`, permitindo herdar periodo em perguntas subsequentes.
- Clique na logo do sistema chama `resetConversation` e limpa a conversa atual.
- Textos do frontend e payloads vindos da API passam por reparo defensivo de encoding antes de renderizar.
- Labels tecnicos como `observacao`, `ticket_medio` e `valor_formatado` sao humanizados para exibicao.
- `getApiBase()` preserva o mesmo host loopback usado no navegador (`localhost` ou `127.0.0.1`) para evitar perda de cookie de sessao.

Decisao arquitetural relacionada: [ADR 0005 - Guardrail deterministico para perguntas criticas de vendas](adrs/0005-deterministic-critical-sales-queries.md).

## Perguntas Prioritarias Cobertas

As seguintes familias de perguntas devem ser tratadas como superficie critica de regressao:

- Faturamento do mes.
- Faturamento do mes anterior.
- Venda por vendedor.
- Qual vendedor teve maior venda.
- Qual vendedor com maior desconto.
- Qual foi nosso desconto.
- Total de desconto.
- Desconto medio.
- Ticket medio.
- Ranking/top clientes, excluindo a loja interna quando aplicavel.
- Perguntas de continuidade na mesma conversa, herdando periodo quando a pergunta seguinte for curta ou ambigua.

## Validacao Incremental Executada Em 2026-07-17

| Validacao | Resultado |
| --- | --- |
| `python -m py_compile` em orquestrador, resolver e transformer | OK |
| `npm run build` no frontend | OK |
| Geracao de `docs/api-reference.md` e `docs/source-inventory.md` com Python do backend | OK |
| E2E Playwright abrindo `http://127.0.0.1:3000/login` | OK |
| Login, hidratacao de sessao e redirecionamento para `/dashboard` via `127.0.0.1` | OK |
| Pergunta real `Faturamento e ticket medio em 06/2026` | OK |
| Renderizacao com `Resumo do período`, `ticket médio`, `Painel Analítico`, `Confiança` e `Observação` sem mojibake | OK |
| Backend temporario usado no teste | Encerrado apos a validacao |

## Observacoes De Escopo

- A bateria completa de regressao registrada em 2026-07-09 nao foi reexecutada integralmente nesta rodada de documentacao.
- Docker, carga produtiva, backup/restore real e `EXPLAIN ANALYZE` com massa real continuam dependentes do ambiente final.
- Arquivos de backup, logs e relatorios historicos podem manter conteudo antigo por rastreabilidade; documentos oficiais apontam para este estado atual quando houver divergencia.
