# Metrics Catalog — LuminaAI
> Auditoria estática completa | Data: 2026-07-15 | Versão do Pipeline: 2.0

---

## Resumo

| Métrica | View Física | Campo Físico | Tipo | Quem Usa |
|---------|------------|-------------|------|---------|
| Faturamento / Receita | VW_VENDAS_LM | ptotal_ | numeric | Todos os pipelines |
| Quantidade Vendida | VW_VENDAS_LM | qtde_ | numeric | Pipelines de volume |
| Preço Unitário | VW_VENDAS_LM | p_unit_ | numeric | Análises de preço |
| Estoque | VW_PRODUTOS_CAD_LM | estoque | numeric | Análises de produto |
| Valor da Parcela | VW_FINANCEIRO_LM | valor_parcela | numeric | Módulo financeiro |

---

## 1. Faturamento / Receita Total

**Nome Canônico:** `ptotal_`  
**Entidade Lógica:** `Venda`  
**View Física:** `VW_VENDAS_LM`  
**Campo Físico:** `ptotal_` (numeric)  
**Significado:** Valor total da linha de pedido/nota fiscal. Soma de `ptotal_` = faturamento bruto.

### Aliases e Sinônimos Mapeados (VIEW_COLUMN_MAPPING)
- `valor`, `valor_venda`, `valor_total`, `ptotal`, `ptotal_`
- `receita`, `faturamento`, `faturamento_total`, `receita_total`
- `data_referencia` (**workaround** — mapeado para `dtemissao_`)
- `trimestre`, `semestre` (**workaround** — mapeado para `dtemissao_`)

### Como é Localizada
1. LLM (Intent Engine) gera `SemanticPlan.metrics = ["receita_total"]`
2. `QueryIntentResolver.resolve_to_canonical()` resolve alias
3. `PlannerEngine` inclui entidade `Venda` no grafo
4. `QueryOptimizer.optimize_plan()` chama `translate_expression("receita_total")`
5. `translate_expression` busca em `VIEW_COLUMN_MAPPING["VW_VENDAS_LM"]` → retorna `VW_VENDAS_LM.ptotal_`
6. `SQLGenerator` inclui `VW_VENDAS_LM.ptotal_` no SELECT

### Quem Utiliza
- `new_query_orchestrator.py` → passo 5 (Query Optimizer)
- `query_optimizer_engine.py` → `VIEW_COLUMN_MAPPING`
- `planner_engine.py` → `supported_metrics` da entidade `Venda`
- `metadata_provider.py` → `supported_metrics=["ptotal_", "qtde_"]`
- `tests/mass_stress_test.py` → cenários 1–90 (maioria)

---

## 2. Quantidade Vendida

**Nome Canônico:** `qtde_`  
**Entidade Lógica:** `Venda`  
**View Física:** `VW_VENDAS_LM`  
**Campo Físico:** `qtde_` (numeric)  
**Significado:** Quantidade de itens vendidos por linha de nota.

### Aliases Mapeados
- `quantidade`, `qtde`, `qtde_`, `quantidade_transacoes`, `transacoes`

### Como é Localizada
- Mesmo pipeline do faturamento, via `translate_expression("quantidade")`

---

## 3. Estoque

**Nome Canônico:** `estoque`  
**Entidade Lógica:** `Produto`  
**View Física:** `VW_PRODUTOS_CAD_LM`  
**Campo Físico:** `estoque` (numeric)  
**Significado:** Posição de estoque atual do produto.

### Aliases Mapeados
- `estoque`, `custo`, `preco_custo`, `preco_venda`, `margem`

> ⚠️ **CONFLITO ARQUITETURAL:** `custo`, `preco_venda` e `margem` foram mapeados para `estoque` como **fallback de segurança** porque a view real não possui colunas de custo/margem. Esses aliases produzem resultados incorretos semanticamente (retornam estoque quando o usuário quer custo).

---

## 4. Valor da Parcela

**Nome Canônico:** `valor_parcela`  
**Entidade Lógica:** `Financeiro`  
**View Física:** `VW_FINANCEIRO_LM`  
**Campo Físico:** `valor_parcela` (numeric)  
**Significado:** Valor de uma parcela a receber.

> ⚠️ **RISCO:** A view `VW_FINANCEIRO_LM` não foi confirmada no banco de produção `luminaai_analytics_db`.

---

## Métricas Derivadas / Calculadas

As seguintes métricas **não existem como colunas físicas** mas são calculadas via SQL em runtime:

| Métrica Derivada | Expressão SQL | Depende de |
|-----------------|---------------|-----------|
| Faturamento Total | `SUM(ptotal_)` | VW_VENDAS_LM.ptotal_ |
| Ticket Médio | `AVG(ptotal_)` | VW_VENDAS_LM.ptotal_ |
| Total de Pedidos | `COUNT(DISTINCT nota_)` | VW_VENDAS_LM.nota_ |
| Quantidade Total | `SUM(qtde_)` | VW_VENDAS_LM.qtde_ |
| % Share Produto | `SUM(ptotal_)/SUM(SUM(ptotal_)) OVER()` | VW_VENDAS_LM.ptotal_ |
| Ranking de Clientes | `ROW_NUMBER() OVER(ORDER BY SUM(ptotal_) DESC)` | JOIN Venda+Cliente |
| Trimestre | `EXTRACT(QUARTER FROM dtemissao_)` | VW_VENDAS_LM.dtemissao_ |
| Mês | `EXTRACT(MONTH FROM dtemissao_)` | VW_VENDAS_LM.dtemissao_ |
| Ano | `EXTRACT(YEAR FROM dtemissao_)` | VW_VENDAS_LM.dtemissao_ |

---

## Métricas Referenciadas mas NÃO Existentes no Schema Atual

| Métrica Tentada | Resultado | Problema |
|----------------|-----------|---------|
| `custo_padrao` | ❌ UndefinedColumnError | Nunca existiu na VW_PRODUTOS_CAD_LM de produção |
| `margem` | ⚠️ Retorna `estoque` (fallback incorreto) | Workaround de sobrevivência |
| `preco_venda` | ⚠️ Retorna `estoque` (fallback incorreto) | Workaround de sobrevivência |
| `data_referencia` | ⚠️ Retorna `dtemissao_` (alias) | Nome legado corrigido |
| `receita` em VW_CLIENTES_CAD_LM | ⚠️ Retorna `codigo` (fallback) | Workaround incorreto semanticamente |
| `faturamento` em VW_CLIENTES_CAD_LM | ⚠️ Retorna `codigo` (fallback) | Workaround incorreto semanticamente |

---

*Auditoria estática — nenhum arquivo modificado.*
