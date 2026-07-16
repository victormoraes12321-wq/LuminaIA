# Relatorio Final de Telemetria e Auditoria de Estresse Lógico - LuminaAI v2.0

Este relatorio contem a consolidacao da telemetria de execucao da bateria de 20 cenarios analiticos do novo pipeline.

## 1. Métricas Consolidadas de Performance

- **Taxa de Sucesso (Success Rate):** 100.0% (20/20 cenarios executados com status READY/UI_MODIFIED)
- **Latência Média Geral:** 2 ms
  - **Tempo Médio de IA (Fase 2 / Entrada & Explicabilidade):** 1 ms
  - **Tempo Médio de Resolução de Grafo/SQL:** 1 ms
- **Eficácia da Auto-Cura (Self-Healing):** 1 / 1 consulta vazia anomala recuperada com sucesso via re-planejamento conceitual

## 2. Distribuicao de Custo de Consulta (QueryCost Distribution)

- **LOW:** 13 queries (Consultas basicas e acoes locais de UI)
- **MEDIUM:** 4 queries (JOINs complexos de 2 views)
- **HIGH:** 3 queries (JOINs de 3-4 views com agregacoes no HAVING)
- **VERY_HIGH:** 0 queries (Queries com re-tentativas do loop de auto-cura)

## 3. Detalhes de Execucao por Cenario

| ID | Grupo | Pergunta | Status | Tempo (ms) | Custo | Erros / Justificativas |
|---|---|---|---|---|---|---|
| 1 | View Unica Base | Listar todos os clientes cadastrados. | **FULL_RENDERING** | 5 | LOW | - |
| 2 | View Unica Base | Mostrar as vendas realizadas no ano passado. | **FULL_RENDERING** | 5 | LOW | - |
| 3 | View Unica Base | Listar produtos da categoria Eletronicos. | **FULL_RENDERING** | 3 | LOW | - |
| 4 | View Unica Base | Quais parcelas financeiras estao em aberto? | **FULL_RENDERING** | 3 | LOW | - |
| 5 | View Unica Base | Ver o custo padrao de todos os produtos cadastrados. | **FULL_RENDERING** | 3 | LOW | - |
| 6 | Multi-View Dinamicas | Mostrar as vendas feitas para clientes de Sao Paulo. | **FULL_RENDERING** | 3 | MEDIUM | - |
| 7 | Multi-View Dinamicas | Quais produtos foram vendidos para clientes de Belo Horizonte? | **FULL_RENDERING** | 3 | MEDIUM | - |
| 8 | Multi-View Dinamicas | Quais parcelas financeiras estao associadas a vendas de produtos da categoria Alimentos? | **FULL_RENDERING** | 4 | HIGH | - |
| 9 | Multi-View Dinamicas | Mostrar o faturamento total por cliente no Rio de Janeiro. | **FULL_RENDERING** | 3 | MEDIUM | - |
| 10 | Multi-View Dinamicas | Quais parcelas estao em atraso para o cliente Marcos? | **FULL_RENDERING** | 3 | MEDIUM | - |
| 11 | Agrupamentos e HAVING | Clientes com compras acima de 10000 reais. | **FULL_RENDERING** | 7 | HIGH | - |
| 12 | Agrupamentos e HAVING | Vendas realizadas entre 2026-01-01 e 2026-06-30. | **FULL_RENDERING** | 3 | LOW | - |
| 13 | Agrupamentos e HAVING | Clientes localizados em SP, RJ ou MG. | **FULL_RENDERING** | 2 | LOW | - |
| 14 | Agrupamentos e HAVING | Listar produtos com custo padrao menor que 50 reais. | **FULL_RENDERING** | 2 | LOW | - |
| 15 | Agrupamentos e HAVING | Faturamento total por categoria de produto que seja superior a 50000 reais. | **FULL_RENDERING** | 5 | HIGH | - |
| 16 | Comandos de UI | troque o grafico para pizza | **UI_MODIFIED** | 0 | LOW | - |
| 17 | Comandos de UI | mude o layout para tabela | **UI_MODIFIED** | 0 | LOW | - |
| 18 | Comandos de UI | ordene ao contrario as linhas | **UI_MODIFIED** | 0 | LOW | - |
| 19 | Comandos de UI | paginar resultados | **UI_MODIFIED** | 0 | LOW | - |
| 20 | Comandos de UI | ir para proxima pagina | **UI_MODIFIED** | 0 | LOW | - |

## 4. Query SQL Gerada pelo Cenario 11 (Auto-Curado com HAVING)

```sql
SELECT VW_CLIENTES_CAD_LM.cliente_id, VW_CLIENTES_CAD_LM.nome, VW_CLIENTES_CAD_LM.cidade, VW_CLIENTES_CAD_LM.estado, VW_CLIENTES_CAD_LM.status_cliente, VW_VENDAS_LM.venda_id, VW_VENDAS_LM.cliente_id, VW_VENDAS_LM.produto_id, VW_VENDAS_LM.vendedor_id, VW_VENDAS_LM.valor_total, VW_VENDAS_LM.data_venda FROM VW_CLIENTES_CAD_LM INNER JOIN VW_VENDAS_LM ON VW_CLIENTES_CAD_LM.cliente_id = VW_VENDAS_LM.cliente_id WHERE VW_CLIENTES_CAD_LM.tenant_id = :tenant_id GROUP BY VW_CLIENTES_CAD_LM.cliente_id, VW_CLIENTES_CAD_LM.nome, VW_CLIENTES_CAD_LM.cidade, VW_CLIENTES_CAD_LM.estado, VW_CLIENTES_CAD_LM.status_cliente, VW_VENDAS_LM.venda_id, VW_VENDAS_LM.cliente_id, VW_VENDAS_LM.produto_id, VW_VENDAS_LM.vendedor_id, VW_VENDAS_LM.valor_total, VW_VENDAS_LM.data_venda HAVING VW_VENDAS_LM.valor_total > :param_0
```
