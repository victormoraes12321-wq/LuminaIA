# ADR 0005 - Guardrail Deterministico Para Perguntas Criticas De Vendas

Status: Aceita

## Contexto

Perguntas como faturamento do mes, ticket medio, desconto total, desconto medio, maior vendedor e top clientes sao usadas operacionalmente e precisam retornar numeros corretos e previsiveis. O fluxo generativo pode interpretar linguagem natural, mas nao deve ser a unica camada responsavel por indicadores criticos quando o periodo e a metrica estao claros.

Tambem havia regras de negocio especificas que precisavam ser preservadas:

- `PADRAO` representa cadastro tecnico e nao deve vencer ranking de vendedores.
- `LAGES E LOPES LTDA` representa a loja interna e nao deve aparecer como top cliente externo.
- Perguntas subsequentes na mesma conversa podem depender do periodo perguntado antes.

## Decisao

O `NewQueryOrchestrator` mantem um caminho deterministico para perguntas criticas de vendas quando houver periodo explicito ou periodo herdado do contexto da conversa.

Esse caminho:

- Executa consultas SQL controladas no backend.
- Calcula faturamento e ticket medio de forma deterministica.
- Para desconto, usa coluna explicita quando a `vw_vendas_lm` expuser `desconto_total`, `valor_desconto`, `vl_desconto`, `vldesconto`, `vldesc` ou `desconto`.
- Quando a view nao expuser desconto real, informa baixa confianca e usa apenas a derivacao `qtde_ * p_unit_ - ptotal_` como diagnostico, sem afirmar que o ERP nao possui desconto.
- Usa o filtro comercial padrao (`tp_ IN (2, 61)`) para nao somar saidas RB, bonificacoes e transferencias como faturamento principal.
- Classifica saida RB e devolucao separadamente: RB usa `tp_ = 9` ou descricao `SAIDA RB`; devolucao usa descricao contendo `DEVOL`.
- Mantem transferencias (`tp_` 3, 31 e 96, ou descricao de transferencia) separadas e fora de faturamento, lucro e `total_bruto`; `total_movimentos_view` existe apenas para auditoria operacional.
- Trata `filial_` como dimensao padrao: perguntas de total consolidam todas as filiais e exibem a abertura por filial; perguntas que citam filial/loja/unidade aplicam esse filtro explicitamente.
- Em rankings, evita repetir o mesmo vendedor/cliente em varias linhas: a saida padrao e uma linha por ranqueado, colunas por filial e colunas de total no fim da linha.
- Mantem a saida padrao enxuta; detalhes operacionais como saida RB, devolucao, bonificadas, transferencias, outras vendas, remessa/uso e consumo, outros movimentos, total bruto sem transferencias e total geral de movimentos so aparecem quando a pergunta solicitar essa abertura.
- Usa o modulo `sales_value_breakdown` para preservar os movimentos separados sem mistura-los ao faturamento comercial principal.
- Trata saida RB e devolucao como metricas consultaveis independentes, inclusive em resumo por periodo, ranking/top por vendedor e continuidade de conversa.
- Herda periodo, metrica e dimensao em perguntas subsequentes quando o usuario usa referencias como `esse dado`, `esse ranking` ou `agora separa por vendedor`.
- Diferencia base de valor em faturamento: liquida/comercial, bruta ou ambas. Lucro e vendas ainda nao faturadas exigem fonte propria; quando a view nao tem os campos necessarios, o sistema retorna aviso em vez de inventar o indicador.
- Usa descoberta explicita de fonte para lucro e vendas ainda nao faturadas via `financial_source_discovery`; a resposta pode informar candidatos parciais, mas so calcula quando houver mapeamento ativo e formula homologada.
- Disponibiliza reconciliacao ERP x clone via `erp_reconciliation`, cobrindo faturamento, filial por filial, ranking vendedores, RB, devolucao, ticket medio, top clientes e filtros oficiais.
- A sincronizacao da view de vendas deve reprocessar janela recente por `dtemissao_` no modo incremental, pois o mes corrente pode receber registros tardios no mesmo dia sem mudar a maior data do clone.
- Respeita visualizacao solicitada no texto quando houver pedido de tabela, grafico, pizza, linha ou tabela+grafico.
- Aplica modos de resposta no caminho deterministico: operacional, analitico e executivo.
- Limita ranking de clientes a top 50 quando o usuario nao pede `top N`, `todos` ou `sem limite`, evitando respostas gigantes por padrao.
- Aplica exclusoes de negocio para ranking.
- Diferencia formato de saida: perguntas `maior/top` retornam lider; perguntas `ranking/lista/todos/por vendedor` retornam tabela ordenada.
- Usa `session_id`, historico recente e `parent_id` para continuidade.
- Entrega payload compatibilidade `QueryResponse`/dashboard sem delegar calculo ao frontend.

## Consequencias

- Indicadores criticos ficam mais previsiveis.
- A resposta nao perde dados operacionais: quando houver movimentos fora do faturamento comercial padrao, eles aparecem separados para reconciliacao com relatorios do ERP.
- Desconto so deve ser tratado como indicador financeiro confiavel quando a view do ERP trouxer coluna propria de desconto ou preco bruto/lista suficiente para recomposicao.
- A IA continua responsavel por interpretacao, contexto e resposta, mas nao substitui calculo deterministico quando o caso e claro.
- Mudancas futuras nessas perguntas devem ter teste/regressao focada.
- Mudancas em filtros de faturamento, RB, devolucao, bonificacao, transferencia, CFOP, cancelamento ou status devem passar pelo relatorio `scripts/run_erp_reconciliation.py` e registrar deltas contra o ERP.
- Novas fontes de lucro ou vendas nao faturadas devem passar pelo contrato de descoberta antes de serem ativadas no chat.
- Novas excecoes de negocio devem ser documentadas aqui, no changelog e em `docs/current-status.md`.
