# Metric Map — LuminaAI
> Gerado automaticamente por script de validação de catálogo | Data: 2026-07-15

---

## Catálogo de Métricas Canônicas (Verdade Única de Negócio)

| Métrica Canônica | Descrição | Tipo de Dado | Coluna Física | View Física | Unidade | Agregações Permitidas |
|------------------|-----------|--------------|---------------|-------------|---------|-----------------------|
| Receita | Faturamento bruto total em vendas | Currency | ptotal_ | VW_VENDAS_LM | BRL | SUM, AVG, MIN, MAX |
| Quantidade | Quantidade de itens físicos vendidos | Quantity | qtde_ | VW_VENDAS_LM | un | SUM, AVG, MIN, MAX |
| Estoque | Posição de estoque atual física cadastrada do produto | Quantity | estoque | VW_PRODUTOS_CAD_LM | un | SUM, AVG, MIN, MAX |
| Valor Parcela | Valor unitário ou total de parcelas financeiras em aberto/pagas | Currency | valor_parcela | VW_FINANCEIRO_LM | BRL | SUM, AVG, MIN, MAX |
