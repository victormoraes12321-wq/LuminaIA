# Semantic Catalog Audit — LuminaAI
> Gerado por auditoria estática completa | Data: 2026-07-15 | Versão do Pipeline: 2.0

---

## 1. Mapeamento Geral do Dicionário Semântico

A camada semântica do LuminaAI é governada principalmente por `backend/services/semantic_layer.py`. Ela atua como um tradutor dinâmico de termos de negócio informais para termos canônicos oficiais e, finalmente, para colunas físicas em views de banco.

### Estrutura Central: `_BUSINESS_DICT`
Este dicionário estático em memória armazena as definições das métricas oficiais da empresa:
- **Campos por métrica**: `metric_name`, `definition`, `formula`, `validation_rules`, `data_sources` (views físicas aceitáveis), e `dependencies` (outras métricas ou campos).
- **Métricas catalogadas**: `receita_total`, `faturamento`, `lucro_bruto`, `margem_lucro`, `ticket_medio`, `cliente_ativo`, `churn_rate`, `ltv_estimado`, `cac_estimado`, `taxa_conversao`, `custo_total`, `quantidade_pedidos`, `unidades_vendidas`, `clientes_distintos`, `margem_media`, `meta_mensal`, `atingimento_meta`, `comissao`, `pedidos_qtd`, `ranking`.

---

## 2. Estratégias de Resolução e Tradução de Métricas

O sistema utiliza um pipeline multinível para traduzir uma métrica a partir da pergunta em linguagem natural do usuário:

```
[Métrica em Linguagem Natural]
       │
       ▼
1. normalizar texto (_normalize_alias_key)
   - Caixa baixa, remoção de acentos e caracteres especiais
       │
       ▼
2. singularizar tokens (_singularize_token)
   - Ex: "compradores" -> "comprador"
       │
       ▼
3. gerar variantes de pesquisa (_metric_key_variants)
   - Exame com/sem stopwords, singularizado, etc.
       │
       ▼
4. pesquisa exata no índice de aliases (_build_metric_alias_index)
   - Combina aliases estáticos + dinâmicos
       │
       ▼
5. pesquisa fuzzy (se falhar exata)
   - SequenceMatcher com threshold >= 0.88 (strings >= 6 chars)
       │
       ▼
[Métrica Canônica Resolvida]
```

### Índice de Aliases Estáticos
O dicionário `_STATIC_METRIC_ALIASES` mapeia mais de 120 variações linguísticas (PT/EN) para nomes canônicos.
*Exemplos de Aliases:*
- `quanto vendi` → `receita_total`
- `vendas` → `receita_total`
- `ganho` → `receita_total`
- `volume` → `unidades_vendidas`
- `pecas` → `unidades_vendidas`
- `media por compra` → `ticket_medio`

---

## 3. Sincronização Dinâmica (Runtime Sync)

O método `sync_from_semantic_catalog(tenant_id)` lê dados do banco de metadados (`luminaai_db`) de 3 tabelas ORM diferentes e atualiza o catálogo dinâmico em memória do tenant:
1. **`SemanticCatalog`** (Legado)
2. **`BusinessConcept`** (Governança BKE)
3. **`BusinessKPI`** (Governança BKE)

---

## ⚠️ ACHADOS CRÍTICOS & ANOMALIAS DA CAMADA SEMÂNTICA

1. **Vulnerabilidade de Isolamento Multi-Tenant (Poluição Global)**:
   > [!CAUTION]
   > A função `register_custom_metric()` muta o dicionário `_BUSINESS_DICT` diretamente usando a palavra-chave `global`.
   > Como o `_BUSINESS_DICT` é compartilhado por todos os tenants em memória no mesmo processo Python, **mutações feitas por um tenant alteram o dicionário de todos os outros tenants** em runtime. Não há chaveamento por `tenant_id` no dicionário interno em memória.

2. **Corrupção de Codificação de Caracteres (Encoding UTF-8 vs Latin-1)**:
   > [!WARNING]
   > No arquivo `semantic_layer.py`, diversas strings literais dentro do dicionário estático estão corrompidas na codificação de caracteres.
   > - `"perÃ­odo"` (esperado: "período")
   > - `"nÃºmero de clientes"` (esperado: "número de clientes")
   > - `"mÃ©dia"` (esperado: "média")
   > Isto indica que o arquivo foi salvo em UTF-8 mas lido ou editado sob encoding incorreto (Latin-1 / CP1252), o que pode fazer com que buscas exatas que contenham caracteres acentuados falhem no lookup inicial de chave.

3. **Inconsistência de Mapeamento de KPI (Fórmulas vs Código)**:
   - A fórmula lógica corporativa é declarada no modelo `BusinessKPI` e `BusinessFormula`, mas o `query_optimizer_engine.py` utiliza expressões SQL hardcoded e aliases fixos para computar as métricas, em vez de avaliar as fórmulas dinâmicas registradas. Existe um descasamento completo entre as fórmulas configuradas na UI de governança e as expressões geradas fisicamente no compilador de SQL.

---

*Auditoria estática — nenhum arquivo modificado.*
