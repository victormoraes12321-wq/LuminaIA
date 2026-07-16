# Validation Report — LuminaAI
> Gerado automaticamente por script de validação de catálogo | Data: 2026-07-15

---

## Resumo Executivo de Saúde do Catálogo

- **Total de Erros/Alertas**: 2
- **Anomalias Críticas**: 0 (impede funcionamento ou gera queries inválidas)
- **Erros Graves**: 0 (inconsistências lógicas que precisam de atenção)
- **Alertas / Avisos**: 2 (alertas de tipo de dados ou performance)

---

## Lista Completa de Inconsistências Detectadas

| Gravidade | Tipo de Anomalia | Elemento Afetado | Descrição do Problema |
|-----------|------------------|------------------|-----------------------|
| WARNING | TYPE_MISMATCH_JOIN | VW_VENDAS_LM <-> VW_PRODUTOS_CAD_LM | Tipo incompatível no JOIN: codprod_ (ColumnDataType.NUMERIC) vs codigo (ColumnDataType.TEXT). Requer cast explícito. |
| WARNING | TYPE_MISMATCH_JOIN | VW_PRODUTOS_CAD_LM <-> VW_VENDAS_LM | Tipo incompatível no JOIN: codigo (ColumnDataType.TEXT) vs codprod_ (ColumnDataType.NUMERIC). Requer cast explícito. |
