# Dimension Map — LuminaAI
> Gerado automaticamente por script de validação de catálogo | Data: 2026-07-15

---

## Catálogo de Dimensões Canônicas

| Dimensão | Tipo de Dimensão | Coluna Física | View Física | Hierarquia Downstream |
|-----------|------------------|---------------|-------------|----------------------|
| Cliente | Entity | nome | VW_CLIENTES_CAD_LM |  |
| Produto | Entity | nome_produto | VW_PRODUTOS_CAD_LM | familia |
| Vendedor | Entity | nome_ved | VW_VENDEDOR_CAD_LM |  |
| Cidade | Geography | nome_cidade | VW_CLIENTES_CAD_LM | uf |
| Estado | Geography | uf | VW_CLIENTES_CAD_LM |  |
| Categoria | Entity | familia | VW_PRODUTOS_CAD_LM |  |
| Data | Time | dtemissao_ | VW_VENDAS_LM | Mês, Ano |
