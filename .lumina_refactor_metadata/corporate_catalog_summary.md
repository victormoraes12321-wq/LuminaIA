# Corporate Catalog Summary — LuminaAI
> Gerado automaticamente por script de validação de catálogo | Data: 2026-07-15 | Versão: 2.0

---

## Estatísticas Gerais do Catálogo (CKC)

- **Total de Views Catalogadas**: 5
- **Total de Entidades de Negócio**: 8
- **Total de Métricas Canônicas**: 4
- **Total de Dimensões Canônicas**: 7
- **Total de Aliases Mapeados**: 26
- **Total de Relacionamentos do Grafo**: 4
- **Total de Anomalias/Erros Encontrados**: 2

---

## Detalhamento de Views Analíticas

| View | Tipo | PK | Qtd. Colunas | Granularidade |
|------|------|----|--------------|---------------|
| VW_CLIENTES_CAD_LM | CADASTRAL | codigo | 6 | Um registro por cliente (codigo) |
| VW_VENDAS_LM | TRANSACTIONAL | nota_ | 11 | Um registro por item de nota fiscal (nota_ + codprod_) |
| VW_PRODUTOS_CAD_LM | CADASTRAL | codigo | 5 | Um registro por produto (codigo) |
| VW_VENDEDOR_CAD_LM | CADASTRAL | codi_ved | 3 | Um registro por vendedor (codi_ved) |
| VW_FINANCEIRO_LM | TRANSACTIONAL | financeiro_id | 5 | Um registro por parcela (financeiro_id) |
