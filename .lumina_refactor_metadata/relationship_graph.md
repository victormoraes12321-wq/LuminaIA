# Relationship Graph — LuminaAI
> Gerado automaticamente por script de validação de catálogo | Data: 2026-07-15

---

## Grafo de Adjacência de Junção Físico

```mermaid
graph TD
    classDef fact fill:#f9f,stroke:#333,stroke-width:2px;
    classDef dim fill:#bbf,stroke:#333,stroke-width:1px;

    VW_CLIENTES_CAD_LM["VW_CLIENTES_CAD_LM (Dimensão)"]:::dim
    VW_VENDAS_LM["VW_VENDAS_LM (Fatos)"]:::fact
    VW_PRODUTOS_CAD_LM["VW_PRODUTOS_CAD_LM (Dimensão)"]:::dim
    VW_VENDEDOR_CAD_LM["VW_VENDEDOR_CAD_LM (Dimensão)"]:::dim
    VW_FINANCEIRO_LM["VW_FINANCEIRO_LM (Fatos)"]:::fact

    VW_VENDAS_LM -- "codcliente_ <-> codigo (Distância: 1)" --> VW_CLIENTES_CAD_LM
    VW_VENDAS_LM -- "codprod_ <-> codigo (Distância: 1)" --> VW_PRODUTOS_CAD_LM
    VW_VENDAS_LM -- "rca_ <-> codi_ved (Distância: 1)" --> VW_VENDEDOR_CAD_LM
    VW_FINANCEIRO_LM -- "cliente_id <-> codigo (Distância: 1)" --> VW_CLIENTES_CAD_LM
```

---

## Estatísticas de Caminhos de JOIN

- **Total de Relacionamentos Diretos Mapeados**: 4
- **Cardinalidades Cadastradas**: N:1, 1:N
- **Provedor de Junções**: `PlannerEngine` (BFS Dijkstra BFS Graph)
