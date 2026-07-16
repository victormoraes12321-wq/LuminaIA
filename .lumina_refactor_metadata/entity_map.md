# Entity Map — LuminaAI
> Gerado automaticamente por script de validação de catálogo | Data: 2026-07-15

---

## Mapeamento de Entidades Lógicas para Views Físicas

| Entidade | Views Físicas Mapeadas | Dimensões Suportadas | Métricas Suportadas | Relacionamentos Diretos |
|----------|------------------------|----------------------|---------------------|------------------------|
| Cliente | VW_CLIENTES_CAD_LM, VW_VENDAS_LM, VW_FINANCEIRO_LM | nome, tpcli, razao_ |  | Venda, Financeiro |
| Produto | VW_PRODUTOS_CAD_LM, VW_VENDAS_LM | nome_produto, descricao, descricao_ | estoque | Venda |
| Venda | VW_VENDAS_LM | dtemissao_, nota_ | ptotal_, qtde_ | Cliente, Produto, Vendedor |
| Vendedor | VW_VENDEDOR_CAD_LM, VW_VENDAS_LM | nome_ved, nome_ |  | Venda |
| Financeiro | VW_FINANCEIRO_LM | status_pagamento, data_vencimento | valor_parcela | Cliente |
| Cidade | VW_CLIENTES_CAD_LM, VW_VENDEDOR_CAD_LM | nome_cidade, muni_ved |  | Cliente, Vendedor |
| Estado | VW_CLIENTES_CAD_LM | uf |  | Cliente |
| Categoria | VW_PRODUTOS_CAD_LM | familia |  | Produto |
